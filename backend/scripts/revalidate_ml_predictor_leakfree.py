"""
Leak-free re-validation of the 12-feature LogisticRegression match predictor
(app/services/ml_predictor.py), run against the corrected match history
(post winner-determination fix, post-dedup, 2026-07-06).

Read-only against the live DB. See .moai/docs/ml-model-findings.md,
"2026-07-06: Retrain + leak-free re-validation" entry, for the hypothesis
this tests.

The live MLPredictor.train() builds features for past matches using each
player's CURRENT Player-row aggregates (today's mmr, win_rate, etc.) and
"recent N" queries with no upper time bound - both leak the match's own
outcome and everything since into its own features. This script rebuilds
the same 12 features from an in-memory chronological walk: per-player
rolling state is read to build a match's feature vector, THEN updated with
that match's outcome - so state used for match N only reflects matches < N.
mmr uses match_players.mmr_before directly (already a correct pre-match
snapshot) rather than a reconstructed proxy.
"""
import random
from collections import defaultdict, deque
from math import comb

import numpy as np
import sqlite3
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

DB = "file:/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db?mode=ro"
WINDOW = 20  # mirrors get_player_match_metrics_avg's limit=20
FORM_WINDOW = 10  # mirrors calculate_form_metrics's limit=10

FEATURE_NAMES = [
    "experience_diff", "sum_mmr_diff", "win_rate_diff", "combat_diff",
    "teamfight_diff", "aggression_diff", "minerals_diff", "supply_block_diff",
    "max_mmr_diff", "team_size_diff", "form_trend_diff", "spending_diff",
]


def load_data():
    conn = sqlite3.connect(DB, uri=True)
    rows = conn.execute("""
        SELECT mp.match_id, m.played_at, mp.team_number, mp.player_id, mp.won, mp.mmr_before
        FROM match_players mp JOIN matches m ON m.id = mp.match_id
        WHERE m.played_at IS NOT NULL
        ORDER BY m.played_at, mp.match_id
    """).fetchall()

    matches, order = {}, []
    for mid, played_at, team, pid, won, mmr_before in rows:
        if mid not in matches:
            matches[mid] = {"teams": {1: [], 2: []}, "winner": None}
            order.append(mid)
        matches[mid]["teams"][team].append((pid, mmr_before if mmr_before is not None else 1000.0))
        if won:
            matches[mid]["winner"] = team

    metric_rows = conn.execute("""
        SELECT mp.match_id, mp.player_id, pmm.combat_score, pmm.economic_score,
               pmm.team_fight_participation, pmm.aggression_score,
               pmm.minerals_collected, pmm.supply_block_seconds, pmm.overall_impact
        FROM match_players mp
        JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
    """).fetchall()
    metrics = {}
    for mid, pid, combat, econ, tf, aggro, minerals, supply, impact in metric_rows:
        metrics[(mid, pid)] = dict(
            combat_score=combat if combat is not None else 50.0,
            economic_score=econ if econ is not None else 50.0,
            teamfight_participation=tf if tf is not None else 0.5,
            aggression_score=aggro if aggro is not None else 50.0,
            minerals_collected=minerals if minerals is not None else 5000.0,
            supply_block_seconds=supply if supply is not None else 20.0,
            overall_impact=impact if impact is not None else 50.0,
        )
    conn.close()
    return matches, order, metrics


def build_dataset(matches, order, metrics):
    usable = [m for m in order
              if matches[m]["teams"][1] and matches[m]["teams"][2] and matches[m]["winner"]]

    total_games = defaultdict(int)
    wins = defaultdict(int)
    metric_hist = defaultdict(lambda: deque(maxlen=WINDOW))
    impact_hist = defaultdict(lambda: deque(maxlen=FORM_WINDOW))

    def player_state(pid):
        games = total_games[pid]
        win_rate = wins[pid] / games if games > 0 else 0.5
        hist = metric_hist[pid]
        if hist:
            combat = sum(h["combat_score"] for h in hist) / len(hist)
            econ = sum(h["economic_score"] for h in hist) / len(hist)
            tf = sum(h["teamfight_participation"] for h in hist) / len(hist)
            aggro = sum(h["aggression_score"] for h in hist) / len(hist)
            minerals = sum(h["minerals_collected"] for h in hist) / len(hist)
            supply = sum(h["supply_block_seconds"] for h in hist) / len(hist)
        else:
            combat, econ, tf, aggro, minerals, supply = 50.0, 50.0, 0.5, 50.0, 5000.0, 20.0
        impacts = list(impact_hist[pid])
        if len(impacts) >= 3:
            slope = np.polyfit(np.arange(len(impacts)), impacts, 1)[0]
            form_trend = max(min(slope / 10.0, 1.0), -1.0)
        else:
            form_trend = 0.0
        return dict(total_games=games, win_rate=win_rate, combat=combat, economic=econ,
                    teamfight=tf, aggression=aggro, minerals=minerals, supply=supply,
                    form_trend=form_trend)

    def team_features(pids_with_mmr):
        n = len(pids_with_mmr)
        states = [player_state(pid) for pid, _ in pids_with_mmr]
        mmrs = [mmr for _, mmr in pids_with_mmr]
        return dict(
            total_games=sum(s["total_games"] for s in states),
            avg_mmr=sum(mmrs) / n,
            team_size=n,
            avg_win_rate=sum(s["win_rate"] for s in states) / n,
            micro_composite=sum(s["combat"] for s in states) / n,
            macro_composite=sum(s["economic"] for s in states) / n,
            avg_teamfight_participation=sum(s["teamfight"] for s in states) / n,
            avg_aggression=sum(s["aggression"] for s in states) / n,
            avg_minerals=sum(s["minerals"] for s in states) / n,
            avg_supply_block=sum(s["supply"] for s in states) / n,
            max_mmr=max(mmrs),
            form_trend=sum(s["form_trend"] for s in states) / n,
        )

    def make_feature_vector(t1, t2):
        return np.array([
            (t1["total_games"] - t2["total_games"]) / 100,
            ((t1["avg_mmr"] * t1["team_size"]) - (t2["avg_mmr"] * t2["team_size"])) / 800,
            t1["avg_win_rate"] - t2["avg_win_rate"],
            (t1["micro_composite"] - t2["micro_composite"]) / 50,
            t1["avg_teamfight_participation"] - t2["avg_teamfight_participation"],
            (t2["avg_aggression"] - t1["avg_aggression"]) / 50,
            (t1["avg_minerals"] - t2["avg_minerals"]) / 1000,
            (t2["avg_supply_block"] - t1["avg_supply_block"]) / 30,
            (t1["max_mmr"] - t2["max_mmr"]) / 500,
            t1["team_size"] - t2["team_size"],
            t1["form_trend"] - t2["form_trend"],
            (t1["macro_composite"] - t2["macro_composite"]) / 50,
        ])

    X, y, mids = [], [], []
    baseline_sum_pred, baseline_avg_pred = [], []
    player_matches = defaultdict(set)

    for mid in usable:
        teams = matches[mid]["teams"]
        winner = matches[mid]["winner"]
        t1_ids, t2_ids = teams[1], teams[2]

        t1_feat = team_features(t1_ids)
        t2_feat = team_features(t2_ids)

        X.append(make_feature_vector(t1_feat, t2_feat))
        y.append(1 if winner == 1 else 0)
        mids.append(mid)

        sum1 = t1_feat["avg_mmr"] * t1_feat["team_size"]
        sum2 = t2_feat["avg_mmr"] * t2_feat["team_size"]
        baseline_sum_pred.append(1 if sum1 > sum2 else (2 if sum2 > sum1 else 0))
        baseline_avg_pred.append(
            1 if t1_feat["avg_mmr"] > t2_feat["avg_mmr"]
            else (2 if t2_feat["avg_mmr"] > t1_feat["avg_mmr"] else 0)
        )

        for pid, _ in t1_ids:
            player_matches[pid].add(mid)
        for pid, _ in t2_ids:
            player_matches[pid].add(mid)

        # Update rolling state AFTER building this match's features/prediction
        for team_num, pids in ((1, t1_ids), (2, t2_ids)):
            won_team = team_num == winner
            for pid, _ in pids:
                total_games[pid] += 1
                if won_team:
                    wins[pid] += 1
                m = metrics.get((mid, pid))
                if m:
                    metric_hist[pid].append(m)
                    impact_hist[pid].append(m["overall_impact"])

    return (np.array(X), np.array(y), mids,
            np.array(baseline_sum_pred), np.array(baseline_avg_pred), player_matches)


def measure_baseline(y, baseline_pred, label):
    ties = int(np.sum(baseline_pred == 0))
    decided = baseline_pred != 0
    n = int(decided.sum())
    actual = np.where(y == 1, 1, 2)
    correct = int((baseline_pred[decided] == actual[decided]).sum())
    print(f"  {label}: {correct}/{n} = {correct/n:.1%}  (ties excluded: {ties})")
    return correct, n, baseline_pred, actual


def mcnemar_exact(pred_a, pred_b, actual):
    # int(...) casts: numpy int64 arithmetic overflows/wraps in 2**n for n>~63,
    # silently producing 0 and a ZeroDivisionError - use plain Python bigints.
    b = int(sum(bool(pa == w and pb != w) for pa, pb, w in zip(pred_a, pred_b, actual)))
    c = int(sum(bool(pb == w and pa != w) for pa, pb, w in zip(pred_a, pred_b, actual)))
    n, k = b + c, min(b, c)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return b, c, p


def main():
    print("Loading match data (read-only)...")
    matches, order, metrics = load_data()
    print(f"Distinct matches: {len(order)}")

    X, y, mids, baseline_sum_pred, baseline_avg_pred, player_matches = build_dataset(
        matches, order, metrics
    )
    print(f"Usable matches (2 teams, real winner): {len(mids)}")
    print(f"Feature matrix: {X.shape}")

    print("\n=== Recipe 1: Baseline (freshly measured, corrected data) ===")
    _, _, sum_pred_decided, actual = measure_baseline(y, baseline_sum_pred, "team-sum mmr_before")
    _, _, avg_pred_decided, _ = measure_baseline(y, baseline_avg_pred, "team-average mmr_before")

    print("\n=== Recipe 2: 5-fold CV, LogisticRegression(C=1.0), leak-free features ===")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(LogisticRegression(C=1.0, max_iter=1000), X, y, cv=cv)
    print(f"  {scores.mean():.1%} +/- {scores.std():.1%} across folds: {scores.round(3)}")

    print("\n=== Recipe 8: quick model shootout (same leak-free features) ===")
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    for name, model in [
        ("LogisticRegression C=1.0", LogisticRegression(C=1.0, max_iter=1000)),
        ("LogisticRegression C=0.1", LogisticRegression(C=0.1, max_iter=1000)),
        ("GradientBoosting (shallow)", GradientBoostingClassifier(max_depth=2, n_estimators=50, random_state=42)),
        ("RandomForest (shallow)", RandomForestClassifier(max_depth=3, n_estimators=100, random_state=42)),
    ]:
        s = cross_val_score(model, X, y, cv=cv)
        print(f"  {name:28s}: {s.mean():.1%} +/- {s.std():.1%}")

    print("\n=== Recipe 3: LOPO (players with >=30 match appearances) ===")
    core_players = [pid for pid, ms in player_matches.items() if len(ms) >= 30]
    print(f"  {len(core_players)} core players qualify")
    mid_to_idx = {m: i for i, m in enumerate(mids)}
    deltas = []
    for pid in core_players:
        held_idx = [mid_to_idx[m] for m in player_matches[pid] if m in mid_to_idx]
        train_idx = [i for i in range(len(mids)) if i not in set(held_idx)]
        if len(held_idx) < 5 or len(train_idx) < 30:
            continue
        model = LogisticRegression(C=1.0, max_iter=1000)
        model.fit(X[train_idx], y[train_idx])
        model_acc = model.score(X[held_idx], y[held_idx])
        held_actual = np.where(y[held_idx] == 1, 1, 2)
        held_baseline_pred = baseline_sum_pred[held_idx]
        decided = held_baseline_pred != 0
        if decided.sum() == 0:
            continue
        baseline_acc = (held_baseline_pred[decided] == held_actual[decided]).mean()
        deltas.append(model_acc - baseline_acc)
    if deltas:
        pos = sum(d > 0 for d in deltas)
        print(f"  mean delta {sum(deltas)/len(deltas):+.1%}, positive for {pos}/{len(deltas)} players")
    else:
        print("  not enough held-out data per player to run LOPO")

    print("\n=== Recipe 4: Bootstrap CI (model vs team-sum baseline, 1000 resamples) ===")
    random.seed(42)
    model_full = LogisticRegression(C=1.0, max_iter=1000)
    model_full.fit(X, y)
    model_pred_all = np.where(model_full.predict(X) == 1, 1, 2)
    diffs = []
    n_total = len(mids)
    for _ in range(1000):
        idx = [random.randrange(n_total) for _ in range(n_total)]
        idx = np.array(idx)
        decided = baseline_sum_pred[idx] != 0
        if decided.sum() == 0:
            continue
        actual_s = np.where(y[idx] == 1, 1, 2)
        b_acc = (baseline_sum_pred[idx][decided] == actual_s[decided]).mean()
        m_acc = (model_pred_all[idx] == actual_s).mean()
        diffs.append(m_acc - b_acc)
    diffs.sort()
    pos = sum(d > 0 for d in diffs) / len(diffs)
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]
    print(f"  mean {sum(diffs)/len(diffs):+.1%}, 95% CI [{lo:+.1%}, {hi:+.1%}], positive in {pos:.0%} of resamples")
    print("  (in-sample model fit used for this CI's point predictions - a bias in the model's favor;")
    print("   the 5-fold CV number above is the honest out-of-sample estimate)")

    print("\n=== Recipe 10: McNemar exact test, model (CV out-of-fold) vs team-sum baseline ===")
    # Build honest out-of-fold model predictions for a fair paired test
    from sklearn.model_selection import cross_val_predict
    oof_pred_label = cross_val_predict(LogisticRegression(C=1.0, max_iter=1000), X, y, cv=cv)
    oof_pred = np.where(oof_pred_label == 1, 1, 2)
    actual_all = np.where(y == 1, 1, 2)
    decided = baseline_sum_pred != 0
    b, c, p = mcnemar_exact(baseline_sum_pred[decided], oof_pred[decided], actual_all[decided])
    print(f"  baseline-only-right={b}, model-only-right={c}, n_disagree={b+c}, exact p={p:.4f}")
    oof_acc = (oof_pred[decided] == actual_all[decided]).mean()
    base_acc = (baseline_sum_pred[decided] == actual_all[decided]).mean()
    print(f"  out-of-fold model accuracy: {oof_acc:.1%} vs baseline {base_acc:.1%} (delta {oof_acc-base_acc:+.1%})")


if __name__ == "__main__":
    main()
