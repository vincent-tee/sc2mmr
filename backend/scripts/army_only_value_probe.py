"""Follow-up to docs/reviews/2026-09-15-replay-metrics-review.md finding #4:
`army_value_killed`/`army_value_lost` in player_match_metrics are actually
sc2reader's PlayerStatsEvent.resources_killed/resources_lost, which sum
army + economy + technology categories. sc2reader separately exposes the
army-only breakdown (minerals_killed_army, vespene_killed_army, and the
_lost_army equivalents). This script re-parses available local replay files
(read-only, no DB writes) to measure:
  1. How much of the stored "army_value_*" figure is actually non-army, and
     how consistent that contamination is across matches.
  2. The army-only killed/lost values, for use as a corrected endpoint.

Only matches whose replay file still exists locally can be re-parsed here
(coverage measured below). Output is written to a CSV-like text artifact for
reuse by captain_effect_fit.py; this script does not fit anything itself.
"""
import sqlite3
import sys
from pathlib import Path

import sc2reader

DB = "file:" + str(Path(__file__).resolve().parents[1] / "data/sc2mmr.db") + "?mode=ro"
OUT = Path(__file__).resolve().parents[2] / "docs/reviews/artifacts/2026-09-15-army-only-values.tsv"


def army_only_from_replay(path, protocol_pid_to_db_player):
    """Returns {db_player_id: (army_killed, army_lost, total_killed, total_lost)}
    using the LAST PlayerStatsEvent per protocol pid (cumulative counters)."""
    r = sc2reader.load_replay(path, load_level=4)
    last_event = {}
    for e in r.events:
        if e.name == "PlayerStatsEvent":
            last_event[e.pid] = e  # later events overwrite; cumulative counters
    out = {}
    for proto_pid, db_pid in protocol_pid_to_db_player.items():
        e = last_event.get(proto_pid)
        if e is None:
            continue
        army_killed = getattr(e, "minerals_killed_army", 0) + getattr(e, "vespene_killed_army", 0)
        army_lost = getattr(e, "minerals_lost_army", 0) + getattr(e, "vespene_lost_army", 0)
        total_killed = getattr(e, "resources_killed", 0)
        total_lost = getattr(e, "resources_lost", 0)
        out[db_pid] = (army_killed, army_lost, total_killed, total_lost)
    return out


def main():
    con = sqlite3.connect(DB, uri=True)
    matches = con.execute("SELECT id, replay_file_path FROM matches WHERE replay_file_path IS NOT NULL").fetchall()
    print(f"Matches with a recorded replay_file_path: {len(matches)}")

    existing = [(mid, p) for mid, p in matches if Path(p).exists()]
    print(f"Of those, file still present locally: {len(existing)}")

    # Map (match_id, team_number-ordered player) -> db player_id, keyed by name
    # since protocol pid is not stored; match by player name against replay.players.
    rows = []
    contamination_killed, contamination_lost = [], []
    parsed, skipped = 0, 0
    for mid, path in existing:
        mp_rows = con.execute(
            "SELECT mp.player_id, p.name FROM match_players mp JOIN players p ON p.id = mp.player_id "
            "WHERE mp.match_id = ?", (mid,)).fetchall()
        name_to_dbid = {name: pid for pid, name in mp_rows}
        try:
            r = sc2reader.load_replay(path, load_level=4)
        except Exception as exc:
            skipped += 1
            continue
        proto_pid_to_db = {}
        for pl in r.players:
            if pl.name in name_to_dbid:
                proto_pid_to_db[pl.pid] = name_to_dbid[pl.name]
        if len(proto_pid_to_db) != len(name_to_dbid):
            skipped += 1
            continue
        vals = army_only_from_replay(path, proto_pid_to_db)
        for db_pid, (ak, al, tk, tl) in vals.items():
            rows.append((mid, db_pid, ak, al, tk, tl))
            if tk > 0:
                contamination_killed.append(1 - ak / tk)
            if tl > 0:
                contamination_lost.append(1 - al / tl)
        parsed += 1
        if parsed % 50 == 0:
            print(f"  ...parsed {parsed} replays")

    con.close()
    print(f"\nSuccessfully re-parsed: {parsed} matches, skipped (identity mismatch/decode error): {skipped}")
    print(f"Player-match rows with usable army-only breakdown: {len(rows)}")

    if contamination_killed:
        ck = sorted(contamination_killed)
        cl = sorted(contamination_lost)
        print(f"\nNon-army fraction of stored 'army_value_killed' "
              f"(n={len(ck)}): mean={sum(ck)/len(ck):.3f}, "
              f"median={ck[len(ck)//2]:.3f}, "
              f"p10={ck[int(.1*len(ck))]:.3f}, p90={ck[int(.9*len(ck))]:.3f}")
        print(f"Non-army fraction of stored 'army_value_lost' "
              f"(n={len(cl)}): mean={sum(cl)/len(cl):.3f}, "
              f"median={cl[len(cl)//2]:.3f}, "
              f"p10={cl[int(.1*len(cl))]:.3f}, p90={cl[int(.9*len(cl))]:.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        f.write("match_id\tplayer_id\tarmy_killed\tarmy_lost\ttotal_killed\ttotal_lost\n")
        for row in rows:
            f.write("\t".join(str(x) for x in row) + "\n")
    print(f"\nWrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
