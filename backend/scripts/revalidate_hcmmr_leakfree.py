"""
Leak-free re-validation of HC-MMR / unified-MMR outperformance-based rating
correction against plain display MMR, on today's corrected match history
(post winner-fix, post-dedup, 2026-07-06).

See docs/superpowers/campaign/rating-consolidation-log.md, "Session 6" entry,
for the hypothesis this tests. Prior campaign numbers (60.6-60.8% for the
unified-MMR arms) were measured before today's data corrections.

Formula ported from app/services/handicap_mmr_service.py, but reconstructed
chronologically: each player's outperformance is computed using ONLY matches
strictly before the one being predicted, with recency weight relative to
THAT match's date - not datetime.utcnow(), which is what the production
service uses (itself a lookahead source for any retrospective validation).

Read-only against the live DB.
"""
import random
from collections import defaultdict
from math import comb, pow as mpow

import numpy as np
import sqlite3

MIN_GAMES = 15
OUTPERFORMANCE_MULTIPLIER = 3000
DB = "file:/home/vtee/projects/sc2mmr/backend/data/sc2mmr.db?mode=ro"


def recency_weight(days_ago: float) -> float:
    # RatingSystem.calculate_recency_weight: 0.5 ** (days / half_life), half_life=90
    return 0.5 ** (days_ago / 90.0)


def expected_win_rate(handicap_per_player: float, team_size: int) -> float:
    dampening = 1.0 / (1.0 + (team_size - 1) * 0.15)
    return 1.0 / (1.0 + 10 ** (-(handicap_per_player * dampening) / 400))


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
            matches[mid] = {"teams": {1: [], 2: []}, "winner": None, "played_at": played_at}
            order.append(mid)
        matches[mid]["teams"][team].append((pid, mmr_before if mmr_before is not None else 1000.0))
        if won:
            matches[mid]["winner"] = team
    conn.close()
    return matches, order


def parse_dt(s):
    from datetime import datetime
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f" if "." in s else "%Y-%m-%d %H:%M:%S")


def build_predictions(matches, order):
    usable = [m for m in order
              if matches[m]["teams"][1] and matches[m]["teams"][2] and matches[m]["winner"]]

    # Per player: list of (played_at:datetime, handicap_per_player, won:bool)
    history = defaultdict(list)
    # Per player: last match's played_at (for inactivity weight)
    last_played = {}

    plain_pred, hc_pred, actual = [], [], []

    for mid in usable:
        m = matches[mid]
        teams = m["teams"]
        winner = m["winner"]
        cur_dt = parse_dt(m["played_at"])
        t1, t2 = teams[1], teams[2]

        # --- plain team-sum mmr_before ---
        sum1_plain = sum(mmr for _, mmr in t1)
        sum2_plain = sum(mmr for _, mmr in t2)
        plain_pred.append(1 if sum1_plain > sum2_plain else (2 if sum2_plain > sum1_plain else 0))
        actual.append(1 if winner == 1 else 2)

        # --- HC-MMR-adjusted team sum (leak-free: history strictly before cur_dt) ---
        def hc_mmr_for(pid: int, plain_mmr: float) -> float:
            hist = history[pid]
            if len(hist) < MIN_GAMES:
                return plain_mmr
            total_valid = 0
            w_outperf, w_total = 0.0, 0.0
            for played_dt, handicap, won in hist:
                days_ago = (cur_dt - played_dt).total_seconds() / 86400
                if days_ago < 0:
                    continue  # safety; shouldn't happen given chronological order
                total_valid += 1
                weight = recency_weight(days_ago)
                team_size_proxy = 1  # dampening uses per-match team size; approximated below
                w_outperf += handicap["outperf"] * weight
                w_total += weight
            if total_valid < MIN_GAMES or w_total < 0.1:
                return plain_mmr
            outperformance = w_outperf / w_total
            games_so_far = len(hist)
            confidence = min(1.0, games_so_far / 40.0)
            lp = last_played.get(pid)
            if lp is None:
                inactivity_weight = 1.0
            else:
                gap_days = (cur_dt - lp).total_seconds() / 86400
                inactivity_weight = 1.0 if gap_days <= 14 else mpow(0.5, (gap_days - 14) / 45.0)
            op = outperformance
            if op < 0:
                op *= 0.75
            bonus = op * OUTPERFORMANCE_MULTIPLIER * confidence * inactivity_weight
            return plain_mmr + bonus

        sum1_hc = sum(hc_mmr_for(pid, mmr) for pid, mmr in t1)
        sum2_hc = sum(hc_mmr_for(pid, mmr) for pid, mmr in t2)
        hc_pred.append(1 if sum1_hc > sum2_hc else (2 if sum2_hc > sum1_hc else 0))

        # --- update rolling history AFTER prediction ---
        for team_num, rows in ((1, t1), (2, t2)):
            opp_rows = t2 if team_num == 1 else t1
            my_size = len(rows)
            my_sum = sum(mmr for _, mmr in rows)
            opp_sum = sum(mmr for _, mmr in opp_rows)
            handicap_per_player = (my_sum - opp_sum) / my_size if my_size else 0.0
            exp_wr = expected_win_rate(handicap_per_player, my_size)
            won_team = team_num == winner
            match_outperf = (1.0 if won_team else 0.0) - exp_wr
            for pid, _ in rows:
                history[pid].append((cur_dt, {"outperf": match_outperf}, won_team))
                last_played[pid] = cur_dt

    return np.array(plain_pred), np.array(hc_pred), np.array(actual)


def measure(pred, actual, label):
    decided = pred != 0
    n = int(decided.sum())
    correct = int((pred[decided] == actual[decided]).sum())
    print(f"  {label}: {correct}/{n} = {correct/n:.1%} (ties excluded: {int((~decided).sum())})")
    return pred, actual, decided


def mcnemar_exact(pred_a, pred_b, actual):
    b = int(sum(bool(pa == w and pb != w) for pa, pb, w in zip(pred_a, pred_b, actual)))
    c = int(sum(bool(pb == w and pa != w) for pa, pb, w in zip(pred_a, pred_b, actual)))
    n, k = b + c, min(b, c)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    return b, c, p


def main():
    print("Loading match data (read-only)...")
    matches, order = load_data()
    plain_pred, hc_pred, actual = build_predictions(matches, order)
    print(f"n={len(actual)} usable matches\n")

    print("=== Baseline comparison ===")
    measure(plain_pred, actual, "plain team-sum mmr_before")
    measure(hc_pred, actual, "HC-MMR-adjusted team-sum (leak-free)")

    print("\n=== McNemar exact test: HC-MMR vs plain MMR ===")
    both_decided = (plain_pred != 0) & (hc_pred != 0)
    b, c, p = mcnemar_exact(plain_pred[both_decided], hc_pred[both_decided], actual[both_decided])
    print(f"  plain-only-right={b}, hc-only-right={c}, n_disagree={b+c}, exact p={p:.4f}")

    print("\n=== Bootstrap CI on the delta (1000 resamples) ===")
    random.seed(42)
    n = len(actual)
    diffs = []
    for _ in range(1000):
        idx = np.array([random.randrange(n) for _ in range(n)])
        pd_, hd_ = plain_pred[idx] != 0, hc_pred[idx] != 0
        p_acc = (plain_pred[idx][pd_] == actual[idx][pd_]).mean() if pd_.any() else 0.5
        h_acc = (hc_pred[idx][hd_] == actual[idx][hd_]).mean() if hd_.any() else 0.5
        diffs.append(h_acc - p_acc)
    diffs.sort()
    pos = sum(d > 0 for d in diffs) / len(diffs)
    lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]
    print(f"  mean {sum(diffs)/len(diffs):+.1%}, 95% CI [{lo:+.1%}, {hi:+.1%}], positive in {pos:.0%} of resamples")


if __name__ == "__main__":
    main()
