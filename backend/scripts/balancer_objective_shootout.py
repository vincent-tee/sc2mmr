"""
Phase 5 (rating-consolidation-campaign) style comparison of the two
TeamBalancer.generate_team_suggestions objectives:

  - default ("mmr"): sorts candidate splits by
    (mmr_difference ascending, |win_probability - 0.5| ascending)
  - "composite": sorts by compute_composite_score (weighted blend of
    TrueSkill win-prob closeness, TrueSkill match quality, skill-spread
    penalty, component-profile penalty, synergy penalty -- see
    DEFAULT_COMPOSITE_WEIGHTS in app/balancer.py)

METHODOLOGY (binding, per the campaign skill's Phase 5 "honest metric"):
for a set of real historical match rosters (the actual players who played
together in a real match, teams unknown to the balancer), feed the full
roster into TeamBalancer.generate_team_suggestions() twice -- once per
objective -- and record, for the ONE split each objective would have
chosen (top_n=1, which sidesteps the "showcase" second-suggestion
synergy reorder that only fires when top_n>=2):

  - the chosen split's TrueSkill win_probability (|win_prob - 0.5|,
    lower is better -- a perfectly balanced split has p=0.5)
  - the chosen split's rating-of-record difference (mmr_difference,
    i.e. |sum(team_1.mmr) - sum(team_2.mmr)|, lower is better)

Success (per the campaign doc): the alternative (composite) is
improved-or-unchanged vs default on BOTH metrics, with the gap clearly
bigger than run-to-run bootstrap noise before promoting it.

This script is READ-ONLY: it opens sqlite3 in mode=ro and never writes to
the DB or calls any recalculation script. PlayerInfo objects are built
directly from the CURRENT `players` table row for each roster member --
this mirrors exactly what the real /teams/balance* endpoints do today
(TeamBalancer._load_balance_inputs -> PlayerInfo.from_player), so the
comparison measures "what would each objective choose for this roster
right now", not a leak-free chronological replay (that framing does not
apply here: the balancer's decision -- which split to propose -- has no
historical "before" state to walk forward through; it always uses
present-day ratings, live).

Usage: cd backend && python3 scripts/balancer_objective_shootout.py
"""
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.balancer import PlayerInfo, TeamBalancer

DB = "file:data/sc2mmr.db?mode=ro"

# Roster sizes above this are skipped -- combinations(n, n//2) blows up
# (e.g. 20 choose 10 = 184,756) and no real roster in this DB exceeds 10
# (verified 2026-09-14: max observed roster size in the last 30 matches is
# 10, C(10,5)=252, trivially cheap).
MAX_ROSTER_SIZE = 14


def load_rosters(con, limit=None):
    """
    Chronological (most-recent-first) list of real 2-team match rosters:
    (match_id, played_at, [player_id...]) for matches with exactly two
    non-empty teams and a real recorded winner.
    """
    rows = con.execute(
        """
        SELECT mp.match_id, m.played_at, mp.team_number, mp.player_id, mp.won
        FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE m.played_at IS NOT NULL
        ORDER BY m.played_at DESC, mp.match_id DESC
        """
    ).fetchall()

    matches, order = {}, []
    for mid, played_at, team, pid, won in rows:
        if mid not in matches:
            matches[mid] = {"played_at": played_at, "teams": defaultdict(list), "winner": None}
            order.append(mid)
        matches[mid]["teams"][team].append(pid)
        if won:
            matches[mid]["winner"] = team

    rosters = []
    for mid in order:
        m = matches[mid]
        teams = m["teams"]
        if len(teams) != 2 or m["winner"] is None:
            continue
        t1, t2 = sorted(teams.keys())
        if not teams[t1] or not teams[t2]:
            continue
        player_ids = teams[t1] + teams[t2]
        if len(player_ids) > MAX_ROSTER_SIZE:
            continue
        rosters.append((mid, m["played_at"], player_ids, teams[t1], teams[t2]))
        if limit is not None and len(rosters) >= limit:
            break
    return rosters


PLAYER_COLS = [
    "id", "name", "mu", "sigma", "mmr", "avg_overall_impact", "total_games",
    "avg_aggression_score", "avg_first_damage_timing", "avg_combat_score",
    "avg_economic_score", "avg_efficiency_score", "handicap_corrected_mmr",
    "unified_mmr",
]


def load_players(con, player_ids):
    """PlayerInfo per player_id, built the same way PlayerInfo.from_player does."""
    q = f"SELECT {','.join(PLAYER_COLS)} FROM players WHERE id IN ({','.join('?' * len(player_ids))})"
    rows = con.execute(q, list(player_ids)).fetchall()
    infos = {}
    for row in rows:
        d = dict(zip(PLAYER_COLS, row))
        avg_fdt = d["avg_first_damage_timing"] or 300
        avg_combat = d["avg_combat_score"] or 25
        timing_bonus = (300 - avg_fdt) / 60 * 100
        handicap_corrected = d["handicap_corrected_mmr"] or d["mmr"]
        unified = d["unified_mmr"] or handicap_corrected
        infos[d["id"]] = PlayerInfo(
            id=d["id"],
            name=d["name"],
            mu=d["mu"],
            sigma=d["sigma"],
            mmr=d["mmr"],
            overall_impact=d["avg_overall_impact"] or 50.0,
            total_games=d["total_games"],
            aggression_score=d["avg_aggression_score"] or 50.0,
            avg_first_damage_timing=avg_fdt,
            avg_combat_score=avg_combat,
            economic_score=d["avg_economic_score"] or 60.0,
            efficiency_score=d["avg_efficiency_score"] or 55.0,
            timing_adjusted_mmr=d["mmr"] + timing_bonus,
            handicap_corrected_mmr=handicap_corrected,
            unified_mmr=unified,
        )
    return infos


def evaluate_roster(player_infos):
    """Run both objectives on one roster; return (default_result, composite_result)."""
    default_pick = TeamBalancer.generate_team_suggestions(
        player_infos, top_n=1, objective="mmr"
    )[0]
    composite_pick = TeamBalancer.generate_team_suggestions(
        player_infos, top_n=1, objective="composite"
    )[0]
    return default_pick, composite_pick


def actual_split_stats(player_infos_by_id, t1_ids, t2_ids):
    """Win-prob / rating-diff of the split that ACTUALLY happened, for context."""
    t1 = [player_infos_by_id[pid] for pid in t1_ids]
    t2 = [player_infos_by_id[pid] for pid in t2_ids]
    win_prob = TeamBalancer.calculate_win_probability(t1, t2)
    diff = abs(sum(p.mmr for p in t1) - sum(p.mmr for p in t2))
    return win_prob, diff


def run(rosters, con):
    results = []
    for mid, played_at, player_ids, t1_ids, t2_ids in rosters:
        infos_by_id = load_players(con, player_ids)
        if len(infos_by_id) != len(player_ids):
            continue  # a player row is missing (e.g. deleted/merged) -- skip
        player_infos = list(infos_by_id.values())

        default_pick, composite_pick = evaluate_roster(player_infos)
        actual_wp, actual_diff = actual_split_stats(infos_by_id, t1_ids, t2_ids)

        results.append(
            dict(
                match_id=mid,
                played_at=played_at,
                n_players=len(player_infos),
                default_abs_wp=abs(default_pick.win_probability - 0.5),
                default_diff=default_pick.mmr_difference,
                composite_abs_wp=abs(composite_pick.win_probability - 0.5),
                composite_diff=composite_pick.mmr_difference,
                actual_abs_wp=abs(actual_wp - 0.5),
                actual_diff=actual_diff,
            )
        )
    return results


def summarize(results, label):
    n = len(results)
    if n == 0:
        print(f"{label}: n=0")
        return
    mean_default_wp = sum(r["default_abs_wp"] for r in results) / n
    mean_default_diff = sum(r["default_diff"] for r in results) / n
    mean_composite_wp = sum(r["composite_abs_wp"] for r in results) / n
    mean_composite_diff = sum(r["composite_diff"] for r in results) / n
    mean_actual_wp = sum(r["actual_abs_wp"] for r in results) / n
    mean_actual_diff = sum(r["actual_diff"] for r in results) / n

    print(f"\n{label} (n={n} rosters)")
    print(f"  {'objective':<12} {'mean |winprob-0.5|':>20} {'mean rating-diff':>18}")
    print(f"  {'default':<12} {mean_default_wp:>20.4f} {mean_default_diff:>18.1f}")
    print(f"  {'composite':<12} {mean_composite_wp:>20.4f} {mean_composite_diff:>18.1f}")
    print(f"  {'actual split':<12} {mean_actual_wp:>20.4f} {mean_actual_diff:>18.1f}")
    print(
        f"  delta (composite - default): "
        f"|winprob-0.5| {mean_composite_wp - mean_default_wp:+.4f}, "
        f"rating-diff {mean_composite_diff - mean_default_diff:+.1f}"
    )
    return dict(
        n=n,
        mean_default_wp=mean_default_wp,
        mean_default_diff=mean_default_diff,
        mean_composite_wp=mean_composite_wp,
        mean_composite_diff=mean_composite_diff,
    )


def bootstrap_delta(results, seed=42, n_resamples=1000):
    """Bootstrap CI on (composite - default) for both metrics, resampling matches."""
    n = len(results)
    if n == 0:
        return None
    rng = random.Random(seed)
    wp_diffs, rd_diffs = [], []
    for _ in range(n_resamples):
        sample = [results[rng.randrange(n)] for _ in range(n)]
        wp_diffs.append(
            sum(r["composite_abs_wp"] for r in sample) / n
            - sum(r["default_abs_wp"] for r in sample) / n
        )
        rd_diffs.append(
            sum(r["composite_diff"] for r in sample) / n
            - sum(r["default_diff"] for r in sample) / n
        )
    wp_diffs.sort()
    rd_diffs.sort()
    lo_i, hi_i = int(0.025 * n_resamples), int(0.975 * n_resamples)
    return dict(
        wp_mean=sum(wp_diffs) / n_resamples,
        wp_ci=(wp_diffs[lo_i], wp_diffs[hi_i]),
        wp_pos_frac=sum(d > 0 for d in wp_diffs) / n_resamples,
        rd_mean=sum(rd_diffs) / n_resamples,
        rd_ci=(rd_diffs[lo_i], rd_diffs[hi_i]),
        rd_pos_frac=sum(d > 0 for d in rd_diffs) / n_resamples,
    )


def main():
    con = sqlite3.connect(DB, uri=True)

    # Pre-registered comparison point: 20 most recent match rosters.
    rosters_20 = load_rosters(con, limit=20)
    results_20 = run(rosters_20, con)
    summary_20 = summarize(results_20, "PRE-REGISTERED: 20 most recent match rosters")

    # Extended sample: all usable historical rosters (roster size <= 14).
    rosters_all = load_rosters(con, limit=None)
    results_all = run(rosters_all, con)
    summary_all = summarize(results_all, "EXTENDED: all usable historical rosters")

    print("\n" + "=" * 78)
    print("BOOTSTRAP (composite - default), 1000 resamples over matches")
    print("=" * 78)
    for label, results in (("20 most recent", results_20), ("extended sample", results_all)):
        ci = bootstrap_delta(results)
        if ci is None:
            continue
        print(f"\n{label} (n={len(results)}):")
        print(
            f"  |winprob-0.5| delta: mean {ci['wp_mean']:+.4f}, "
            f"95% CI [{ci['wp_ci'][0]:+.4f}, {ci['wp_ci'][1]:+.4f}], "
            f"composite-worse in {ci['wp_pos_frac']:.0%} of resamples"
        )
        print(
            f"  rating-diff delta:   mean {ci['rd_mean']:+.1f}, "
            f"95% CI [{ci['rd_ci'][0]:+.1f}, {ci['rd_ci'][1]:+.1f}], "
            f"composite-worse in {ci['rd_pos_frac']:.0%} of resamples"
        )

    con.close()


if __name__ == "__main__":
    main()
