#!/usr/bin/env python3
"""
Backfill game-stage damage metrics from stored damage_timeline.

The damage_timeline JSON is already stored in player_match_metrics,
but early_game_damage, mid_game_damage, late_game_damage weren't calculated.
This script recalculates them from the stored timeline.
"""

import json
import sqlite3
from pathlib import Path


def calculate_window_damage(damage_events: dict, start: int, end: int) -> int:
    """Get total damage in time window [start, end)."""
    return sum(dmg for sec, dmg in damage_events.items() if start <= sec < end)


def main():
    db_path = Path(__file__).parent.parent / "data" / "sc2mmr.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all records with damage_timeline
    cursor.execute("""
        SELECT id, damage_timeline, damage_dealt
        FROM player_match_metrics
        WHERE damage_timeline IS NOT NULL AND damage_timeline != ''
    """)

    records = cursor.fetchall()
    print(f"Processing {len(records)} records...")

    updated = 0
    errors = 0

    for record_id, timeline_json, damage_dealt in records:
        try:
            # Parse timeline JSON
            if not timeline_json:
                continue

            timeline_data = json.loads(timeline_json)

            # Convert string keys to integers
            damage_events = {int(k): v for k, v in timeline_data.items()}

            # Calculate game-stage damage
            early = calculate_window_damage(damage_events, 0, 300)  # 0-5 min
            mid = calculate_window_damage(damage_events, 300, 900)  # 5-15 min
            late = calculate_window_damage(damage_events, 900, 99999)  # 15+ min

            # Calculate aggression score
            total_damage = damage_dealt or (early + mid + late)
            if total_damage > 0:
                early_ratio = early / total_damage
                aggression = min(100, early_ratio * 200)
            else:
                aggression = 50.0

            # Get first damage timing
            first_damage = min(damage_events.keys()) if damage_events else None

            # Update record
            cursor.execute(
                """
                UPDATE player_match_metrics
                SET early_game_damage = ?,
                    mid_game_damage = ?,
                    late_game_damage = ?,
                    aggression_score = ?,
                    first_damage_timing = ?
                WHERE id = ?
            """,
                (early, mid, late, aggression, first_damage, record_id),
            )

            updated += 1

        except (json.JSONDecodeError, ValueError) as e:
            errors += 1
            print(f"Error processing record {record_id}: {e}")

    conn.commit()
    conn.close()

    print(f"\nDone! Updated {updated} records, {errors} errors")

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM player_match_metrics
        WHERE early_game_damage > 0 OR mid_game_damage > 0 OR late_game_damage > 0
    """
    )
    non_zero = cursor.fetchone()[0]
    print(f"Records with non-zero game-stage damage: {non_zero}")
    conn.close()


if __name__ == "__main__":
    main()
