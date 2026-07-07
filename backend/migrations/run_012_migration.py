#!/usr/bin/env python3
"""
Migration script to add kill_death_ratio column to player_match_metrics.

Idempotent: skips (without touching anything) if the column already exists.
Otherwise the DB file is backed up to a timestamped copy via SQLite's online
backup API before the ALTER (house rule: timestamped backup before writing to
the live DB). New uploads populate the column via the parser; run
backend/scripts/backfill_kd_ratio.py to recompute historical rows from their
stored unit counts.

Usage:
    python backend/migrations/run_012_migration.py
"""

import os
import sqlite3
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, DATABASE_PATH
from sqlalchemy import text


def backup_db(db_path: str) -> str:
    """Timestamped, WAL-safe backup via SQLite's online backup API."""
    backup_path = f"{db_path}.backup_{time.strftime('%Y%m%d_%H%M%S')}"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(backup_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return backup_path


def run_migration():
    """Add kill_death_ratio column to player_match_metrics table."""
    with engine.connect() as connection:
        # Idempotency check first, so a no-op run makes no backup and no writes.
        columns = [
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(player_match_metrics)")
            )
        ]
        if "kill_death_ratio" in columns:
            print("✓ Column kill_death_ratio already exists, skipping")
            return

    backup = backup_db(DATABASE_PATH)
    print(f"✓ Backed up DB to {backup}")

    with engine.connect() as connection:
        try:
            connection.execute(
                text(
                    "ALTER TABLE player_match_metrics "
                    "ADD COLUMN kill_death_ratio REAL DEFAULT 1.0"
                )
            )
            connection.commit()
            print("✓ Successfully added kill_death_ratio to player_match_metrics")
        except Exception as e:
            print(f"✗ Migration failed (adding column): {e}")
            print(f"  Rollback point: {backup}")
            raise


if __name__ == "__main__":
    run_migration()
