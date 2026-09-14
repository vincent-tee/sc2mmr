"""Read-only: does sigma-aware "closeness" (trueskill.quality) identify
genuinely balanced games better than point-estimate MMR difference?

Frontier item 1 in .claude/skills/sc2mmr-research-frontier/SKILL.md. Reuses
the exact same leak-free chronological state (rating_policy decay + rate)
as scripts/walkforward_session_eval.py so this is directly comparable to
that script's numbers, not a separate simulation with its own drift.

Method: for every played match, compute both closeness metrics from
pre-match state only, then ask -- among the quarter of games each metric
calls "most balanced", how close to 50% did the favored side actually win?
A metric that correctly identifies close games should land near 50% there;
one that doesn't will be further off. Session-block bootstrap for the CI.
"""
import random
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import trueskill

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.rating_policy import decayed_sigma, typical_session_gap, win_probability, rate_teams
from walkforward_session_eval import load_matches, assign_sessions, display_mmr, DB, SESSION_GAP_HOURS


def run(usable):
    """Same chronological replay as walkforward_session_eval.run_simulation,
    plus the two closeness metrics (mu-sum diff, trueskill.quality) per match."""
    ratings = defaultdict(lambda: trueskill.Rating(mu=25.0, sigma=8.333))
    history = defaultdict(list)
    rows = []

    for mid, played_at, t1, t1_ids, t2, t2_ids, winner in usable:
        now = datetime.fromisoformat(played_at)
        for pid in t1_ids + t2_ids:
            prior_times = history[pid]
            old = ratings[pid]
            days = (now - prior_times[-1]).days if prior_times else 0
            ratings[pid] = trueskill.Rating(mu=old.mu, sigma=decayed_sigma(
                old.sigma, days, len(prior_times), typical_session_gap(prior_times + [now]),
            ))
        t1_ratings = [ratings[pid] for pid in t1_ids]
        t2_ratings = [ratings[pid] for pid in t2_ids]

        p1 = win_probability(t1_ratings, t2_ratings)
        favored = t1 if p1 > 0.5 else (t2 if p1 < 0.5 else None)
        mu_diff = abs(sum(r.mu for r in t1_ratings) - sum(r.mu for r in t2_ratings))
        quality = trueskill.quality([t1_ratings, t2_ratings])

        rows.append(dict(
            mid=mid, session_played_at=now, favored=favored, winner=winner,
            mu_diff=mu_diff, quality=quality,
        ))

        new_t1, new_t2 = rate_teams(t1_ratings, t2_ratings, winner == t1)
        for pid, r in zip(t1_ids, new_t1):
            ratings[pid] = r
        for pid, r in zip(t2_ids, new_t2):
            ratings[pid] = r
        for pid in t1_ids + t2_ids:
            history[pid].append(now)

    return rows


def favored_win_rate(rows):
    decided = [r for r in rows if r["favored"] is not None]
    if not decided:
        return None
    correct = sum(1 for r in decided if r["favored"] == r["winner"])
    return correct / len(decided), len(decided)


def quartile_by(rows, key, reverse):
    """Bottom quarter by `key` ascending (reverse=False) or descending (reverse=True)."""
    ordered = sorted(rows, key=lambda r: r[key], reverse=reverse)
    cutoff = max(1, len(ordered) // 4)
    return ordered[:cutoff]


def deviation_from_half(rows):
    result = favored_win_rate(rows)
    if result is None:
        return None
    rate, n = result
    return abs(rate - 0.5), rate, n


def main():
    con = sqlite3.connect(DB, uri=True)
    usable = load_matches(con)
    con.close()
    session_ids = assign_sessions(usable)
    print(f"Loaded {len(usable)} usable matches, {session_ids[-1] + 1 if session_ids else 0} sessions")

    rows = run(usable)

    quartile_point = quartile_by(rows, "mu_diff", reverse=False)   # smallest mu diff = "most balanced"
    quartile_sigma = quartile_by(rows, "quality", reverse=True)    # highest quality = "most balanced"

    dev_point, rate_point, n_point = deviation_from_half(quartile_point)
    dev_sigma, rate_sigma, n_sigma = deviation_from_half(quartile_sigma)

    print(f"\nPoint-estimate metric (|mu sum diff|), most-balanced quarter (n={n_point}):")
    print(f"  favored-side win rate = {rate_point:.1%}  (deviation from 50% = {dev_point:.1%})")
    print(f"\nSigma-aware metric (trueskill.quality), most-balanced quarter (n={n_sigma}):")
    print(f"  favored-side win rate = {rate_sigma:.1%}  (deviation from 50% = {dev_sigma:.1%})")
    print(f"\nRaw deviation gap (point - sigma): {dev_point - dev_sigma:+.1%} "
          f"(positive = sigma-aware metric identifies genuinely closer games)")

    # Session-block bootstrap on the deviation gap.
    groups = defaultdict(list)
    for i, sid in enumerate(session_ids):
        groups[sid].append(i)
    blocks = list(groups.values())
    rng = random.Random(42)
    diffs = []
    for _ in range(1000):
        sample_idx = [i for _ in blocks for i in blocks[rng.randrange(len(blocks))]]
        sample_rows = [rows[i] for i in sample_idx]
        qp = quartile_by(sample_rows, "mu_diff", reverse=False)
        qs = quartile_by(sample_rows, "quality", reverse=True)
        dp = deviation_from_half(qp)
        ds = deviation_from_half(qs)
        if dp is None or ds is None:
            continue
        diffs.append(dp[0] - ds[0])
    diffs.sort()
    if diffs:
        pos = sum(d > 0 for d in diffs) / len(diffs)
        mean = sum(diffs) / len(diffs)
        lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]
        print(f"\nSession-block bootstrap ({len(diffs)} resamples): "
              f"mean gap {mean:+.1%}, 95% CI [{lo:+.1%}, {hi:+.1%}], "
              f"sigma-aware better in {pos:.0%} of resamples")


if __name__ == "__main__":
    main()
