#!/usr/bin/env python3
"""
Migration script to add is_ai column to players table.

Usage:
    python backend/migrations/run_008_add_is_ai_to_players.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine
from sqlalchemy import text


def run_migration():
    """Add is_ai column to players table."""
    with engine.connect() as connection:
        try:
            # 1. Add the column
            connection.execute(
                text("ALTER TABLE players ADD COLUMN is_ai INTEGER DEFAULT 0")
            )
            connection.commit()
            print("✓ Successfully added is_ai column to players table")
        except Exception as e:
            if (
                "duplicate column name" in str(e).lower()
                or "already exists" in str(e).lower()
            ):
                print("✓ Column is_ai already exists, skipping addition")
            else:
                print(f"✗ Migration failed (adding column): {e}")
                raise

        try:
            # 2. Heuristic update for existing AI players
            result = connection.execute(
                text("UPDATE players SET is_ai = 1 WHERE name LIKE 'Computer %'")
            )
            connection.commit()
            if hasattr(result, "rowcount"):
                print(f"✓ Heuristic update applied to {result.rowcount} players")
            else:
                print("✓ Heuristic update applied")
        except Exception as e:
            print(f"⚠️ Heuristic update failed (non-critical): {e}")


if __name__ == "__main__":
    run_migration()
