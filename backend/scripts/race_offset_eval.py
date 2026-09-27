import math
import random
import sqlite3
import sys
from collections import defaultdict, deque
from datetime import datetime
from math import comb
from pathlib import Path

import trueskill

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings
from app.rating_policy import decayed_sigma, typical_session_gap
from walkforward_session_eval import (
    DB, load_matches, assign_sessions, log_loss, display_mmr, duplicated_game_ids,
)

RACE_WINDOW = 20
FOCUS_PLAYERS = ["Stephan", "ShadowDragon"]


def load_races(con):
    return {(mid, pid): race for mid, pid, race in
            con.execute("SELECT match_id, player_id, race FROM match_players")}


def win_prob(team1_mean_variances, team2_mean_variances, k):
    delta = (sum(mean for mean, _ in team1_mean_variances)
             - sum(mean for mean, _ in team2_mean_variances))
    variance = sum(var for _, var in team1_mean_variances + team2_mean_variances) * (1 + k)
    return 0.5 * (1 + math.erf(delta / math.sqrt(2 * variance)))


def simulate(usable, races, s0, tau):
    env = trueskill.TrueSkill(mu=settings.trueskill_mu, sigma=settings.trueskill_sigma,
                              beta=settings.trueskill_beta, tau=0.0,
                              draw_probability=settings.trueskill_draw_probability)
    base = defaultdict(lambda: [settings.trueskill_mu, settings.trueskill_sigma ** 2])
    offset = defaultdict(lambda: [0.0, s0 ** 2])
    history = defaultdict(list)
    recent_races = defaultdict(lambda: deque(maxlen=RACE_WINDOW))
    rows = []
    for mid, played_at, t1, t1_ids, t2, t2_ids, winner in usable:
        now = datetime.fromisoformat(played_at)
        for pid in t1_ids + t2_ids:
            prior = history[pid]
            days = (now - prior[-1]).days if prior else 0
            sigma = decayed_sigma(math.sqrt(base[pid][1]), days, len(prior),
                                  typical_session_gap(prior + [now]))
            base[pid][1] = sigma ** 2

        def oracle(pid):
            o = offset[(pid, races[(mid, pid)])]
            return base[pid][0] + o[0], base[pid][1] + o[1]

        def race_mix(pid):
            seen = recent_races[pid]
            if not seen:
                return tuple(base[pid])
            weights = defaultdict(float)
            for r in seen:
                weights[r] += 1 / len(seen)
            offs = [(w, offset[(pid, r)]) for r, w in weights.items()]
            mean = sum(w * o[0] for w, o in offs)
            var = sum(w * (o[1] + o[0] ** 2) for w, o in offs) - mean ** 2
            return base[pid][0] + mean, base[pid][1] + var

        rows.append(dict(
            mid=mid, outcome=1 if winner == t1 else 0, t1_ids=t1_ids, t2_ids=t2_ids,
            oracle=([oracle(p) for p in t1_ids], [oracle(p) for p in t2_ids]),
            mix=([race_mix(p) for p in t1_ids], [race_mix(p) for p in t2_ids]),
        ))

        for pid in t1_ids + t2_ids:
            base[pid][1] += tau ** 2
        composite = {pid: oracle(pid) for pid in t1_ids + t2_ids}
        new1, new2 = env.rate(
            [[trueskill.Rating(mu=m, sigma=math.sqrt(v)) for m, v in (composite[p] for p in t1_ids)],
             [trueskill.Rating(mu=m, sigma=math.sqrt(v)) for m, v in (composite[p] for p in t2_ids)]],
            ranks=[0, 1] if winner == t1 else [1, 0])
        for pid, r in zip(t1_ids + t2_ids, list(new1) + list(new2)):
            mu, var = composite[pid]
            shrink = var - r.sigma ** 2
            o = offset[(pid, races[(mid, pid)])]
            for component in (base[pid], o):
                gain = component[1] / var
                component[0] += gain * (r.mu - mu)
                component[1] -= gain ** 2 * shrink
            history[pid].append(now)
            recent_races[pid].append(races[(mid, pid)])
    return rows


def probs(rows, idx, mode, k):
    return [win_prob(*rows[i][mode], k) for i in idx]


def mmr_diffs(rows, idx, mode):
    def team_mmr(team):
        return sum(display_mmr(mu, math.sqrt(var)) for mu, var in team)
    return [team_mmr(rows[i][mode][0]) - team_mmr(rows[i][mode][1]) for i in idx]


def logistic(diffs, scale):
    return [1 / (1 + math.exp(-d / scale)) for d in diffs]


def fit_scale(diffs, outcomes):
    return min(range(100, 5001, 25), key=lambda s: log_loss(logistic(diffs, s), outcomes))


def block_bootstrap_ll_gain(p_ref, p_new, outcomes, blocks, seed=42):
    rng = random.Random(seed)
    gains = []
    for _ in range(1000):
        js = [j for _ in blocks for j in blocks[rng.randrange(len(blocks))]]
        yy = [outcomes[j] for j in js]
        gains.append(log_loss([p_ref[j] for j in js], yy) - log_loss([p_new[j] for j in js], yy))
    gains.sort()
    return gains[24], gains[974]


def mcnemar(pa, pb, y):
    b = sum((a > .5) == o and (c > .5) != o for a, c, o in zip(pa, pb, y))
    c_ = sum((c > .5) == o and (a > .5) != o for a, c, o in zip(pa, pb, y))
    n, m = b + c_, min(b, c_)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(m + 1)) / 2 ** n)
    return b, c_, p


def run(path):
    con = sqlite3.connect(path, uri=True)
    usable = load_matches(con)
    races = load_races(con)
    names = dict(con.execute("SELECT name, id FROM players"))
    duplicated = duplicated_game_ids(con)
    con.close()
    session_ids = assign_sessions(usable)
    sessions = sorted(set(session_ids))
    cutoff = sessions[int(len(sessions) * .75)]
    scored = [usable[i][0] not in duplicated for i in range(len(usable))]
    train = [i for i, s in enumerate(session_ids) if s < cutoff and scored[i]]
    test = [i for i, s in enumerate(session_ids) if s >= cutoff and scored[i]]
    y_train = [1 if usable[i][6] == usable[i][2] else 0 for i in train]
    y_test = [1 if usable[i][6] == usable[i][2] else 0 for i in test]
    print(f"n={len(usable)} matches ({len(duplicated)} duplicated-game copies rated but not scored), "
          f"train={len(train)}, test={len(test)} "
          f"(test starts {usable[test[0]][1][:10]})")

    k_grid = [6, 8, 9, 10, 11, 12, 13, 15, 18]
    sims = {}

    def best(s0, tau, mode):
        key = (s0, tau)
        if key not in sims:
            sims[key] = simulate(usable, races, s0, tau)
        rows = sims[key]
        k = min(k_grid, key=lambda k: log_loss(probs(rows, train, mode, k), y_train))
        return log_loss(probs(rows, train, mode, k), y_train), k, key

    tau0 = settings.trueskill_tau
    arms = {"A incumbent": best(0.0, tau0, "oracle")}
    print(f"sanity: arm A fitted k={arms['A incumbent'][1]} (live k=11)")
    s0_grid = [0.5, 1, 2, 3, 4, 6]
    for mode, label in (("oracle", "B per-race, oracle race"), ("mix", "C per-race, race mix")):
        results = [best(s0, tau0, mode) for s0 in s0_grid]
        print(f"{label} train log loss by s0: "
              + ", ".join(f"{s}:{r[0]:.4f}" for s, r in zip(s0_grid, results)))
        arms[label] = min(results)
    tau_grid = [0.25, 0.35, 0.5, 0.75, 1.0, 1.5]
    results = [best(0.0, t, "oracle") for t in tau_grid]
    print("D faster dynamics train log loss by tau: "
          + ", ".join(f"{t}:{r[0]:.4f}" for t, r in zip(tau_grid, results)))
    arms["D faster dynamics"] = min(results)

    blocks = defaultdict(list)
    for j, i in enumerate(test):
        blocks[session_ids[i]].append(j)
    blocks = list(blocks.values())

    a_rows = sims[arms["A incumbent"][2]]
    a_test = probs(a_rows, test, "oracle", arms["A incumbent"][1])
    print("\n-- gate 1: win_probability (held-out) --")
    print(f"{'arm':28s} {'s0':>4} {'tau':>5} {'k':>3} {'test LL':>8} {'dLL vs A':>9} {'95% CI':>20} {'acc':>6}  McNemar vs A")
    for label, (_, k, (s0, tau)) in arms.items():
        mode = "mix" if label.startswith("C") else "oracle"
        p = probs(sims[(s0, tau)], test, mode, k)
        lo, hi = block_bootstrap_ll_gain(a_test, p, y_test, blocks)
        acc = sum((q > .5) == bool(o) for q, o in zip(p, y_test)) / len(p)
        b, c, mp = mcnemar(a_test, p, y_test)
        print(f"{label:28s} {s0:>4} {tau:>5} {k:>3} {log_loss(p, y_test):>8.4f} "
              f"{log_loss(a_test, y_test) - log_loss(p, y_test):>+9.4f} "
              f"[{lo:+.4f}, {hi:+.4f}] {acc:>6.1%}  b={b} c={c} p={mp:.3f}")
        for name in FOCUS_PLAYERS:
            pid = names.get(name)
            res = [(o - q) if pid in sims[(s0, tau)][i]["t1_ids"] else (q - o)
                   for i, q, o in zip(test, p, y_test)
                   if pid in sims[(s0, tau)][i]["t1_ids"] + sims[(s0, tau)][i]["t2_ids"]]
            if res:
                print(f"    {name}: held-out n={len(res)}, mean team residual={sum(res)/len(res):+.3f}")

    print("\n-- gate 2: summed display MMR, the balancer's sort key (logistic scale fit on train) --")
    a_diffs = mmr_diffs(a_rows, test, "oracle")
    a_mmr = logistic(a_diffs, fit_scale(mmr_diffs(a_rows, train, "oracle"), y_train))
    for label, (_, k, (s0, tau)) in arms.items():
        mode = "mix" if label.startswith("C") else "oracle"
        rows = sims[(s0, tau)]
        scale = fit_scale(mmr_diffs(rows, train, mode), y_train)
        diffs = mmr_diffs(rows, test, mode)
        p = logistic(diffs, scale)
        lo, hi = block_bootstrap_ll_gain(a_mmr, p, y_test, blocks)
        decided = [(d > 0) == bool(o) for d, o in zip(diffs, y_test) if d != 0]
        b, c, mp = mcnemar(a_mmr, p, y_test)
        print(f"{label:28s} scale={scale:>5} test LL={log_loss(p, y_test):.4f} "
              f"dLL vs A={log_loss(a_mmr, y_test) - log_loss(p, y_test):+.4f} [{lo:+.4f}, {hi:+.4f}] "
              f"acc={sum(decided)/len(decided):.1%}  b={b} c={c} p={mp:.3f}")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DB)
