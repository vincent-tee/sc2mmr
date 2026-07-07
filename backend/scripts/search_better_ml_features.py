"""
Hypothesis 2 (2026-07-06 session, following the leak-free re-validation):
does any currently-unused metric add real incremental CV value on top of the
existing 12 leak-free features, or does a different model class help?

Predicted: given 4 model classes already tied with baseline on the current
12 features (see ml-model-findings.md), and given this project's own history
(algorithm-shopping alone has never helped at small n), I predict NO
individual candidate feature or model swap moves 5-fold CV accuracy by more
than ~1pp - the ceiling is signal-limited, not model-limited.

Kill criterion: same as the first experiment - a candidate only counts as a
real find if its CV-with-vs-without delta is >= +1.0pp AND positive in a
clear majority of a 200-resample bootstrap.

Read-only. Reuses the leak-free chronological walk from
revalidate_ml_predictor_leakfree.py, extended with additional candidate
per-player rolling metrics not in the current 12-feature set.
"""
import random
from collections import defaultdict, deque

import numpy as np
import sqlite3
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

DB = "file:/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db?mode=ro"
WINDOW = 20

BASE_FEATURE_NAMES = [
    "experience_diff", "sum_mmr_diff", "win_rate_diff", "combat_diff",
    "teamfight_diff", "aggression_diff", "minerals_diff", "supply_block_diff",
    "max_mmr_diff", "team_size_diff", "form_trend_diff", "spending_diff",
]

CANDIDATES = ["apm", "kill_death_ratio", "damage_ratio", "spending_efficiency",
              "workers_created", "army_net_efficiency"]


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
               pmm.minerals_collected, pmm.supply_block_seconds, pmm.overall_impact,
               pmm.apm, pmm.kill_death_ratio, pmm.damage_ratio, pmm.spending_efficiency,
               pmm.workers_created, pmm.army_value_killed, pmm.army_value_lost
        FROM match_players mp
        JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
    """).fetchall()
    metrics = {}
    for (mid, pid, combat, econ, tf, aggro, minerals, supply, impact,
         apm, kd, dmg_ratio, spend_eff, workers, army_killed, army_lost) in metric_rows:
        army_total = (army_killed or 0) + (army_lost or 0)
        army_net = (army_killed / army_total) if army_total > 0 else 0.5
        metrics[(mid, pid)] = dict(
            combat_score=combat if combat is not None else 50.0,
            economic_score=econ if econ is not None else 50.0,
            teamfight_participation=tf if tf is not None else 0.5,
            aggression_score=aggro if aggro is not None else 50.0,
            minerals_collected=minerals if minerals is not None else 5000.0,
            supply_block_seconds=supply if supply is not None else 20.0,
            overall_impact=impact if impact is not None else 50.0,
            apm=apm if apm is not None else 100.0,
            kill_death_ratio=min(kd, 10.0) if kd is not None else 1.0,
            damage_ratio=min(dmg_ratio, 10.0) if dmg_ratio is not None else 1.0,
            spending_efficiency=spend_eff if spend_eff is not None else 0.5,
            workers_created=workers if workers is not None else 20.0,
            army_net_efficiency=army_net,
        )
    conn.close()
    return matches, order, metrics


def build_dataset(matches, order, metrics):
    usable = [m for m in order
              if matches[m]["teams"][1] and matches[m]["teams"][2] and matches[m]["winner"]]

    total_games = defaultdict(int)
    wins = defaultdict(int)
    hist = defaultdict(lambda: deque(maxlen=WINDOW))
    impact_hist = defaultdict(lambda: deque(maxlen=10))

    def player_state(pid):
        games = total_games[pid]
        win_rate = wins[pid] / games if games > 0 else 0.5
        h = hist[pid]
        if h:
            avg = {k: sum(x[k] for x in h) / len(h) for k in CANDIDATES + [
                "combat_score", "economic_score", "teamfight_participation",
                "aggression_score", "minerals_collected", "supply_block_seconds"]}
        else:
            avg = dict(combat_score=50.0, economic_score=50.0, teamfight_participation=0.5,
                       aggression_score=50.0, minerals_collected=5000.0, supply_block_seconds=20.0,
                       apm=100.0, kill_death_ratio=1.0, damage_ratio=1.0,
                       spending_efficiency=0.5, workers_created=20.0, army_net_efficiency=0.5)
        impacts = list(impact_hist[pid])
        if len(impacts) >= 3:
            slope = np.polyfit(np.arange(len(impacts)), impacts, 1)[0]
            form_trend = max(min(slope / 10.0, 1.0), -1.0)
        else:
            form_trend = 0.0
        return dict(total_games=games, win_rate=win_rate, form_trend=form_trend, **avg)

    def team_state(rows):
        n = len(rows)
        states = [player_state(pid) for pid, _ in rows]
        mmrs = [mmr for _, mmr in rows]
        out = dict(
            total_games=sum(s["total_games"] for s in states),
            avg_mmr=sum(mmrs) / n, team_size=n,
            avg_win_rate=sum(s["win_rate"] for s in states) / n,
            micro_composite=sum(s["combat_score"] for s in states) / n,
            macro_composite=sum(s["economic_score"] for s in states) / n,
            avg_teamfight_participation=sum(s["teamfight_participation"] for s in states) / n,
            avg_aggression=sum(s["aggression_score"] for s in states) / n,
            avg_minerals=sum(s["minerals_collected"] for s in states) / n,
            avg_supply_block=sum(s["supply_block_seconds"] for s in states) / n,
            max_mmr=max(mmrs), form_trend=sum(s["form_trend"] for s in states) / n,
        )
        for c in CANDIDATES:
            out[c] = sum(s[c] for s in states) / n
        return out

    def base_vector(t1, t2):
        return [
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
        ]

    X_base, y, cand_cols = [], [], {c: [] for c in CANDIDATES}

    for mid in usable:
        teams = matches[mid]["teams"]
        winner = matches[mid]["winner"]
        t1_ids, t2_ids = teams[1], teams[2]
        t1_feat, t2_feat = team_state(t1_ids), team_state(t2_ids)

        X_base.append(base_vector(t1_feat, t2_feat))
        y.append(1 if winner == 1 else 0)
        for c in CANDIDATES:
            cand_cols[c].append(t1_feat[c] - t2_feat[c])

        for team_num, rows in ((1, t1_ids), (2, t2_ids)):
            won_team = team_num == winner
            for pid, _ in rows:
                total_games[pid] += 1
                if won_team:
                    wins[pid] += 1
                m = metrics.get((mid, pid))
                if m:
                    hist[pid].append(m)
                    impact_hist[pid].append(m["overall_impact"])

    return np.array(X_base), np.array(y), {c: np.array(v) for c, v in cand_cols.items()}


def main():
    print("Loading and building leak-free dataset + candidate features...")
    matches, order, metrics = load_data()
    X_base, y, candidates = build_dataset(matches, order, metrics)
    print(f"n={len(y)}, base features={X_base.shape[1]}, candidates={list(candidates.keys())}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    model = LogisticRegression(C=1.0, max_iter=1000)

    base_scores = cross_val_score(model, X_base, y, cv=cv)
    base_acc = base_scores.mean()
    print(f"\nBase 12 features: {base_acc:.1%} +/- {base_scores.std():.1%}")

    print("\n=== Recipe 7: incremental CV value of each candidate (base+1 vs base) ===")
    results = []
    for name, col in candidates.items():
        X_plus = np.column_stack([X_base, col])
        scores = cross_val_score(model, X_plus, y, cv=cv)
        delta = scores.mean() - base_acc
        results.append((name, scores.mean(), delta))
        print(f"  +{name:22s}: {scores.mean():.1%} (delta {delta:+.1%})")

    results.sort(key=lambda r: -r[2])
    best_name, best_acc, best_delta = results[0]
    print(f"\nBest single candidate: {best_name} ({best_delta:+.1%})")

    print("\n=== Bootstrap check on best candidate (200 resamples, in-sample) ===")
    random.seed(42)
    X_plus_best = np.column_stack([X_base, candidates[best_name]])
    n = len(y)
    pos = 0
    for _ in range(200):
        idx = np.array([random.randrange(n) for _ in range(n)])
        m_base = LogisticRegression(C=1.0, max_iter=1000).fit(X_base[idx], y[idx])
        m_plus = LogisticRegression(C=1.0, max_iter=1000).fit(X_plus_best[idx], y[idx])
        if m_plus.score(X_plus_best[idx], y[idx]) > m_base.score(X_base[idx], y[idx]):
            pos += 1
    print(f"  best candidate ({best_name}) improved in-sample fit in {pos}/200 resamples")

    print("\n=== Trying combined top-2 candidates together ===")
    top2 = [r[0] for r in results[:2]]
    X_top2 = np.column_stack([X_base] + [candidates[c] for c in top2])
    scores_top2 = cross_val_score(model, X_top2, y, cv=cv)
    print(f"  base + {top2}: {scores_top2.mean():.1%} (delta {scores_top2.mean() - base_acc:+.1%})")

    print("\n=== Model shootout on base+best-candidate feature set ===")
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
    from sklearn.svm import SVC
    from sklearn.naive_bayes import GaussianNB
    for name, m in [
        ("LogisticRegression C=1.0", LogisticRegression(C=1.0, max_iter=1000)),
        ("SVC (RBF, calibrated)", SVC(probability=True, random_state=42)),
        ("GaussianNB", GaussianNB()),
        ("GradientBoosting (shallow)", GradientBoostingClassifier(max_depth=2, n_estimators=50, random_state=42)),
        ("RandomForest (shallow)", RandomForestClassifier(max_depth=3, n_estimators=100, random_state=42)),
        ("ExtraTrees (shallow)", ExtraTreesClassifier(max_depth=3, n_estimators=100, random_state=42)),
    ]:
        s = cross_val_score(m, X_plus_best, y, cv=cv)
        print(f"  {name:28s}: {s.mean():.1%} +/- {s.std():.1%}")


if __name__ == "__main__":
    main()
