"""Read-only: two owner-specified, named hypotheses about specific players.

Run under sc2mmr-research-methodology Rule 1 (predict before running) and
Rule 3 (adversarial refutation). These are pre-registered because the owner
named the players AND the mechanism before any data was looked at -- this is
NOT a scan of all 160 players for whoever looks extreme (that would be the
multiple-comparisons trap); only Stephan and DragonKing get a formal test.

## Hypothesis A -- Stephan, "captain effect"
Stephan adapts mid-game, punishes early aggression, and calls counters --
a coordination/decision-making effect on the WHOLE team, not just his own
combat stats. TrueSkill's additive model (team strength = sum of individual
mu) cannot represent a player who makes teammates perform above their own
rating. If real, teams with Stephan should beat the pre-match win-probability
model's prediction on average, systematically, not just from his own mu
being slightly stale.

Predicted number: mean signed prediction residual for Stephan's teams > 0.
Kill criterion: dead if the bootstrap CI (resampled over his own matches)
includes zero, or if the effect size is not clearly larger than the spread
seen across other high-volume players (context distribution below).

## Hypothesis B -- DragonKing (aka "ShadowDragon"), boom-or-bust
Claim: DragonKing's macro is either unstoppable ("on form") or ordinary --
higher game-to-game variance in performance than a typical player at his
skill level, not a stable single skill number.

Predicted number: DragonKing's per-match overall_impact_z standard deviation
noticeably above the distribution of other high-volume players' std devs.
Kill criterion: dead if his std dev is not in the upper tail of that
distribution once sample-size noise is accounted for (players naturally show
more variance with fewer games; compare like-for-like via subsampling).

Also runs Hypothesis A's residual test for DragonKing, since "on form"
could equally mean "swings the whole team's result," not just his own box
score -- worth checking even though it wasn't the owner's stated claim.
"""
import random
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import trueskill

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.rating_policy import decayed_sigma, typical_session_gap, win_probability, rate_teams
from walkforward_session_eval import load_matches, DB

NAMED_PLAYERS = ["Stephan", "DragonKing", "ShadowDragon"]
MIN_GAMES_FOR_CONTEXT = 50  # "high-volume" cohort per the frontier skill's own inventory


def player_id_map(con):
    return {name: pid for pid, name in con.execute("SELECT id, name FROM players").fetchall()}


def dk_name(con):
    """DragonKing was merged into ShadowDragon in prod but not in local dev --
    use whichever name this dataset actually has."""
    ids = player_id_map(con)
    return "ShadowDragon" if "ShadowDragon" in ids else "DragonKing"


def match_residuals(usable):
    """Leak-free: for each match, (actual_outcome_team1 - predicted_p1), plus
    the pre-match ratings so callers can compute other per-match stats too."""
    ratings = defaultdict(lambda: trueskill.Rating(mu=25.0, sigma=8.333))
    history = defaultdict(list)
    out = []
    for mid, played_at, t1, t1_ids, t2, t2_ids, winner in usable:
        now = datetime.fromisoformat(played_at)
        for pid in t1_ids + t2_ids:
            prior_times = history[pid]
            old = ratings[pid]
            days = (now - prior_times[-1]).days if prior_times else 0
            ratings[pid] = trueskill.Rating(mu=old.mu, sigma=decayed_sigma(
                old.sigma, days, len(prior_times), typical_session_gap(prior_times + [now])))
        t1r = [ratings[pid] for pid in t1_ids]
        t2r = [ratings[pid] for pid in t2_ids]
        p1 = win_probability(t1r, t2r)
        outcome1 = 1 if winner == t1 else 0
        out.append(dict(mid=mid, t1_ids=t1_ids, t2_ids=t2_ids, residual=outcome1 - p1))
        new_t1, new_t2 = rate_teams(t1r, t2r, winner == t1)
        for pid, r in zip(t1_ids, new_t1):
            ratings[pid] = r
        for pid, r in zip(t2_ids, new_t2):
            ratings[pid] = r
        for pid in t1_ids + t2_ids:
            history[pid].append(now)
    return out


def per_player_signed_residuals(rows):
    """player_id -> list of signed residuals (positive = that player's team beat the model)."""
    out = defaultdict(list)
    for r in rows:
        for pid in r["t1_ids"]:
            out[pid].append(r["residual"])
        for pid in r["t2_ids"]:
            out[pid].append(-r["residual"])
    return out


def bootstrap_mean_ci(values, seed=42, n_resamples=2000):
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return dict(mean=sum(values) / n, lo=means[int(0.025 * n_resamples)],
                hi=means[int(0.975 * n_resamples)])


def hypothesis_a(con, label):
    usable = load_matches(con)
    rows = match_residuals(usable)
    by_player = per_player_signed_residuals(rows)
    ids = player_id_map(con)

    print(f"\n--- Hypothesis A ({label}): does this player's team beat the pre-match "
          f"win-probability model, systematically? ---")
    print(f"(context: distribution across all players with >= {MIN_GAMES_FOR_CONTEXT} games)")

    context_means = []
    for pid, vals in by_player.items():
        if len(vals) >= MIN_GAMES_FOR_CONTEXT:
            context_means.append(sum(vals) / len(vals))
    context_means.sort()
    if context_means:
        print(f"  n={len(context_means)} players; median mean-residual={statistics.median(context_means):+.3f}, "
              f"range [{context_means[0]:+.3f}, {context_means[-1]:+.3f}]")

    names_here = ["Stephan", dk_name(con)]
    for name in names_here:
        pid = ids.get(name)
        if pid is None or pid not in by_player:
            print(f"  {name}: not found or no matches in this dataset")
            continue
        vals = by_player[pid]
        ci = bootstrap_mean_ci(vals)
        rank = sum(1 for m in context_means if m < ci["mean"]) / len(context_means) if context_means else None
        survives = ci["lo"] > 0
        print(f"  {name}: n={len(vals)} games, mean signed residual={ci['mean']:+.3f}, "
              f"95% CI [{ci['lo']:+.3f}, {ci['hi']:+.3f}]"
              + (f", percentile among >= {MIN_GAMES_FOR_CONTEXT}-game players={rank:.0%}" if rank is not None else "")
              + f" -- {'SURVIVES (CI excludes zero, positive)' if survives else 'does not survive (CI includes zero or negative)'}")


def hypothesis_b(con, label):
    name = dk_name(con)
    print(f"\n--- Hypothesis B ({label}): is {name}'s per-game performance more "
          f"variable (boom-or-bust) than typical, not just consistently high? ---")
    ids = player_id_map(con)
    dk_id = ids.get(name)
    if dk_id is None:
        print(f"  {name} not found in this dataset")
        return

    rows = con.execute("""
        SELECT pmm.overall_impact FROM player_match_metrics pmm
        JOIN match_players mp ON mp.id = pmm.match_player_id
        WHERE mp.player_id = ? AND pmm.overall_impact IS NOT NULL
    """, (dk_id,)).fetchall()
    dk_values = [r[0] for r in rows]
    if len(dk_values) < 10:
        print(f"  Only {len(dk_values)} games with overall_impact recorded -- too few to assess variance.")
        return
    dk_std = statistics.stdev(dk_values)
    dk_mean = statistics.mean(dk_values)
    print(f"  {name}: n={len(dk_values)} games with recorded overall_impact, "
          f"mean={dk_mean:.1f}, std dev={dk_std:.1f} (coefficient of variation={dk_std/dk_mean:.2f})")

    # Context: other players with >= MIN_GAMES_FOR_CONTEXT recorded overall_impact games.
    other_ids = con.execute("""
        SELECT mp.player_id, COUNT(*) c FROM player_match_metrics pmm
        JOIN match_players mp ON mp.id = pmm.match_player_id
        WHERE pmm.overall_impact IS NOT NULL AND mp.player_id != ?
        GROUP BY mp.player_id HAVING c >= ?
    """, (dk_id, MIN_GAMES_FOR_CONTEXT)).fetchall()

    other_stds = []
    rng = random.Random(42)
    n_dk = len(dk_values)
    for pid, _ in other_ids:
        vals = [r[0] for r in con.execute("""
            SELECT pmm.overall_impact FROM player_match_metrics pmm
            JOIN match_players mp ON mp.id = pmm.match_player_id
            WHERE mp.player_id = ? AND pmm.overall_impact IS NOT NULL
        """, (pid,)).fetchall()]
        # Subsample to DragonKing's own game count so more-played players don't
        # get an unfair, noisier-looking variance estimate just from having more data.
        sample = vals if len(vals) <= n_dk else rng.sample(vals, n_dk)
        if len(sample) >= 10:
            other_stds.append(statistics.stdev(sample))

    if not other_stds:
        print("  No comparable players with enough data for context.")
        return
    other_stds.sort()
    percentile = sum(1 for s in other_stds if s < dk_std) / len(other_stds)
    print(f"  Context: {len(other_stds)} other players (>= {MIN_GAMES_FOR_CONTEXT} games, "
          f"subsampled to n={n_dk} for a fair comparison), "
          f"std dev range [{other_stds[0]:.1f}, {other_stds[-1]:.1f}], median={statistics.median(other_stds):.1f}")
    print(f"  {name}'s std dev is at the {percentile:.0%} percentile of that distribution "
          + ("-- SURVIVES (clearly in the upper tail)" if percentile >= 0.90
             else "-- does not survive (not unusually variable)"))


def main():
    for label, path in [("local dev", DB),
                         ("prod", "file:/home/vtee/.claude/jobs/969106c5/tmp/prod-before.db?mode=ro")]:
        con = sqlite3.connect(path, uri=True)
        hypothesis_a(con, label)
        hypothesis_b(con, label)
        con.close()


if __name__ == "__main__":
    main()
