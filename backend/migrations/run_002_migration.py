#!/usr/bin/env python3
"""
Migration script to add team fight metrics to player_match_metrics table.

Usage:
    python backend/migrations/run_002_migration.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine

def run_migration():
    """Add team fight metrics columns to player_match_metrics table."""
    with engine.connect() as connection:
        try:
            connection.execute("ALTER TABLE player_match_metrics ADD COLUMN team_fight_participation REAL DEFAULT 0.0")
            print("✓ Added team_fight_participation column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ team_fight_participation column already exists")
            else:
                print(f"✗ Failed to add team_fight_participation: {e}")

        try:
            connection.execute("ALTER TABLE player_match_metrics ADD COLUMN team_fight_damage INTEGER DEFAULT 0")
            print("✓ Added team_fight_damage column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ team_fight_damage column already exists")
            else:
                print(f"✗ Failed to add team_fight_damage: {e}")

        try:
            connection.execute("ALTER TABLE player_match_metrics ADD COLUMN team_fight_damage_ratio REAL DEFAULT 0.0")
            print("✓ Added team_fight_damage_ratio column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ team_fight_damage_ratio column already exists")
            else:
                print(f"✗ Failed to add team_fight_damage_ratio: {e}")

        connection.commit()
        print("\n✓ Migration completed successfully")

if __name__ == "__main__":
    run_migration()
