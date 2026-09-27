"""Read-only chronological evaluation using the live rating policy.

Predict before observing each result. Current game time is known; only prior
results affect ratings. Calibration fits earlier complete sessions and is
scored on the untouched last 25% of sessions. No live ratings are written.
"""
import math
import random
import sqlite3
from collections import defaultdict
from datetime import datetime

import trueskill

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings
from app.rating_system import RatingSystem
from app.rating_policy import (
    POLICY_VERSION, decayed_sigma, typical_session_gap, win_probability, rate_teams,
)

DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sc2mmr.db") + "?mode=ro"
TS_MU = settings.trueskill_mu
TS_SIGMA = settings.trueskill_sigma
SESSION_GAP_HOURS = settings.session_gap_hours


def display_mmr(mu, sigma):
    return RatingSystem.calculate_display_mmr(mu, sigma)


def trueskill_win_prob(team1_ratings, team2_ratings):
    return win_probability(team1_ratings, team2_ratings)


def load_matches(con):
    """Chronological (match_id, played_at, {team: [player_id,...]}, winner_team)."""
    rows = con.execute("""
        SELECT mp.match_id, m.played_at, mp.team_number, mp.player_id, mp.won
        FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE m.played_at IS NOT NULL
        ORDER BY m.played_at ASC, mp.match_id ASC
    """).fetchall()

    matches, order = {}, []
    for mid, played_at, team, pid, won in rows:
        if mid not in matches:
            matches[mid] = {"played_at": played_at, "teams": defaultdict(list), "winner": None, "results": []}
            order.append(mid)
        matches[mid]["teams"][team].append(pid)
        matches[mid]["results"].append((team, pid, won))
        if won:
            matches[mid]["winner"] = team

    usable = []
    for mid in order:
        m = matches[mid]
        teams = m["teams"]
        results = m["results"]
        winners = {team for team, _, won in results if won}
        ids = [pid for _, pid, _ in results]
        if (len(teams) != 2 or len(winners) != 1
                or len(ids) != len(set(ids))
                or any(bool(won) != (team in winners) for team, _, won in results)):
            continue
        t1, t2 = sorted(teams.keys())
        if not teams[t1] or not teams[t2]:
            continue
        usable.append((mid, m["played_at"], t1, teams[t1], t2, teams[t2], m["winner"]))
    return usable


def duplicated_game_ids(con, max_start_gap_seconds=120):
    rosters = defaultdict(set)
    for mid, pid in con.execute("SELECT match_id, player_id FROM match_players"):
        rosters[mid].add(pid)
    games = sorted((datetime.fromisoformat(played_at), map_name, mid) for mid, played_at, map_name
                   in con.execute("SELECT id, played_at, map_name FROM matches WHERE played_at IS NOT NULL"))
    duplicated = set()
    for i, (t, map_name, mid) in enumerate(games):
        for t2, map2, mid2 in games[i + 1:i + 6]:
            if ((t2 - t).total_seconds() <= max_start_gap_seconds and map2 == map_name
                    and rosters[mid] == rosters[mid2]):
                duplicated |= {mid, mid2}
    return duplicated


def assign_sessions(usable, gap_hours=SESSION_GAP_HOURS):
    """Assign a session id per match based on a wall-clock gap threshold."""
    session_ids = []
    session_id = 0
    prev_time = None
    for mid, played_at, t1, t1_ids, t2, t2_ids, winner in usable:
        t = datetime.fromisoformat(played_at)
        if prev_time is not None:
            gap = (t - prev_time).total_seconds() / 3600.0
            if gap > gap_hours:
                session_id += 1
        session_ids.append(session_id)
        prev_time = t
    return session_ids


def brier_score(probs, outcomes):
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def log_loss(probs, outcomes, eps=1e-12):
    total = 0.0
    for p, o in zip(probs, outcomes):
        p = min(max(p, eps), 1 - eps)
        total += -(o * math.log(p) + (1 - o) * math.log(1 - p))
    return total / len(probs)


def calibration_table(probs, outcomes, n_bins=10):
    bins = [[] for _ in range(n_bins)]
    for p, o in zip(probs, outcomes):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, o))
    rows = []
    for i, b in enumerate(bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        if not b:
            rows.append((lo, hi, 0, None, None))
            continue
        mean_pred = sum(p for p, _ in b) / len(b)
        actual_rate = sum(o for _, o in b) / len(b)
        rows.append((lo, hi, len(b), mean_pred, actual_rate))
    return rows


def run_simulation(usable):
    """Walk forward through matches; predict from pre-match state, then update."""
    ratings = defaultdict(lambda: trueskill.Rating(mu=TS_MU, sigma=TS_SIGMA))

    history = defaultdict(list)
    ts_probs, ts_outcomes, ts_pred_winner = [], [], []
    base_pred_winner = []
    match_ids = []

    for mid, played_at, t1, t1_ids, t2, t2_ids, winner in usable:
        now = datetime.fromisoformat(played_at)
        for pid in t1_ids + t2_ids:
            prior_times = history[pid]
            old = ratings[pid]
            days = (now - prior_times[-1]).days if prior_times else 0
            ratings[pid] = trueskill.Rating(mu=old.mu, sigma=decayed_sigma(
                old.sigma, days, len(prior_times),
                typical_session_gap(prior_times + [now]),
            ))
        t1_ratings = [ratings[pid] for pid in t1_ids]
        t2_ratings = [ratings[pid] for pid in t2_ids]

        # --- 1. PREDICT from pre-match state only ---
        p1 = trueskill_win_prob(t1_ratings, t2_ratings)
        outcome = 1 if winner == t1 else 0
        ts_probs.append(p1)
        ts_outcomes.append(outcome)
        if p1 == 0.5:
            ts_pred_winner.append(None)  # true tie, excluded from winner accuracy
        else:
            ts_pred_winner.append(t1 if p1 > 0.5 else t2)

        sum1 = sum(display_mmr(r.mu, r.sigma) for r in t1_ratings)
        sum2 = sum(display_mmr(r.mu, r.sigma) for r in t2_ratings)
        if sum1 == sum2:
            base_pred_winner.append(None)
        else:
            base_pred_winner.append(t1 if sum1 > sum2 else t2)

        match_ids.append(mid)

        # --- 2. THEN advance state with the real outcome ---
        new_t1, new_t2 = rate_teams(t1_ratings, t2_ratings, winner == t1)
        for pid, r in zip(t1_ids, new_t1):
            ratings[pid] = r
        for pid, r in zip(t2_ids, new_t2):
            ratings[pid] = r
        for pid in t1_ids + t2_ids:
            history[pid].append(now)

    actual_winner = [w for (_, _, _, _, _, _, w) in usable]
    return dict(
        ratings=dict(ratings),
        match_ids=match_ids,
        ts_probs=ts_probs,
        ts_outcomes=ts_outcomes,
        ts_pred_winner=ts_pred_winner,
        base_pred_winner=base_pred_winner,
        actual_winner=actual_winner,
    )


def winner_accuracy(pred_winner, actual_winner):
    ties = sum(1 for p in pred_winner if p is None)
    decided = [(p, a) for p, a in zip(pred_winner, actual_winner) if p is not None]
    n = len(decided)
    correct = sum(1 for p, a in decided if p == a)
    return correct, n, ties


def report_block(title, idx, res):
    """Print full metrics for a subset of match indices."""
    if not idx:
        print(f"  {title}: n=0 (no matches)")
        return None
    probs = [res["ts_probs"][i] for i in idx]
    outcomes = [res["ts_outcomes"][i] for i in idx]
    ts_pred = [res["ts_pred_winner"][i] for i in idx]
    base_pred = [res["base_pred_winner"][i] for i in idx]
    actual = [res["actual_winner"][i] for i in idx]

    brier = brier_score(probs, outcomes)
    ll = log_loss(probs, outcomes)
    ts_correct, ts_n, ts_ties = winner_accuracy(ts_pred, actual)
    base_correct, base_n, base_ties = winner_accuracy(base_pred, actual)

    print(f"  {title}")
    print(f"    n={len(idx)}  Brier={brier:.4f}  LogLoss={ll:.4f}")
    print(f"    TrueSkill win-prob accuracy: {ts_correct}/{ts_n} = {ts_correct/ts_n:.1%}"
          f"  (ties excluded: {ts_ties})" if ts_n else "    TrueSkill: no decided matches")
    print(f"    Naive baseline (sum display-MMR) accuracy: {base_correct}/{base_n} = "
          f"{base_correct/base_n:.1%}  (ties excluded: {base_ties})" if base_n else
          "    Baseline: no decided matches")
    return dict(brier=brier, log_loss=ll, ts_acc=(ts_correct, ts_n), base_acc=(base_correct, base_n))


def print_calibration(probs, outcomes, label):
    print(f"\n  Calibration ({label}, predicted P(team1 wins) vs actual team1 win rate):")
    print(f"    {'bucket':<12} {'n':>5} {'mean_pred':>10} {'actual_rate':>12}")
    for lo, hi, n, mean_pred, actual_rate in calibration_table(probs, outcomes):
        if n == 0:
            print(f"    [{lo:.1f},{hi:.1f})  {n:>5}  {'--':>10} {'--':>12}")
        else:
            print(f"    [{lo:.1f},{hi:.1f})  {n:>5}  {mean_pred:>10.3f} {actual_rate:>12.3f}")


def bootstrap_delta(res, idx, seed=42, n_resamples=1000, session_ids=None):
    """Bootstrap CI on (TrueSkill accuracy - baseline accuracy) over session blocks (or individual matches when IDs omitted)."""
    decided = [i for i in idx
               if res["ts_pred_winner"][i] is not None and res["base_pred_winner"][i] is not None]
    if not decided:
        return None
    rng = random.Random(seed)
    diffs = []
    groups = defaultdict(list)
    for i in decided:
        groups[session_ids[i] if session_ids is not None else i].append(i)
    blocks = list(groups.values())
    for _ in range(n_resamples):
        sample = [i for _ in blocks for i in blocks[rng.randrange(len(blocks))]]
        ts_c = sum(1 for i in sample if res["ts_pred_winner"][i] == res["actual_winner"][i])
        base_c = sum(1 for i in sample if res["base_pred_winner"][i] == res["actual_winner"][i])
        diffs.append(ts_c / len(sample) - base_c / len(sample))
    diffs.sort()
    pos = sum(d > 0 for d in diffs) / len(diffs)
    return dict(mean=sum(diffs) / len(diffs), lo=diffs[24], hi=diffs[974], pos_frac=pos)


def calibrated_probability(p, temperature):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return 1 / (1 + math.exp(-math.log(p / (1 - p)) / temperature))


def holdout_comparison(res, session_ids):
    """Choose a symmetric temperature on training sessions only; freeze for test."""
    sessions = sorted(set(session_ids))
    if len(sessions) < 8:
        return None
    cutoff = sessions[max(1, int(len(sessions) * .75))]
    train = [i for i, sid in enumerate(session_ids) if sid < cutoff]
    test = [i for i, sid in enumerate(session_ids) if sid >= cutoff]
    outcomes = [res['ts_outcomes'][i] for i in train]
    temperatures = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    temperature = min(temperatures, key=lambda t: log_loss(
        [calibrated_probability(res['ts_probs'][i], t) for i in train], outcomes))
    raw = [res['ts_probs'][i] for i in test]
    calibrated = [calibrated_probability(p, temperature) for p in raw]
    actual = [res['ts_outcomes'][i] for i in test]
    return dict(temperature=temperature, train_count=len(train), test_count=len(test),
                cutoff_session=cutoff, raw=raw, calibrated=calibrated, actual=actual)


def report_holdout(res, session_ids):
    result = holdout_comparison(res, session_ids)
    if result is None:
        print('Not enough sessions for calibration holdout (minimum 8).')
        return
    print(f"Held-out last 25% of sessions: train={result['train_count']}, "
          f"test={result['test_count']}, fitted temperature={result['temperature']}")
    for label in ('raw', 'calibrated'):
        print(f"  {label}: Brier={brier_score(result[label], result['actual']):.4f}, "
              f"log loss={log_loss(result[label], result['actual']):.4f}")
    print('Offline candidate only; no live probabilities or balancing weights changed by this fit.')


def main():
    print(f"Policy: {POLICY_VERSION}; beta={settings.trueskill_beta}; "
          f"tau={settings.trueskill_tau}; adaptive_decay={settings.adaptive_decay_enabled}")
    con = sqlite3.connect(DB, uri=True)
    usable = load_matches(con)
    con.close()
    print(f"Loaded {len(usable)} usable matches (2-team, real winner, played_at known)")

    session_ids = assign_sessions(usable)
    n_sessions = session_ids[-1] + 1 if session_ids else 0
    print(f"Grouped into {n_sessions} gaming sessions (gap threshold = {SESSION_GAP_HOURS}h)")

    res = run_simulation(usable)
    report_holdout(res, session_ids)

    print("\n" + "=" * 78)
    print("OVERALL (leak-free, chronological walk-forward)")
    print("=" * 78)
    all_idx = list(range(len(usable)))
    report_block("All matches", all_idx, res)
    print_calibration(res["ts_probs"], res["ts_outcomes"], "TrueSkill, all matches")

    ci = bootstrap_delta(res, all_idx, session_ids=session_ids)
    if ci:
        print(f"\n  Session-block bootstrap (1000 resamples): TrueSkill - baseline accuracy delta "
              f"mean {ci['mean']:+.1%}, 95% CI [{ci['lo']:+.1%}, {ci['hi']:+.1%}], "
              f"positive in {ci['pos_frac']:.0%} of resamples")

    print("\n" + "=" * 78)
    print("PER-SESSION BREAKDOWN")
    print("=" * 78)
    by_session = defaultdict(list)
    for i, sid in enumerate(session_ids):
        by_session[sid].append(i)

    session_summaries = []
    for sid in sorted(by_session):
        idx = by_session[sid]
        if len(idx) < 3:
            continue  # too few matches for a meaningful per-session Brier/calibration
        played_at_first = usable[idx[0]][1]
        summary = report_block(f"Session {sid} (first match {played_at_first}, n={len(idx)})", idx, res)
        if summary:
            session_summaries.append((sid, len(idx), summary))

    small_sessions = sum(1 for sid in by_session if len(by_session[sid]) < 3)
    print(f"\n  ({small_sessions} sessions with <3 matches omitted from per-session table; "
          f"still included in OVERALL)")

    if session_summaries:
        ts_win_sessions = sum(
            1 for _, _, s in session_summaries
            if s["ts_acc"][1] > 0 and s["base_acc"][1] > 0
            and (s["ts_acc"][0] / s["ts_acc"][1]) > (s["base_acc"][0] / s["base_acc"][1])
        )
        comparable = sum(1 for _, _, s in session_summaries if s["ts_acc"][1] > 0 and s["base_acc"][1] > 0)
        print(f"\n  TrueSkill beat the naive baseline in {ts_win_sessions}/{comparable} "
              f"sessions with >=3 matches")


if __name__ == "__main__":
    main()
