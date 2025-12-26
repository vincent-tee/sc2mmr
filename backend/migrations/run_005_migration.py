#!/usr/bin/env python3
"""
Run migration 005: Add Achievement System Tables

Usage:
    python migrations/run_005_migration.py
"""
import sqlite3
import os
from pathlib import Path


def run_migration():
    """Execute the migration."""
    # Find the database
    db_path = Path(__file__).parent.parent / "data" / "sc2mmr.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False

    # Read migration SQL
    migration_path = Path(__file__).parent / "005_add_achievements.sql"

    if not migration_path.exists():
        print(f"Migration file not found at {migration_path}")
        return False

    with open(migration_path, "r") as f:
        migration_sql = f.read()

    # Execute migration
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Execute each statement separately
        statements = [s.strip() for s in migration_sql.split(";") if s.strip() and not s.strip().startswith("--")]

        for statement in statements:
            if statement:
                print(f"Executing: {statement[:60]}...")
                cursor.execute(statement)

        conn.commit()
        print("\n✅ Migration 005 completed successfully!")

        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('achievements', 'player_achievements', 'player_rivalries')")
        tables = cursor.fetchall()
        print(f"Created tables: {[t[0] for t in tables]}")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
