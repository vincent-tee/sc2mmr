"""Step B for SPEC-CAPTAIN-EFFECT-STEPHAN.md: power/precision simulation on
the ACTUAL 57-stratum exact-roster design, BEFORE fitting any real
coefficient. Injects synthetic within-stratum effects of 0 and 0.2 SD with
session-correlated noise calibrated to the real (unconditional) Y variance
decomposition from captain_effect_coverage.py. Read-only; does not look at
or use the real with/against outcome difference anywhere.

Gate: if this simulation shows the design cannot separate 0 from 0.2 SD,
the spec requires stopping here and reporting the power limitation instead
of fitting the real data.
"""
import sqlite3
import random
from collections import defaultdict
from pathlib import Path
import math

DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sc2mmr.db") + "?mode=ro"

# From captain_effect_coverage.py (measured before this script; reused as
# fixed nuisance parameters, not as anything derived from the treatment effect).
WITHIN_SESSION_SD = math.sqrt(1.7823974477498015)
BETWEEN_SESSION_SD = math.sqrt(0.01890364150000204)
Y_TOTAL_SD = math.sqrt(1.8013010892498036)  # standardization unit for the 0.2 SD threshold


def build_real_strata():
    """Reconstruct the same 57 metric-complete Stephan strata: for each
    (session, exact roster), the receiver's state (with/against) count so we
    can simulate on the SAME design shape (number of receivers per stratum,
    number of 'with' vs 'against' observations per receiver where available).
    We do not read the real Y values into the simulation at all."""
    con = sqlite3.connect(DB, uri=True)
    rows = con.execute("""
        SELECT mp.match_id, m.played_at, mp.team_number, mp.player_id, mp.won,
               p.army_value_killed, p.army_value_lost
        FROM match_players mp
        JOIN matches m ON m.id = mp.match_id
        LEFT JOIN player_match_metrics p ON p.match_player_id = mp.id
        WHERE m.played_at IS NOT NULL
        ORDER BY m.played_at ASC, mp.match_id ASC
    """).fetchall()
    name_to_id = dict(con.execute("SELECT name, id FROM players"))
    con.close()
    captain_id = name_to_id["Stephan"]

    matches = {}
    order = []
    for mid, played_at, team, pid, won, killed, lost in rows:
        if mid not in matches:
            matches[mid] = {"played_at": played_at, "teams": defaultdict(list),
                             "winner": None, "metrics": {}}
            order.append(mid)
        matches[mid]["teams"][team].append(pid)
        matches[mid]["metrics"][pid] = (killed, lost)
        if won:
            matches[mid]["winner"] = team

    from datetime import datetime
    session_id, prev, sessions = 0, None, []
    for mid in order:
        t = datetime.fromisoformat(matches[mid]["played_at"])
        if prev is not None and (t - prev).total_seconds() / 3600.0 > 4.0:
            session_id += 1
        sessions.append(session_id)
        prev = t

    strata = defaultdict(lambda: defaultdict(set))       # (sid, roster) -> receiver -> states
    strata_complete = defaultdict(lambda: defaultdict(set))
    for mid, sid in zip(order, sessions):
        m = matches[mid]
        if len(m["teams"]) != 2 or not m["winner"]:
            continue
        t1, t2 = sorted(m["teams"].keys())
        if not m["teams"][t1] or not m["teams"][t2]:
            continue
        all_ids = m["teams"][t1] + m["teams"][t2]
        if captain_id not in all_ids:
            continue
        roster = tuple(sorted(all_ids))
        cap_team = t1 if captain_id in m["teams"][t1] else t2
        for pid in all_ids:
            if pid == captain_id:
                continue
            state = "with" if pid in m["teams"][cap_team] else "against"
            strata[(sid, roster)][pid].add(state)
            killed, lost = m["metrics"].get(pid, (None, None))
            if killed is not None and lost is not None:
                strata_complete[(sid, roster)][pid].add(state)

    switching = {k: recv for k, recv in strata_complete.items()
                 if any(len(states) == 2 for states in recv.values())}
    # design shape: for each switching stratum, how many receivers have both states
    design = [{r: 1 for r, states in recv.items() if len(states) == 2} for recv in switching.values()]
    design = [d for d in design if d]
    return design


def simulate(design, true_effect_sd_units, n_sim=2000, seed=42):
    """For each stratum, each qualifying receiver contributes a (with, against)
    pair. Simulate Y_with - Y_against = true_effect + session_effect_noise*0
    (session effect cancels within a fixed session-roster stratum, since both
    observations share the same session) + within_session_noise_with -
    within_session_noise_against. This is the correct noise model: the
    between-session component drops out of a within-stratum difference by
    construction (both draws are the same session), so only within-session
    variance contributes to the contrast noise."""
    rng = random.Random(seed)
    true_effect = true_effect_sd_units * Y_TOTAL_SD
    per_pair_noise_sd = WITHIN_SESSION_SD * math.sqrt(2)  # two independent within-session draws

    detections = 0       # CI excludes zero AND positive
    ruled_out_below_0_2 = 0  # CI upper bound < 0.2 SD
    ci_widths = []
    for _ in range(n_sim):
        contrasts = []
        for stratum in design:
            for _ in stratum:
                noise = rng.gauss(0, per_pair_noise_sd)
                contrasts.append(true_effect + noise)
        # session-block bootstrap CI on the mean contrast (block = stratum, since
        # a stratum's receivers share a session)
        idx_by_stratum = []
        pos = 0
        for stratum in design:
            k = len(stratum)
            idx_by_stratum.append(list(range(pos, pos + k)))
            pos += k
        boot_means = []
        for _ in range(500):
            sample = [i for _ in idx_by_stratum
                      for i in idx_by_stratum[rng.randrange(len(idx_by_stratum))]]
            boot_means.append(sum(contrasts[i] for i in sample) / len(sample))
        boot_means.sort()
        lo = boot_means[int(0.025 * len(boot_means))]
        hi = boot_means[int(0.975 * len(boot_means))]
        ci_widths.append(hi - lo)
        if lo > 0:
            detections += 1
        if hi < 0.2 * Y_TOTAL_SD:
            ruled_out_below_0_2 += 1

    n_pairs = sum(len(s) for s in design)
    return dict(
        true_effect_sd_units=true_effect_sd_units,
        n_strata=len(design), n_receiver_pairs=n_pairs,
        detection_rate=detections / n_sim,
        rule_out_0_2_rate=ruled_out_below_0_2 / n_sim,
        mean_ci_width_raw=sum(ci_widths) / len(ci_widths),
        mean_ci_width_sd_units=(sum(ci_widths) / len(ci_widths)) / Y_TOTAL_SD,
    )


def main():
    design = build_real_strata()
    n_pairs = sum(len(s) for s in design)
    print(f"Design: {len(design)} metric-complete switching strata, {n_pairs} receiver pairs")
    print(f"Noise model: within-session SD={WITHIN_SESSION_SD:.4f}, "
          f"Y total SD={Y_TOTAL_SD:.4f} (0.2 SD threshold = {0.2*Y_TOTAL_SD:.4f} raw units)")
    print("Between-session SD dropped from contrast noise by construction "
          f"(same-session pairing) -- measured between-session SD={BETWEEN_SESSION_SD:.4f} "
          "for reference only.\n")

    for true_effect in [0.0, 0.2]:
        r = simulate(design, true_effect)
        print(f"True effect = {true_effect} SD:")
        for k, v in r.items():
            print(f"  {k}: {v}")
        print()


if __name__ == "__main__":
    main()
