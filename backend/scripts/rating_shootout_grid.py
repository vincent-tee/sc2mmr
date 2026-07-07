"""Phase 2.4 branch — coefficient re-fit grid search (read-only).

Grid: sigma_coef (display base) x handicap_mult x combat_coef, evaluated with
chronological 5-block CV: for each held-out block, the best cell is selected
on the OTHER four blocks, then scored on the held-out block. This guards
against pick-the-best-of-98-cells selection overfitting. Also prints the full
grid on all matches (transparency obligation) — do not promote from that table.

Usage: cd backend && python3 scripts/rating_shootout_grid.py
"""
import math
import sqlite3
from collections import defaultdict

DB = "file:data/sc2mmr.db?mode=ro"
SIGMA_COEFS = [0.0, 200.0, 300.0]
HANDICAP_MULTS = [0, 1000, 1500, 2000, 2500, 3000, 4000]
COMBAT_COEFS = [0, 5, 10, 15, 20, 25, 30]
SPEC_COMBAT_DEFAULT = 25.0


def load_components():
    """One chronological pass; per match, per-team sums of (a, sigma, outperf, prior-combat)."""
    con = sqlite3.connect(DB, uri=True)
    by_match, order = defaultdict(list), {}
    q = """SELECT mp.match_id, m.played_at, mp.player_id, mp.team_number, mp.won,
                  mp.mu_before, mp.sigma_before, pmm.combat_score
           FROM match_players mp JOIN matches m ON m.id = mp.match_id
           LEFT JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
           ORDER BY m.played_at ASC, m.id ASC"""
    for mid, played, pid, team, won, mu, sigma, cs in con.execute(q):
        by_match[mid].append((pid, team, won, mu, sigma, cs))
        order.setdefault(mid, (played, mid))
    con.close()

    st = defaultdict(lambda: {"g": 0, "w": 0, "sew": 0.0, "nc": 0, "sc": 0.0})
    comps = []  # (t1_won, {team: [a_sum, sigma_sum, outperf_sum, combat_sum]})
    for mid in sorted(by_match, key=lambda m: order[m]):
        rows = by_match[mid]
        teams = sorted({r[1] for r in rows})
        if len(teams) != 2:
            continue
        t1, t2 = teams
        t1_won = any(r[1] == t1 and r[2] == 1 for r in rows)
        sums = {t1: [0.0] * 4, t2: [0.0] * 4}
        a_team = {t1: [], t2: []}
        for pid, team, _won, mu, sigma, _cs in rows:
            s = st[pid]
            a = 1000.0 + 100.0 * mu
            a_team[team].append(a)
            outperf = (s["w"] / s["g"] - s["sew"] / s["g"]) if s["g"] > 0 else 0.0
            pac = (s["sc"] / s["nc"]) if s["nc"] > 0 else SPEC_COMBAT_DEFAULT
            sums[team][0] += a
            sums[team][1] += sigma
            sums[team][2] += outperf
            sums[team][3] += pac
        comps.append((t1_won, sums[t1], sums[t2]))
        avg = {t: sum(a_team[t]) / len(a_team[t]) for t in teams}
        for pid, team, won, _mu, _sigma, cs in rows:
            opp = t2 if team == t1 else t1
            handicap = (avg[team] - avg[opp]) / len(a_team[team])
            exp_wr = 1.0 / (1.0 + 10.0 ** (-handicap / 400.0))
            s = st[pid]
            s["g"] += 1
            s["w"] += 1 if won else 0
            s["sew"] += exp_wr
            if cs is not None and cs > 0:
                s["nc"] += 1
                s["sc"] += cs
    return comps


def cell_correct(comps, idxs, sig, h, c):
    corr = dec = 0
    for i in idxs:
        t1_won, s1, s2 = comps[i]
        d = (s1[0] - s2[0]) - sig * (s1[1] - s2[1]) + h * (s1[2] - s2[2]) + c * (s1[3] - s2[3])
        if d == 0:
            continue
        dec += 1
        corr += (d > 0) == t1_won
    return corr, dec


def main():
    comps = load_components()
    n = len(comps)
    cells = [(s, h, c) for s in SIGMA_COEFS for h in HANDICAP_MULTS for c in COMBAT_COEFS]
    blocks = [list(range(k * n // 5, (k + 1) * n // 5)) for k in range(5)]

    print(f"matches: {n}; grid cells: {len(cells)}; 5 chronological blocks of ~{n//5}")
    # nested CV: select best cell on 4 blocks, score on held-out block
    held_corr = held_dec = 0
    print("\nfold | selected cell (sigma,handicap,combat) | train acc | held-out acc")
    for k in range(5):
        train = [i for b in range(5) if b != k for i in blocks[b]]
        best, best_acc = None, -1.0
        for cell in cells:
            corr, dec = cell_correct(comps, train, *cell)
            if dec and corr / dec > best_acc:
                best, best_acc = cell, corr / dec
        corr, dec = cell_correct(comps, blocks[k], *best)
        held_corr += corr
        held_dec += dec
        print(f"  {k+1}  | sigma={best[0]:<5} h={best[1]:<5} c={best[2]:<3}       | {best_acc:6.1%}   | {corr}/{dec} = {corr/dec:.1%}")
    print(f"\nCV OUT-OF-FOLD accuracy of the select-best-cell procedure: {held_corr}/{held_dec} = {held_corr/held_dec:.1%}")

    # reference anchors on all data
    for name, cell in [("A (0,0,0)", (0.0, 0, 0)), ("A' (200,0,0)", (200.0, 0, 0)), ('A" (300,0,0)', (300.0, 0, 0)),
                       ("D-spec (0,3000,20)", (0.0, 3000, 20)), ("A'+handicap+combat (200,3000,20)", (200.0, 3000, 20))]:
        corr, dec = cell_correct(comps, range(n), *cell)
        print(f"anchor {name:<34} {corr}/{dec} = {corr/dec:.1%}")

    # full grid, all data (transparency only — selection here is overfit by construction)
    print("\nFULL GRID (all matches; report-only). Rows=handicap, cols=combat. One table per sigma coef.")
    for s in SIGMA_COEFS:
        print(f"\nsigma_coef={s:.0f}    " + "".join(f"c={c:<6}" for c in COMBAT_COEFS))
        for h in HANDICAP_MULTS:
            row = []
            for c in COMBAT_COEFS:
                corr, dec = cell_correct(comps, range(n), s, h, c)
                row.append(f"{corr/dec:6.1%} ")
            print(f"h={h:<6} " + "".join(row))


if __name__ == "__main__":
    main()
