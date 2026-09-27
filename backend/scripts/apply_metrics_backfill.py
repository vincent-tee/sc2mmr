"""Single-threaded, FK-enforced apply step for the metrics backfill. Reads
every shard_*.jsonl from backfill_metrics_shard.py and writes through the
app's real SessionLocal (same pattern as rating_recalculation.py). Skips a
match's kill_events if it already has any, so re-running is safe.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.models import PlayerMatchMetrics, KillEvent, Player, MatchPlayer


def apply_metrics_row(db, row):
    pmm = db.get(PlayerMatchMetrics, row["player_match_metrics_id"])
    if pmm is None:
        return False
    pmm.army_value_built = row["army_value_built"]
    pmm.army_value_killed = row["army_value_killed"]
    pmm.army_value_lost = row["army_value_lost"]
    pmm.spending_efficiency = row["spending_efficiency"]
    pmm.peak_active_workers = row["peak_active_workers"]
    pmm.units_killed = row["units_killed"]
    pmm.units_lost = row["units_lost"]
    pmm.kill_death_ratio = row["kill_death_ratio"]
    pmm.unit_composition = json.dumps(row["unit_composition"]) if row["unit_composition"] else None
    pmm.economic_score = row["economic_score"]
    pmm.combat_score = row["combat_score"]
    pmm.efficiency_score = row["efficiency_score"]
    pmm.overall_impact = row["overall_impact"]
    return True


def main():
    shard_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/backfill_shards")
    files = sorted(shard_dir.glob("shard_*.jsonl"))
    if not files:
        print(f"No shard files found in {shard_dir}")
        return

    db = SessionLocal()
    matches_with_existing_kill_events = {
        mid for (mid,) in db.query(KillEvent.match_id).distinct()
    }
    updated = missing = kills_written = kills_skipped = 0

    try:
        for f in files:
            name_to_player_id = {}
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row["type"] == "metrics":
                    if apply_metrics_row(db, row):
                        updated += 1
                    else:
                        missing += 1
                elif row["type"] == "kill_event":
                    if row["match_id"] in matches_with_existing_kill_events:
                        kills_skipped += 1
                        continue
                    if row["match_id"] not in name_to_player_id:
                        name_to_player_id[row["match_id"]] = dict(
                            db.query(Player.name, Player.id)
                            .join(MatchPlayer, MatchPlayer.player_id == Player.id)
                            .filter(MatchPlayer.match_id == row["match_id"])
                            .all()
                        )
                    lookup = name_to_player_id[row["match_id"]]
                    db.add(KillEvent(
                        match_id=row["match_id"],
                        killer_player_id=lookup.get(row["killer_name"]),
                        victim_player_id=lookup.get(row["victim_name"]),
                        unit_type=row["unit_type"],
                        game_second=row["game_second"],
                        x=row.get("x"),
                        y=row.get("y"),
                    ))
                    kills_written += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Metrics: {updated} rows updated, {missing} referenced rows no longer exist")
    print(f"Kill events: {kills_written} written, {kills_skipped} skipped (match already had kill_events)")


if __name__ == "__main__":
    main()
