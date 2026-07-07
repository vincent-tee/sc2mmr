#!/usr/bin/env python3
"""
Migration script to add kill_death_ratio column to player_match_metrics.

Idempotent: skips if the column already exists. New uploads populate the
column via the parser; run backend/scripts/backfill_kd_ratio.py to recompute
historical rows from their stored unit counts.

Usage:
    python backend/migrations/run_012_migration.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Add kill_death_ratio column to player_match_metrics table."""
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
            if (
                "duplicate column name" in str(e).lower()
                or "already exists" in str(e).lower()
            ):
                print("✓ Column kill_death_ratio already exists, skipping")
            else:
                print(f"✗ Migration failed (adding column): {e}")
                raise


if __name__ == "__main__":
    run_migration()
