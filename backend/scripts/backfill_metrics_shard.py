"""One shard of the metrics backfill: parses this shard's matches with
UnifiedParser (read-only against the DB) and writes one JSONL file per
shard. apply_metrics_backfill.py does the actual DB write. See
docs/reviews/2026-09-16-parser-field-audit.md for what changed and why.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.unified_parser import UnifiedParser

DB = "file:data/sc2mmr.db?mode=ro"


def match_player_ids(con, match_id):
    rows = con.execute(
        """
        SELECT p.name, pmm.id
        FROM match_players mp
        JOIN players p ON p.id = mp.player_id
        LEFT JOIN player_match_metrics pmm ON pmm.match_player_id = mp.id
        WHERE mp.match_id = ?
        """,
        (match_id,),
    ).fetchall()
    return dict(rows)


def main():
    shard_idx = int(sys.argv[1])
    num_shards = int(sys.argv[2])
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB, uri=True)
    rows = con.execute(
        "SELECT id, replay_file_path FROM matches "
        "WHERE replay_file_path IS NOT NULL AND replay_file_path != '' ORDER BY id"
    ).fetchall()
    rows = [(mid, path) for mid, path in rows if os.path.exists(path)]
    shard = [r for i, r in enumerate(rows) if i % num_shards == shard_idx]

    import logging
    logging.getLogger("app.services.unified_parser").setLevel(logging.ERROR)

    parser = UnifiedParser()
    out_path = out_dir / f"shard_{shard_idx}.jsonl"
    n_ok = n_failed = n_metrics_rows = n_kill_events = 0

    with open(out_path, "w") as out:
        for mid, path in shard:
            try:
                result = parser.parse(path)
            except Exception:
                n_failed += 1
                continue
            n_ok += 1
            pmm_ids = match_player_ids(con, mid)

            for pr in result.players:
                pmm_id = pmm_ids.get(pr.name)
                if pmm_id is None:
                    continue
                out.write(json.dumps({
                    "type": "metrics",
                    "player_match_metrics_id": pmm_id,
                    "army_value_built": pr.army_value_built,
                    "army_value_killed": pr.army_value_killed,
                    "army_value_lost": pr.army_value_lost,
                    "spending_efficiency": pr.spending_efficiency,
                    "peak_active_workers": pr.peak_active_workers,
                    "units_killed": pr.units_killed,
                    "units_lost": pr.units_lost,
                    "kill_death_ratio": pr.kill_death_ratio,
                    "unit_composition": pr.unit_composition,
                    "economic_score": pr.economic_score,
                    "combat_score": pr.combat_score,
                    "efficiency_score": pr.efficiency_score,
                    "overall_impact": pr.overall_impact,
                }) + "\n")
                n_metrics_rows += 1

            for ev in result.kill_events:
                out.write(json.dumps({"type": "kill_event", "match_id": mid, **ev}) + "\n")
                n_kill_events += 1

    con.close()
    print(f"shard {shard_idx}/{num_shards}: parsed_ok={n_ok} failed={n_failed} "
          f"metrics_rows={n_metrics_rows} kill_events={n_kill_events} -> {out_path}")


if __name__ == "__main__":
    main()
