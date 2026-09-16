"""Step C for SPEC-CAPTAIN-EFFECT-STEPHAN.md: the real within-stratum fit.

Only run after captain_effect_power_sim.py has been inspected (measured
2026-09-15: 57% power to detect a true 0.2 SD effect, 58% correct rule-out
rate at true zero, ~4% false-positive rate -- moderate, not hopeless; see
that script's output). Per the frozen spec, a null result here should be
read as "did not detect," not "ruled out," given that power.

Identification: for each receiver who appears in a given (session, exact
roster) stratum both WITH and AGAINST the captain, take
    D = Y_with - Y_against
Any receiver x session x roster fixed effect (skill, map, roster-level
context) cancels exactly in this difference by construction. What does NOT
cancel is anything that differs between the receiver's two occurrences:
teammate strength (excluding the captain), opponent strength (excluding the
captain), game order within the session, and prior captain exposure. Those
are regressed out; the intercept of that regression is the estimated
captain-presence association, in the same units as D (raw log-ratio units;
convert to the frozen 0.2 SD threshold using the total_sd from
captain_effect_coverage.py).

Read-only. Local DB only. No production/rating changes.
"""
import sqlite3
import random
from collections import defaultdict
from pathlib import Path
from datetime import datetime
import math

import trueskill

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rating_policy import decayed_sigma, typical_session_gap, rate_teams
from app.config import settings

DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sc2mmr.db") + "?mode=ro"
Y_TOTAL_SD = math.sqrt(1.8013010892498036)  # from captain_effect_coverage.py, frozen before this fit
CAPTAIN_NAME = "Stephan"


def load_full():
    con = sqlite3.connect(DB, uri=True)
    rows = con.execute("""
        SELECT mp.match_id, m.played_at, m.map_name, mp.team_number, mp.player_id,
               mp.won, mp.race, p.army_value_killed, p.army_value_lost
        FROM match_players mp
        JOIN matches m ON m.id = mp.match_id
        LEFT JOIN player_match_metrics p ON p.match_player_id = mp.id
        WHERE m.played_at IS NOT NULL
        ORDER BY m.played_at ASC, mp.match_id ASC
    """).fetchall()
    name_to_id = dict(con.execute("SELECT name, id FROM players"))
    con.close()

    matches = {}
    order = []
    for mid, played_at, map_name, team, pid, won, race, killed, lost in rows:
        if mid not in matches:
            matches[mid] = {"played_at": played_at, "map_name": map_name,
                             "teams": defaultdict(list), "winner": None,
                             "race": {}, "metrics": {}}
            order.append(mid)
        matches[mid]["teams"][team].append(pid)
        matches[mid]["race"][pid] = race
        matches[mid]["metrics"][pid] = (killed, lost)
        if won:
            matches[mid]["winner"] = team

    usable = []
    for mid in order:
        m = matches[mid]
        if len(m["teams"]) != 2 or not m["winner"]:
            continue
        t1, t2 = sorted(m["teams"].keys())
        if not m["teams"][t1] or not m["teams"][t2]:
            continue
        usable.append((mid, m["played_at"], m["map_name"], t1, m["teams"][t1],
                        t2, m["teams"][t2], m["winner"], m["race"], m["metrics"]))
    return usable, name_to_id


def assign_sessions(usable, gap_hours=4.0):
    session_ids, session_id, prev, order_in_session = [], 0, None, []
    idx = 0
    for mid, played_at, *_ in usable:
        t = datetime.fromisoformat(played_at)
        if prev is not None and (t - prev).total_seconds() / 3600.0 > gap_hours:
            session_id += 1
            idx = 0
        session_ids.append(session_id)
        order_in_session.append(idx)
        idx += 1
        prev = t
    return session_ids, order_in_session


def chronological_mu(usable):
    """Pre-match mu for every player in every match, walking forward with the
    live rating policy (mirrors skill_dependent_variance_eval.build_dataset)."""
    ratings = defaultdict(lambda: trueskill.Rating(mu=settings.trueskill_mu, sigma=settings.trueskill_sigma))
    history = defaultdict(list)
    pre_match_mu = {}  # (match_id, player_id) -> mu just before this match
    for mid, played_at, map_name, t1, t1_ids, t2, t2_ids, winner, race, metrics in usable:
        now = datetime.fromisoformat(played_at)
        for pid in t1_ids + t2_ids:
            prior_times = history[pid]
            old = ratings[pid]
            days = (now - prior_times[-1]).days if prior_times else 0
            ratings[pid] = trueskill.Rating(mu=old.mu, sigma=decayed_sigma(
                old.sigma, days, len(prior_times), typical_session_gap(prior_times + [now])))
            pre_match_mu[(mid, pid)] = ratings[pid].mu
        t1r = [ratings[pid] for pid in t1_ids]
        t2r = [ratings[pid] for pid in t2_ids]
        new_t1, new_t2 = rate_teams(t1r, t2r, winner == t1)
        for pid, r in zip(t1_ids, new_t1):
            ratings[pid] = r
        for pid, r in zip(t2_ids, new_t2):
            ratings[pid] = r
        for pid in t1_ids + t2_ids:
            history[pid].append(now)
    return pre_match_mu


def build_observations(usable, sessions, order_in_session, pre_mu, captain_id):
    """One row per (receiver, match) where the captain is present and the
    receiver is not the captain. Later grouped into (session, roster)."""
    obs = []  # dict per occurrence
    prior_exposure = defaultdict(int)  # receiver_id -> count of prior matches sharing session with captain
    for i, (mid, played_at, map_name, t1, t1_ids, t2, t2_ids, winner, race, metrics) in enumerate(usable):
        all_ids = t1_ids + t2_ids
        if captain_id not in all_ids:
            continue
        cap_team_ids = t1_ids if captain_id in t1_ids else t2_ids
        opp_team_ids = t2_ids if captain_id in t1_ids else t1_ids
        sid = sessions[i]
        roster = tuple(sorted(all_ids))
        for pid in all_ids:
            if pid == captain_id:
                continue
            killed, lost = metrics.get(pid, (None, None))
            if killed is None or lost is None:
                continue
            state = "with" if pid in cap_team_ids else "against"
            own_team_ids = cap_team_ids if state == "with" else opp_team_ids
            other_team_ids = opp_team_ids if state == "with" else cap_team_ids
            teammates_excl_captain = [x for x in own_team_ids if x not in (pid, captain_id)]
            opponents_excl_captain = [x for x in other_team_ids if x != captain_id]
            teammate_strength = (sum(pre_mu[(mid, x)] for x in teammates_excl_captain) / len(teammates_excl_captain)
                                  if teammates_excl_captain else pre_mu[(mid, pid)])
            opponent_strength = (sum(pre_mu[(mid, x)] for x in opponents_excl_captain) / len(opponents_excl_captain)
                                  if opponents_excl_captain else pre_mu[(mid, pid)])
            y = math.log(1 + max(killed, 0)) - math.log(1 + max(lost, 0))
            obs.append(dict(mid=mid, sid=sid, roster=roster, receiver=pid, state=state,
                             y=y, race=race.get(pid), map_name=map_name,
                             order=order_in_session[i], teammate_strength=teammate_strength,
                             opponent_strength=opponent_strength,
                             prior_exposure=prior_exposure[pid]))
            prior_exposure[pid] += 1
    return obs


def build_pairs(obs):
    """Collapse to one row per (receiver, session, roster) that has both
    states, taking the differenced controls WITH - AGAINST."""
    groups = defaultdict(dict)
    for o in obs:
        key = (o["receiver"], o["sid"], o["roster"])
        groups[key][o["state"]] = o
    pairs = []
    race_mismatches = 0
    for key, states in groups.items():
        if "with" not in states or "against" not in states:
            continue
        w, a = states["with"], states["against"]
        if w["race"] != a["race"]:
            race_mismatches += 1
            continue
        pairs.append(dict(
            receiver=key[0], sid=key[1], roster=key[2],
            D=w["y"] - a["y"],
            teammate_strength_diff=w["teammate_strength"] - a["teammate_strength"],
            opponent_strength_diff=w["opponent_strength"] - a["opponent_strength"],
            order_diff=w["order"] - a["order"],
            prior_exposure_diff=w["prior_exposure"] - a["prior_exposure"],
        ))
    return pairs, race_mismatches


def ols_intercept(pairs, x_keys):
    """D = intercept + sum(beta_k * x_k) + eps, via normal equations."""
    n = len(pairs)
    X = [[1.0] + [p[k] for k in x_keys] for p in pairs]
    y = [p["D"] for p in pairs]
    p_dim = len(x_keys) + 1
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p_dim)] for a in range(p_dim)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p_dim)]
    # Gaussian elimination solve (small, fixed dimension)
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for col in range(p_dim):
        piv = max(range(col, p_dim), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-9:
            return None  # singular -- collinearity
        M[col], M[piv] = M[piv], M[col]
        pivval = M[col][col]
        M[col] = [v / pivval for v in M[col]]
        for r in range(p_dim):
            if r != col:
                factor = M[r][col]
                M[r] = [v - factor * M[col][j] for j, v in enumerate(M[r])]
    return M[0][p_dim]  # intercept coefficient


def session_block_bootstrap(pairs, x_keys, n_resamples=3000, seed=42):
    by_session = defaultdict(list)
    for p in pairs:
        by_session[p["sid"]].append(p)
    blocks = list(by_session.values())
    rng = random.Random(seed)
    ests = []
    for _ in range(n_resamples):
        sample = [p for _ in blocks for p in blocks[rng.randrange(len(blocks))]]
        est = ols_intercept(sample, x_keys)
        if est is not None:
            ests.append(est)
    ests.sort()
    return ests


def leave_one_out(pairs, x_keys, by):
    keys = sorted({p[by] for p in pairs})
    results = []
    for k in keys:
        subset = [p for p in pairs if p[by] != k]
        est = ols_intercept(subset, x_keys)
        results.append((k, est, len(subset)))
    return results


def main():
    usable, name_to_id = load_full()
    sessions, order_in_session = assign_sessions(usable)
    pre_mu = chronological_mu(usable)
    captain_id = name_to_id[CAPTAIN_NAME]

    obs = build_observations(usable, sessions, order_in_session, pre_mu, captain_id)
    pairs, race_mismatches = build_pairs(obs)
    print(f"Captain: {CAPTAIN_NAME}. Qualifying receiver-stratum pairs: {len(pairs)} "
          f"(race-mismatch exclusions: {race_mismatches})")
    print(f"Distinct sessions represented: {len({p['sid'] for p in pairs})}, "
          f"distinct receivers: {len({p['receiver'] for p in pairs})}")

    x_keys = ["teammate_strength_diff", "opponent_strength_diff", "order_diff", "prior_exposure_diff"]
    point = ols_intercept(pairs, x_keys)
    if point is None:
        print("SINGULAR regression (severe collinearity) -- NOT IDENTIFIABLE. Stopping per spec.")
        return
    print(f"\nPoint estimate (raw units): {point:+.4f}  "
          f"({point / Y_TOTAL_SD:+.4f} SD units; 0.2 SD threshold = {0.2*Y_TOTAL_SD:.4f} raw)")

    boot = session_block_bootstrap(pairs, x_keys)
    lo, hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]
    print(f"Session-block bootstrap 95% CI (raw units): [{lo:+.4f}, {hi:+.4f}]  "
          f"= SD units [{lo/Y_TOTAL_SD:+.4f}, {hi/Y_TOTAL_SD:+.4f}]  "
          f"({len(boot)}/{3000} resamples nonsingular)")

    print("\nLeave-one-session-out stability (intercept, raw units):")
    loo_session = leave_one_out(pairs, x_keys, "sid")
    ests = [e for _, e, _ in loo_session if e is not None]
    print(f"  range [{min(ests):+.4f}, {max(ests):+.4f}] across {len(loo_session)} sessions, "
          f"full-sample point {point:+.4f}")

    print("\nLeave-one-receiver-out stability (intercept, raw units):")
    loo_receiver = leave_one_out(pairs, x_keys, "receiver")
    ests_r = [e for _, e, _ in loo_receiver if e is not None]
    print(f"  range [{min(ests_r):+.4f}, {max(ests_r):+.4f}] across {len(loo_receiver)} receivers, "
          f"full-sample point {point:+.4f}")

    verdict = "NOT IDENTIFIABLE"
    if hi / Y_TOTAL_SD < 0.2:
        verdict = "RULED OUT (>=0.2 SD effect excluded by upper CI bound)"
    elif lo <= 0 <= hi:
        verdict = "INCONCLUSIVE (CI includes zero)"
    elif lo > 0:
        stable = (min(ests) > 0) and (min(ests_r) > 0)
        verdict = ("SUPPORTED, stable under leave-one-out" if stable
                   else "POSITIVE POINT ESTIMATE BUT NOT STABLE under leave-one-out -- do not promote")
    print(f"\nVerdict per frozen spec: {verdict}")
    print("Reminder: power sim measured ~57% detection probability at true 0.2 SD and "
          "~4% false-positive rate at true 0 -- read an inconclusive result as "
          "'did not detect', not 'ruled out', given that power.")


if __name__ == "__main__":
    main()
