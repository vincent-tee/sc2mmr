import json
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import trueskill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.rating_policy import decayed_sigma, typical_session_gap, win_probability, rate_teams
from walkforward_session_eval import (
    DB, load_matches, assign_sessions, display_mmr, duplicated_game_ids,
)

MIN_TRADE_SHARE_WINNER_AGREEMENT = 0.90


def ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2
        i = j + 1
    return out


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = sum((a - mx) ** 2 for a in rx) ** 0.5
    sy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (sx * sy)


def pre_match_predictors(usable):
    ratings = defaultdict(lambda: trueskill.Rating(mu=25.0, sigma=8.333))
    history = defaultdict(list)
    out = {}
    for mid, played_at, t1, t1_ids, t2, t2_ids, winner in usable:
        now = datetime.fromisoformat(played_at)
        for pid in t1_ids + t2_ids:
            prior = history[pid]
            days = (now - prior[-1]).days if prior else 0
            ratings[pid] = trueskill.Rating(mu=ratings[pid].mu, sigma=decayed_sigma(
                ratings[pid].sigma, days, len(prior), typical_session_gap(prior + [now])))
        t1r = [ratings[p] for p in t1_ids]
        t2r = [ratings[p] for p in t2_ids]
        mmr_gap = abs(sum(display_mmr(r.mu, r.sigma) for r in t1r)
                      - sum(display_mmr(r.mu, r.sigma) for r in t2r))
        out[mid] = dict(t1=t1, mmr=mmr_gap, wp=abs(win_probability(t1r, t2r) - 0.5))
        new1, new2 = rate_teams(t1r, t2r, winner == t1)
        for pid, r in zip(t1_ids + t2_ids, list(new1) + list(new2)):
            ratings[pid] = r
            history[pid].append(now)
    return out


def main(sweep_path, db_uri):
    with open(sweep_path) as sweep_file:
        recorded_result = {e["mid"]: e for e in json.load(sweep_file)
                           if "error" not in e and len(e["result"]) == 1}
    con = sqlite3.connect(db_uri, uri=True)
    usable = load_matches(con)
    duplicated = duplicated_game_ids(con)
    con.close()
    session_of = dict(zip((u[0] for u in usable), assign_sessions(usable)))
    predictors = pre_match_predictors(usable)

    rows, trade_share_picks_winner = [], 0
    for mid, pred in predictors.items():
        replay = recorded_result.get(mid)
        if not replay or mid in duplicated:
            continue
        team1 = str(pred["t1"])
        team2 = next(t for t in replay["agg"] if t != team1)
        killed1, killed2 = replay["agg"][team1]["killed"], replay["agg"][team2]["killed"]
        if killed1 + killed2 == 0:
            continue
        team1_trade_share = killed1 / (killed1 + killed2)
        trade_share_picks_winner += (team1_trade_share > 0.5) == (replay["result"][0] == pred["t1"])
        rows.append(dict(session=session_of[mid], lopsidedness=abs(team1_trade_share - 0.5), **pred))

    agreement = trade_share_picks_winner / len(rows)
    print(f"n={len(rows)} ground-truth games; trade share picks the recorded winner in {agreement:.1%} "
          f"(required >= {MIN_TRADE_SHARE_WINNER_AGREEMENT:.0%})")
    if agreement < MIN_TRADE_SHARE_WINNER_AGREEMENT:
        print("Verdict: margin not trustworthy, no comparison made")
        return
    lopsidedness = [r["lopsidedness"] for r in rows]
    rho = {k: spearman([r[k] for r in rows], lopsidedness) for k in ("mmr", "wp")}
    print(f"Spearman with realized lopsidedness: MMR gap {rho['mmr']:+.3f}, "
          f"win-prob gap {rho['wp']:+.3f}, difference (WP - MMR) {rho['wp'] - rho['mmr']:+.3f}")

    sessions = defaultdict(list)
    for r in rows:
        sessions[r["session"]].append(r)
    sessions = list(sessions.values())
    rng = random.Random(42)
    diffs = []
    for _ in range(1000):
        sample = [r for _ in sessions for r in sessions[rng.randrange(len(sessions))]]
        outcome = [r["lopsidedness"] for r in sample]
        diffs.append(spearman([r["wp"] for r in sample], outcome)
                     - spearman([r["mmr"] for r in sample], outcome))
    diffs.sort()
    lo, hi = diffs[24], diffs[974]
    print(f"session-block bootstrap 95% CI on (WP - MMR): [{lo:+.3f}, {hi:+.3f}], "
          f"WP better in {sum(d > 0 for d in diffs) / 10:.0f}% of resamples")

    def mean_lopsidedness(games):
        return sum(r["lopsidedness"] for r in games) / len(games)

    for k in ("mmr", "wp"):
        ordered = sorted(rows, key=lambda r: r[k])
        quarter = len(ordered) // 4
        print(f"  {k:3s}: most-balanced quarter mean lopsidedness {mean_lopsidedness(ordered[:quarter]):.3f}, "
              f"least-balanced quarter {mean_lopsidedness(ordered[-quarter:]):.3f}")
    print("Verdict:", "SWITCH default to win probability" if lo > 0 else "KEEP the default (criterion not met)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else DB)
