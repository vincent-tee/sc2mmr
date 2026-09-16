"""Step A (design/feasibility only) for the proposed captain-effect experiment
in docs/reviews/2026-09-15-methodology-audit-and-coordination-plan.md #7.

Purpose: measure what is actually available on the LOCAL database (chosen as
canonical -- the prod snapshot is not an independent sample, see that doc's
#1) before freezing the analysis protocol. Prints:
  - receiver x session x exact-roster switching strata for Stephan (primary)
    and ShadowDragon (secondary), with vs without requiring a joined metric
    row for the receiver's own match_player row.
  - Y = log(1+army_value_killed) - log(1+army_value_lost) coverage and
    variance decomposition (session-level vs within-session) for the
    receiver population, computed WITHOUT conditioning on captain presence --
    this is a nuisance-parameter check for the power simulation, not a look
    at the treatment effect.

Read-only. No fitting, no coefficient estimate. Run before writing the freeze.
"""
import sqlite3
from collections import defaultdict
from pathlib import Path
import math

DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sc2mmr.db") + "?mode=ro"
CANDIDATES = ["Stephan", "DragonKing"]  # DragonKing is this DB's name for the ShadowDragon/DragonKing identity


def load(con):
    rows = con.execute("""
        SELECT mp.match_id, m.played_at, mp.team_number, mp.player_id, mp.won,
               p.army_value_killed, p.army_value_lost, mp.id
        FROM match_players mp
        JOIN matches m ON m.id = mp.match_id
        LEFT JOIN player_match_metrics p ON p.match_player_id = mp.id
        WHERE m.played_at IS NOT NULL
        ORDER BY m.played_at ASC, mp.match_id ASC
    """).fetchall()
    matches = {}
    order = []
    for mid, played_at, team, pid, won, killed, lost, mpid in rows:
        if mid not in matches:
            matches[mid] = {"played_at": played_at, "teams": defaultdict(list),
                             "winner": None, "metrics": {}}
            order.append(mid)
        matches[mid]["teams"][team].append(pid)
        matches[mid]["metrics"][pid] = (killed, lost, mpid)
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
        usable.append((mid, m["played_at"], m["teams"][t1], m["teams"][t2], m["metrics"]))
    return usable


def assign_sessions(usable, gap_hours=4.0):
    from datetime import datetime
    session_ids, session_id, prev = [], 0, None
    for mid, played_at, *_ in usable:
        t = datetime.fromisoformat(played_at)
        if prev is not None and (t - prev).total_seconds() / 3600.0 > gap_hours:
            session_id += 1
        session_ids.append(session_id)
        prev = t
    return session_ids


def exact_roster_strata(usable, sessions, captain_name, name_to_id):
    captain_id = name_to_id.get(captain_name)
    if captain_id is None:
        return None
    groups = defaultdict(lambda: defaultdict(set))  # (session, roster) -> receiver -> {'with','against'}
    metric_complete = defaultdict(lambda: defaultdict(set))
    for (mid, played_at, t1, t2, metrics), sid in zip(usable, sessions):
        all_ids = t1 + t2
        if captain_id not in all_ids:
            continue
        roster = tuple(sorted(all_ids))
        cap_team = t1 if captain_id in t1 else t2
        for pid in all_ids:
            if pid == captain_id:
                continue
            state = "with" if pid in cap_team else "against"
            groups[(sid, roster)][pid].add(state)
            killed, lost, mpid = metrics.get(pid, (None, None, None))
            if killed is not None and lost is not None:
                metric_complete[(sid, roster)][pid].add(state)
    def summarize(d):
        switching_keys = [k for k, recv in d.items() if any(len(states) == 2 for states in recv.values())]
        sessions_switch = {k[0] for k in switching_keys}
        pairs = sum(1 for k in switching_keys for recv, states in d[k].items() if len(states) == 2)
        return len(sessions_switch), pairs
    raw_sessions, raw_pairs = summarize(groups)
    complete_sessions, complete_pairs = summarize(metric_complete)
    return dict(raw_switch_sessions=raw_sessions, raw_receiver_pairs=raw_pairs,
                metric_complete_switch_sessions=complete_sessions,
                metric_complete_receiver_pairs=complete_pairs)


def y_variance_decomposition(usable, sessions, name_to_id):
    """Variance of Y across ALL receiver-appearances in the dataset (not
    conditioned on any captain), decomposed into between-session and
    within-session components. This calibrates the power simulation's noise
    model; it does not touch the with/against comparison."""
    by_session = defaultdict(list)
    for (mid, played_at, t1, t2, metrics), sid in zip(usable, sessions):
        for pid, (killed, lost, mpid) in metrics.items():
            if killed is None or lost is None:
                continue
            y = math.log(1 + max(killed, 0)) - math.log(1 + max(lost, 0))
            by_session[sid].append(y)
    all_y = [y for ys in by_session.values() for y in ys]
    n = len(all_y)
    grand_mean = sum(all_y) / n
    session_means = {sid: sum(ys) / len(ys) for sid, ys in by_session.items()}
    between = sum(len(ys) * (session_means[sid] - grand_mean) ** 2
                  for sid, ys in by_session.items()) / n
    within = sum((y - session_means[sid]) ** 2
                 for sid, ys in by_session.items() for y in ys) / n
    return dict(n=n, n_sessions=len(by_session), grand_mean=grand_mean,
                total_var=between + within, between_session_var=between,
                within_session_var=within, total_sd=(between + within) ** 0.5)


def main():
    con = sqlite3.connect(DB, uri=True)
    usable = load(con)
    sessions = assign_sessions(usable)
    name_to_id = dict(con.execute("SELECT name, id FROM players"))

    print(f"Local DB. Usable 2-team decided matches: {len(usable)}, sessions: {len(set(sessions))}")

    print("\n-- Y variance decomposition (all receiver-appearances, no captain conditioning) --")
    decomp = y_variance_decomposition(usable, sessions, name_to_id)
    for k, v in decomp.items():
        print(f"  {k}: {v}")

    print("\n-- Exact-roster (session, full-roster) switching strata per candidate --")
    for name in CANDIDATES:
        strata = exact_roster_strata(usable, sessions, name, name_to_id)
        if strata is None:
            print(f"  {name}: not found in players table")
            continue
        print(f"  {name}:")
        for k, v in strata.items():
            print(f"    {k}: {v}")

    con.close()


if __name__ == "__main__":
    main()
