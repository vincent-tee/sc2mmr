"""Test a specific, pre-registered fix for the mu-vs-residual correlation
found in all_players_residual_scan.py (r=+0.56 to +0.61, both datasets,
robust to removing the top outlier): the model's win_probability formula
adds a FIXED performance-variance term (n_players * beta^2) regardless of
how converged a player's rating is, so strong/converged players get more
predicted uncertainty than they apparently deserve, and weak/unconverged
players get less.

## Hypothesis
Replacing the fixed beta term with one that scales with each player's own
sigma (so a converged player contributes less extra variance, an
unconverged one contributes more) will reduce the mu-residual correlation
and improve held-out calibration, versus the current fixed-beta formula.

## Candidate formula
variance = sum(sigma_i^2) * (1 + k)   [replaces + n_players*beta^2]
k is the one free parameter, fit by grid search on log loss on the EARLIER
75% of sessions only, then frozen and evaluated on the untouched last 25%.

## Kill criterion
Dead if held-out log loss does not improve with a session-block bootstrap
CI excluding zero, OR if the mu-residual correlation on the held-out set
does not shrink toward zero versus the current formula.
"""
import math
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from datetime import datetime

import trueskill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.rating_policy import decayed_sigma, typical_session_gap, rate_teams
from walkforward_session_eval import load_matches, assign_sessions, log_loss, DB


def candidate_win_prob(team1, team2, k):
    delta = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    variance = sum(r.sigma ** 2 for r in team1 + team2) * (1 + k)
    return 0.5 * (1 + math.erf(delta / math.sqrt(2 * variance)))


def baseline_win_prob(team1, team2, beta=5.0):
    delta = sum(r.mu for r in team1) - sum(r.mu for r in team2)
    variance = sum(r.sigma ** 2 for r in team1 + team2)
    variance += (len(team1) + len(team2)) * beta ** 2
    return 0.5 * (1 + math.erf(delta / math.sqrt(2 * variance)))


def build_dataset(usable):
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
                old.sigma, days, len(prior_times), typical_session_gap(prior_times + [now])))
        t1r = [ratings[pid] for pid in t1_ids]
        t2r = [ratings[pid] for pid in t2_ids]
        outcome = 1 if winner == t1 else 0
        avg_mu = (sum(r.mu for r in t1r) + sum(r.mu for r in t2r)) / (len(t1r) + len(t2r))
        rows.append(dict(t1r=t1r, t2r=t2r, outcome=outcome, avg_mu=avg_mu))
        new_t1, new_t2 = rate_teams(t1r, t2r, winner == t1)
        for pid, r in zip(t1_ids, new_t1):
            ratings[pid] = r
        for pid, r in zip(t2_ids, new_t2):
            ratings[pid] = r
        for pid in t1_ids + t2_ids:
            history[pid].append(now)
    return rows


def mu_residual_correlation(rows, probs):
    """Correlation between each match's average mu and (outcome - predicted prob),
    signed toward team1. Positive = model underpredicts strong teams, as found."""
    resids = [r["outcome"] - p for r, p in zip(rows, probs)]
    mus = [r["avg_mu"] for r in rows]
    n = len(rows)
    mean_mu, mean_r = sum(mus) / n, sum(resids) / n
    cov = sum((m - mean_mu) * (rr - mean_r) for m, rr in zip(mus, resids))
    sd_mu = sum((m - mean_mu) ** 2 for m in mus) ** 0.5
    sd_r = sum((rr - mean_r) ** 2 for rr in resids) ** 0.5
    return cov / (sd_mu * sd_r) if sd_mu > 0 and sd_r > 0 else 0.0


def run(label, path):
    con = sqlite3.connect(path, uri=True)
    usable = load_matches(con)
    con.close()
    session_ids = assign_sessions(usable)
    sessions = sorted(set(session_ids))
    rows = build_dataset(usable)
    cutoff = sessions[max(1, int(len(sessions) * .75))]
    train_idx = [i for i, sid in enumerate(session_ids) if sid < cutoff]
    test_idx = [i for i, sid in enumerate(session_ids) if sid >= cutoff]

    print(f"\n=== {label}: train={len(train_idx)}, test={len(test_idx)} ===")

    # Grid search k on TRAIN only. Wide sweep first (0..1000, checked in
    # scratch analysis to confirm log loss bottoms out and rises again --
    # not a runaway toward infinite variance), then refine near the minimum.
    outcomes_train = [rows[i]["outcome"] for i in train_idx]

    def train_ll(k):
        probs = [candidate_win_prob(rows[i]["t1r"], rows[i]["t2r"], k) for i in train_idx]
        return log_loss(probs, outcomes_train)

    coarse_grid = [0, 1, 2, 3, 5, 8, 10, 12, 15, 20, 30, 50, 100, 300, 1000]
    coarse_best_k = min(coarse_grid, key=train_ll)
    fine_grid = [coarse_best_k + d for d in range(-4, 5)] if coarse_best_k > 4 else [x * 0.5 for x in range(0, 20)]
    best_k = min(fine_grid, key=train_ll)
    best_ll = train_ll(best_k)
    print(f"Best k on train: {best_k} (train log loss {best_ll:.4f}, coarse-grid best was {coarse_best_k})")

    # Evaluate BOTH formulas on TEST, frozen.
    baseline_probs = [baseline_win_prob(rows[i]["t1r"], rows[i]["t2r"]) for i in test_idx]
    candidate_probs = [candidate_win_prob(rows[i]["t1r"], rows[i]["t2r"], best_k) for i in test_idx]
    test_outcomes = [rows[i]["outcome"] for i in test_idx]
    test_rows = [rows[i] for i in test_idx]

    baseline_ll = log_loss(baseline_probs, test_outcomes)
    candidate_ll = log_loss(candidate_probs, test_outcomes)
    baseline_corr = mu_residual_correlation(test_rows, baseline_probs)
    candidate_corr = mu_residual_correlation(test_rows, candidate_probs)

    print(f"Held-out log loss: baseline(beta=5.0)={baseline_ll:.4f}  candidate(k={best_k})={candidate_ll:.4f}  "
          f"improvement={baseline_ll-candidate_ll:+.4f}")
    print(f"Held-out mu-residual correlation: baseline={baseline_corr:+.3f}  candidate={candidate_corr:+.3f}")

    # Session-block bootstrap on the log-loss improvement.
    groups = defaultdict(list)
    for i in test_idx:
        groups[session_ids[i]].append(i)
    blocks = list(groups.values())
    rng = random.Random(42)
    diffs = []
    for _ in range(1000):
        sample = [i for _ in blocks for i in blocks[rng.randrange(len(blocks))]]
        y = [rows[i]["outcome"] for i in sample]
        bp = [baseline_win_prob(rows[i]["t1r"], rows[i]["t2r"]) for i in sample]
        cp = [candidate_win_prob(rows[i]["t1r"], rows[i]["t2r"], best_k) for i in sample]
        diffs.append(log_loss(bp, y) - log_loss(cp, y))
    diffs.sort()
    mean = sum(diffs) / len(diffs)
    lo, hi = diffs[24], diffs[974]
    pos = sum(d > 0 for d in diffs) / len(diffs)
    print(f"Session-block bootstrap (1000 resamples) on log-loss improvement: "
          f"mean {mean:+.4f}, 95% CI [{lo:+.4f}, {hi:+.4f}], candidate better in {pos:.0%} of resamples")

    survives = lo > 0 and abs(candidate_corr) < abs(baseline_corr)
    print("Verdict:", "SURVIVES (log-loss CI excludes zero AND correlation shrank)" if survives
          else "DOES NOT SURVIVE per pre-registered kill criterion")
    return survives


if __name__ == "__main__":
    r1 = run("local dev", DB)
    r2 = run("prod", "file:/home/vtee/.claude/jobs/969106c5/tmp/prod-before.db?mode=ro")
