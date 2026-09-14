"""Read-only: does teammate chemistry add predictive value beyond rating?

Frontier item 3 in .claude/skills/sc2mmr-research-frontier/SKILL.md, run under
sc2mmr-research-methodology Rule 1 (predict-before-running) and Rule 3
(assigned adversarial refutation before trusting any positive result).

## Hypothesis (written before this script's numbers were seen)
Pairs who have played many games together as teammates win more than their
individual win rates alone would predict (positive synergy residual), and
adding this residual to a rating-based win-probability model improves
held-out log loss on strictly later, unseen sessions.

## Mechanism
Repeated teammates develop non-transferable coordination (callouts, split
map responsibilities, complementary races) that individual skill ratings
cannot see. If real, teams built from high-synergy pairs should win more
than rating alone predicts, and this should survive holding out synergy's
own future games (no target leakage) and controlling for each player's own
win rate (no "two good players" confound -- see Rule 2/3 of the methodology
skill: a raw together-win-rate correlation would just be restating skill).

## Predicted numbers (written before running)
- Baseline: rating-only win probability, calibrated on the SAME train split
  used below (not reused from a different script's numbers -- Rule 3 item 5).
- Kill criterion: if adding the synergy feature does not reduce held-out log
  loss versus the rating-only model on the last 25% of sessions, or the
  session-block bootstrap CI on that reduction includes zero, this idea is
  dead. Given only 112-163 pairs have >=10 shared games (per the frontier
  skill's verified inventory) and even fewer will co-occur in the held-out
  window, a null result is the more likely outcome going in.

## Anti-leakage design (methodology Rule 3 leak taxonomy)
- Pair "together" stats and each player's individual win rate are running
  totals built ONLY from strictly prior matches (chronological single pass;
  see `_history_before` below) -- never the cached, current-day
  player_synergies table, which would leak each pair's own future games.
- Synergy residual = together_win_rate - expected_win_rate_from_individuals,
  not raw together_win_rate, specifically to net out "two good players"
  before crediting anything to synergy.
- Same session-based chronological 75/25 split as walkforward_session_eval.py
  and the same win_probability/decay policy, so this is a true incremental-
  value test against the existing rating-of-record, not a separate baseline.
"""
import random
import sqlite3
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

import trueskill

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.rating_policy import decayed_sigma, typical_session_gap, win_probability, rate_teams
from walkforward_session_eval import load_matches, assign_sessions, log_loss, DB

MIN_TOGETHER_GAMES = 5   # per frontier skill's own synergy-pair threshold
MIN_INDIV_GAMES = 10     # need a stable individual win-rate estimate first


def logit(p, eps=1e-9):
    p = min(max(p, eps), 1 - eps)
    return __import__("math").log(p / (1 - p))


def sigmoid(x):
    import math
    return 1 / (1 + math.exp(-x))


def team_synergy_residual(team_ids, pair_stats, indiv_stats):
    """Average (together_wr - expected_wr_from_individuals) over qualifying
    pairs on this team, using only history strictly before this match."""
    residuals = []
    for i, j in combinations(sorted(team_ids), 2):
        together = pair_stats.get((i, j))
        indiv_i, indiv_j = indiv_stats.get(i), indiv_stats.get(j)
        if (not together or together["games"] < MIN_TOGETHER_GAMES
                or not indiv_i or indiv_i["games"] < MIN_INDIV_GAMES
                or not indiv_j or indiv_j["games"] < MIN_INDIV_GAMES):
            continue
        together_wr = together["wins"] / together["games"]
        expected_wr = ((indiv_i["wins"] / indiv_i["games"]) + (indiv_j["wins"] / indiv_j["games"])) / 2
        residuals.append(together_wr - expected_wr)
    return sum(residuals) / len(residuals) if residuals else 0.0, len(residuals)


def build_dataset(usable):
    ratings = defaultdict(lambda: trueskill.Rating(mu=25.0, sigma=8.333))
    history = defaultdict(list)
    pair_stats = defaultdict(lambda: {"games": 0, "wins": 0})   # keyed (min_id, max_id) -> games/wins FOR THAT PAIR TOGETHER (either team)
    indiv_stats = defaultdict(lambda: {"games": 0, "wins": 0})

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

        syn1, n1 = team_synergy_residual(t1_ids, pair_stats, indiv_stats)
        syn2, n2 = team_synergy_residual(t2_ids, pair_stats, indiv_stats)

        rows.append(dict(
            mid=mid, win_prob=p1, outcome=1 if winner == t1 else 0,
            synergy_diff=syn1 - syn2, n_qualifying_pairs=n1 + n2,
        ))

        # advance ratings with the real outcome
        new_t1, new_t2 = rate_teams(t1_ratings, t2_ratings, winner == t1)
        for pid, r in zip(t1_ids, new_t1):
            ratings[pid] = r
        for pid, r in zip(t2_ids, new_t2):
            ratings[pid] = r
        for pid in t1_ids + t2_ids:
            history[pid].append(now)

        # THEN update pair/individual running history with this match's real result
        t1_won = winner == t1
        for i, j in combinations(sorted(t1_ids), 2):
            pair_stats[(i, j)]["games"] += 1
            pair_stats[(i, j)]["wins"] += int(t1_won)
        for i, j in combinations(sorted(t2_ids), 2):
            pair_stats[(i, j)]["games"] += 1
            pair_stats[(i, j)]["wins"] += int(not t1_won)
        for pid in t1_ids:
            indiv_stats[pid]["games"] += 1
            indiv_stats[pid]["wins"] += int(t1_won)
        for pid in t2_ids:
            indiv_stats[pid]["games"] += 1
            indiv_stats[pid]["wins"] += int(not t1_won)

    return rows


def fit_1d_logistic(x, y, lr=0.1, iters=2000):
    """Single-feature logistic regression via gradient descent (no external
    ML dependency needed for one coefficient + intercept)."""
    a, b = 0.0, 1.0  # intercept, slope (slope starts at 1 = trust the input as-is)
    n = len(x)
    for _ in range(iters):
        grad_a = grad_b = 0.0
        for xi, yi in zip(x, y):
            pred = sigmoid(a + b * xi)
            err = pred - yi
            grad_a += err
            grad_b += err * xi
        a -= lr * grad_a / n
        b -= lr * grad_b / n
    return a, b


def main():
    con = sqlite3.connect(DB, uri=True)
    usable = load_matches(con)
    con.close()
    session_ids = assign_sessions(usable)
    sessions = sorted(set(session_ids))
    print(f"Loaded {len(usable)} usable matches, {len(sessions)} sessions")
    if len(sessions) < 8:
        print("Not enough sessions for a holdout split.")
        return

    rows = build_dataset(usable)
    cutoff = sessions[max(1, int(len(sessions) * .75))]
    train_idx = [i for i, sid in enumerate(session_ids) if sid < cutoff]
    test_idx = [i for i, sid in enumerate(session_ids) if sid >= cutoff]
    print(f"Train: {len(train_idx)} matches (sessions < {cutoff}); "
          f"Test: {len(test_idx)} matches (sessions >= {cutoff})")

    test_with_pairs = sum(1 for i in test_idx if rows[i]["n_qualifying_pairs"] > 0)
    print(f"Test matches with >=1 qualifying synergy pair on either team: "
          f"{test_with_pairs}/{len(test_idx)}")

    # Baseline: recalibrate rating-only logit on TRAIN, evaluate on TEST.
    train_logit = [logit(rows[i]["win_prob"]) for i in train_idx]
    train_y = [rows[i]["outcome"] for i in train_idx]
    a0, b0 = fit_1d_logistic(train_logit, train_y)

    test_logit = [logit(rows[i]["win_prob"]) for i in test_idx]
    test_y = [rows[i]["outcome"] for i in test_idx]
    baseline_probs = [sigmoid(a0 + b0 * x) for x in test_logit]
    baseline_ll = log_loss(baseline_probs, test_y)

    # Candidate: 2-feature logistic (rating logit + synergy diff) fit on TRAIN.
    from sklearn.linear_model import LogisticRegression
    X_train = [[logit(rows[i]["win_prob"]), rows[i]["synergy_diff"]] for i in train_idx]
    model = LogisticRegression()
    model.fit(X_train, train_y)
    X_test = [[logit(rows[i]["win_prob"]), rows[i]["synergy_diff"]] for i in test_idx]
    candidate_probs = [p[1] for p in model.predict_proba(X_test)]
    candidate_ll = log_loss(candidate_probs, test_y)

    print(f"\nRating-only (recalibrated), held-out log loss: {baseline_ll:.4f}")
    print(f"Rating + synergy residual, held-out log loss:   {candidate_ll:.4f}")
    print(f"Synergy coefficient (train fit): {model.coef_[0][1]:+.4f} "
          f"(positive = higher synergy residual predicts more wins, as hypothesized)")
    print(f"Log loss improvement (baseline - candidate): {baseline_ll - candidate_ll:+.4f} "
          f"(positive = synergy helped)")

    # Session-block bootstrap on the log-loss improvement, TEST set only.
    groups = defaultdict(list)
    for i in test_idx:
        groups[session_ids[i]].append(i)
    blocks = list(groups.values())
    rng = random.Random(42)
    diffs = []
    for _ in range(1000):
        sample = [i for _ in blocks for i in blocks[rng.randrange(len(blocks))]]
        y = [rows[i]["outcome"] for i in sample]
        base_p = [sigmoid(a0 + b0 * logit(rows[i]["win_prob"])) for i in sample]
        cand_p = [p[1] for p in model.predict_proba(
            [[logit(rows[i]["win_prob"]), rows[i]["synergy_diff"]] for i in sample])]
        diffs.append(log_loss(base_p, y) - log_loss(cand_p, y))
    diffs.sort()
    mean = sum(diffs) / len(diffs)
    lo, hi = diffs[24], diffs[974]
    pos = sum(d > 0 for d in diffs) / len(diffs)
    print(f"\nSession-block bootstrap (1000 resamples) on log-loss improvement: "
          f"mean {mean:+.4f}, 95% CI [{lo:+.4f}, {hi:+.4f}], "
          f"synergy helped in {pos:.0%} of resamples")

    print("\nVerdict:", "SURVIVES first look (CI excludes zero, positive direction)"
          if lo > 0 else "DOES NOT SURVIVE (CI includes zero or is negative) -- per the "
                         "pre-registered kill criterion, this idea is dead as stated.")


if __name__ == "__main__":
    main()
