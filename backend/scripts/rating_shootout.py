"""Rating consolidation campaign — Phase 2 predictive shoot-out.

Chronological, no-lookahead match-prediction accuracy for every rating variant,
all derived from stored per-match mu_before/sigma_before (formula-independent).
Read-only: opens the DB with mode=ro. See
.claude/skills/sc2mmr-rating-consolidation-campaign/SKILL.md Phase 2 for the
binding methodology (prior-matches-only handicap/combat, ties excluded,
McNemar exact vs arm A, pre-registered verdict rule).

Usage: cd backend && python3 scripts/rating_shootout.py
"""
import math
import random
import sqlite3
from collections import defaultdict

DB = "file:data/sc2mmr.db?mode=ro"
HANDICAP_MULT = 3000.0
SPEC_COMBAT_COEF = 20.0
SPEC_COMBAT_DEFAULT = 25.0  # design-doc default when no prior metrics
LIVE_COMBAT_DEFAULT, LIVE_ECO_DEFAULT, LIVE_EFF_DEFAULT = 20.0, 50.0, 50.0

VARIANTS = ["A", "Aprime", "Adouble", "B", "C", "D", "E"]
LABELS = {
    "A": "A  display 1000+100mu (no-sigma doctrine)",
    "Aprime": "A' display 1000+100mu-200sigma (working tree)",
    "Adouble": 'A" conservative 1000+100mu-300sigma',
    "B": "B  TrueSkill win-prob phi(dmu/sqrt(sum sigma^2))",
    "C": "C  A + running_outperformance*3000 (design-doc handicap)",
    "D": "D  C + 20*prior-avg combat (SPEC formula)",
    "E": "E  C + min(1200, 25*min(combat,60)+4*eco+2*eff) (live formula)",
}


def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def mcnemar_exact(b, c):
    """Two-sided exact binomial test on discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # two-sided: 2 * P(X <= k), X ~ Bin(n, 0.5), capped at 1
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2.0 * p)


def load_matches(con):
    """Return matches (chronological) as (match_id, complete_metrics, rows).

    rows: list of (player_id, team, won, mu, sigma, combat, eco, eff) —
    combat/eco/eff are THIS match's metrics (used only to update running
    state AFTER prediction, never for the prediction itself).
    """
    complete = {
        r[0]
        for r in con.execute(
            """SELECT m.id FROM matches m WHERE NOT EXISTS (
                 SELECT 1 FROM match_players mp
                 LEFT JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
                 WHERE mp.match_id = m.id
                   AND (pmm.id IS NULL OR pmm.combat_score IS NULL OR pmm.combat_score <= 0))"""
        )
    }
    by_match = defaultdict(list)
    order = {}
    q = """SELECT mp.match_id, m.played_at, m.id, mp.player_id, mp.team_number, mp.won,
                  mp.mu_before, mp.sigma_before,
                  pmm.combat_score, pmm.economic_score, pmm.efficiency_score
           FROM match_players mp
           JOIN matches m ON m.id = mp.match_id
           LEFT JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
           ORDER BY m.played_at ASC, m.id ASC"""
    for (mid, played, _mid2, pid, team, won, mu, sigma, cs, eco, eff) in con.execute(q):
        by_match[mid].append((pid, team, won, mu, sigma, cs, eco, eff))
        order.setdefault(mid, (played, mid))
    matches = []
    for mid in sorted(by_match, key=lambda m: order[m]):
        rows = by_match[mid]
        teams = {r[1] for r in rows}
        if len(teams) != 2:
            continue  # not a 2-team match
        matches.append((mid, mid in complete, rows))
    return matches


def run(con):
    matches = load_matches(con)
    # per-player running state (prior matches only)
    st = defaultdict(lambda: {"g": 0, "w": 0, "sew": 0.0, "nc": 0, "sc": 0.0, "se": 0.0, "sf": 0.0})

    results = {v: {} for v in VARIANTS}  # variant -> {match_id: True/False}; ties omitted
    complete_ids = set()

    for mid, is_complete, rows in matches:
        if is_complete:
            complete_ids.add(mid)
        t1, t2 = sorted({r[1] for r in rows})
        t1_won = any(r[1] == t1 and r[2] == 1 for r in rows)

        # --- per-player variant ratings from PRIOR state + mu/sigma_before ---
        per_team = {v: {t1: 0.0, t2: 0.0} for v in VARIANTS if v != "B"}
        mu_sum, s2_sum = {t1: 0.0, t2: 0.0}, {t1: 0.0, t2: 0.0}
        a_team = {t1: [], t2: []}  # A-base display values for handicap update later
        for pid, team, _won, mu, sigma, _cs, _eco, _eff in rows:
            s = st[pid]
            a = 1000.0 + 100.0 * mu
            a_team[team].append(a)
            outperf = (s["w"] / s["g"] - s["sew"] / s["g"]) if s["g"] > 0 else 0.0
            c_val = a + outperf * HANDICAP_MULT
            pac_spec = (s["sc"] / s["nc"]) if s["nc"] > 0 else SPEC_COMBAT_DEFAULT
            pac = (s["sc"] / s["nc"]) if s["nc"] > 0 else LIVE_COMBAT_DEFAULT
            pae = (s["se"] / s["nc"]) if s["nc"] > 0 else LIVE_ECO_DEFAULT
            paf = (s["sf"] / s["nc"]) if s["nc"] > 0 else LIVE_EFF_DEFAULT
            per_team["A"][team] += a
            per_team["Aprime"][team] += a - 200.0 * sigma
            per_team["Adouble"][team] += a - 300.0 * sigma
            per_team["C"][team] += c_val
            per_team["D"][team] += c_val + SPEC_COMBAT_COEF * pac_spec
            per_team["E"][team] += c_val + min(1200.0, 25.0 * min(pac, 60.0) + 4.0 * pae + 2.0 * paf)
            mu_sum[team] += mu
            s2_sum[team] += sigma * sigma

        for v in per_team:
            d = per_team[v][t1] - per_team[v][t2]
            if d != 0:
                results[v][mid] = (d > 0) == t1_won
        tot_s = math.sqrt(s2_sum[t1] + s2_sum[t2])
        if tot_s > 0:
            p1 = phi((mu_sum[t1] - mu_sum[t2]) / tot_s)
            if p1 != 0.5:
                results["B"][mid] = (p1 > 0.5) == t1_won

        # --- update running state AFTER prediction (this match becomes 'prior') ---
        avg = {t: sum(a_team[t]) / len(a_team[t]) for t in (t1, t2)}
        for pid, team, won, _mu, _sigma, cs, eco, eff in rows:
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
                s["se"] += eco or 0.0
                s["sf"] += eff or 0.0
    return results, complete_ids


def report(results, complete_ids, subset=None, title="FULL HISTORY"):
    ids = subset if subset is not None else None
    base = results["A"] if ids is None else {m: v for m, v in results["A"].items() if m in ids}
    print(f"\n=== {title} ===")
    print(f"{'variant':<58} {'acc':>14} {'d_vs_A':>7} {'McNemar b/c':>12} {'p':>8} {'boot 95% CI':>16}")
    rng = random.Random(42)
    for v in VARIANTS:
        res = results[v] if ids is None else {m: r for m, r in results[v].items() if m in ids}
        n, corr = len(res), sum(res.values())
        acc = corr / n if n else float("nan")
        # paired vs A
        paired = [m for m in res if m in base]
        b = sum(1 for m in paired if base[m] and not res[m])
        c = sum(1 for m in paired if not base[m] and res[m])
        p = mcnemar_exact(b, c)
        deltas = []
        if v != "A" and paired:
            for _ in range(1000):
                samp = [paired[rng.randrange(len(paired))] for _ in paired]
                deltas.append(sum(res[m] for m in samp) / len(samp) - sum(base[m] for m in samp) / len(samp))
            deltas.sort()
            lo, hi = deltas[24], deltas[974]
            ci = f"[{lo:+.1%}, {hi:+.1%}]"
            d = acc - sum(base[m] for m in paired) / len(paired)
            print(f"{LABELS[v]:<58} {corr:>5}/{n:<4}={acc:6.1%} {d:+6.1%} {b:>5}/{c:<5} {p:8.4f} {ci:>16}")
        else:
            print(f"{LABELS[v]:<58} {corr:>5}/{n:<4}={acc:6.1%} {'—':>7} {'—':>12} {'—':>8} {'—':>16}")


if __name__ == "__main__":
    con = sqlite3.connect(DB, uri=True)
    results, complete_ids = run(con)
    excluded = 863 - len(results["A"])
    print(f"matches decided by arm A: {len(results['A'])} (excluded: ties/one-sided = {excluded} of 863 total incl. non-2-team)")
    report(results, complete_ids)
    report(results, complete_ids, subset=complete_ids, title=f"COMPLETE-METRICS SUBSET (n={len(complete_ids)})")
    con.close()
