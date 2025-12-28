#!/usr/bin/env python3
"""
Script to fix duplicate MatchPlayer entries in the database.

This script:
1. Identifies duplicate (match_id, player_id) combinations
2. Keeps the first entry (lowest ID) and deletes the rest
3. Cleans up associated metrics and features
4. Adds a unique index to prevent future duplicates

Run from backend directory:
    python scripts/fix_duplicate_match_players.py
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal, engine


def fix_duplicates():
    """Find and remove duplicate MatchPlayer entries."""
    db = SessionLocal()

    try:
        # Step 1: Find duplicates
        print("Checking for duplicate MatchPlayer entries...")

        result = db.execute(
            text("""
            SELECT match_id, player_id, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
            FROM match_players
            GROUP BY match_id, player_id
            HAVING COUNT(*) > 1
        """)
        )

        duplicates = result.fetchall()

        if not duplicates:
            print("No duplicates found!")
        else:
            print(f"Found {len(duplicates)} duplicate combinations")

            for dup in duplicates:
                match_id, player_id, count, ids_str = dup
                ids = [int(x) for x in ids_str.split(",")]
                keep_id = min(ids)  # Keep the first one
                delete_ids = [x for x in ids if x != keep_id]

                print(
                    f"  Match {match_id}, Player {player_id}: keeping ID {keep_id}, deleting {delete_ids}"
                )

                for del_id in delete_ids:
                    # Delete associated metrics
                    db.execute(
                        text(
                            "DELETE FROM player_match_metrics WHERE match_player_id = :id"
                        ),
                        {"id": del_id},
                    )

                    # Delete associated performance features
                    db.execute(
                        text(
                            "DELETE FROM performance_features WHERE match_player_id = :id"
                        ),
                        {"id": del_id},
                    )

                    # Delete the duplicate match_player
                    db.execute(
                        text("DELETE FROM match_players WHERE id = :id"), {"id": del_id}
                    )

            db.commit()
            print(
                f"Deleted {sum(len([int(x) for x in d[3].split(',')]) - 1 for d in duplicates)} duplicate entries"
            )

        # Step 2: Check if unique index exists
        print("\nChecking for unique index...")
        result = db.execute(
            text("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_match_players_unique'
        """)
        )

        if result.fetchone():
            print("Unique index already exists")
        else:
            print("Creating unique index...")
            db.execute(
                text("""
                CREATE UNIQUE INDEX idx_match_players_unique 
                ON match_players(match_id, player_id)
            """)
            )
            db.commit()
            print("Unique index created successfully")

        print("\nDone! Database is now clean and protected against duplicates.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_duplicates()
