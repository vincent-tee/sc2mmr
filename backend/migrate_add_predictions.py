#!/usr/bin/env python3
"""
Migration: Add prediction columns to matches table

Adds predicted_team1_win_prob and predicted_team2_win_prob columns to the matches table.
These columns store pre-match win probability predictions based on TrueSkill ratings.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DATABASE_URL


def migrate():
    """Add prediction columns to matches table."""
    engine = create_engine(DATABASE_URL)

    print("Starting migration: Add prediction columns to matches table")
    print(f"Database: {DATABASE_URL}")
    print()

    with engine.connect() as conn:
        # Check if columns already exist
        try:
            result = conn.execute(text("SELECT predicted_team1_win_prob FROM matches LIMIT 1"))
            result.close()
            print("✓ Column 'predicted_team1_win_prob' already exists")
            team1_exists = True
        except OperationalError:
            team1_exists = False
            print("✗ Column 'predicted_team1_win_prob' does not exist")

        try:
            result = conn.execute(text("SELECT predicted_team2_win_prob FROM matches LIMIT 1"))
            result.close()
            print("✓ Column 'predicted_team2_win_prob' already exists")
            team2_exists = True
        except OperationalError:
            team2_exists = False
            print("✗ Column 'predicted_team2_win_prob' does not exist")

        print()

        # Add missing columns
        if not team1_exists:
            print("Adding column 'predicted_team1_win_prob'...")
            conn.execute(text(
                "ALTER TABLE matches ADD COLUMN predicted_team1_win_prob REAL"
            ))
            conn.commit()
            print("✓ Added 'predicted_team1_win_prob'")

        if not team2_exists:
            print("Adding column 'predicted_team2_win_prob'...")
            conn.execute(text(
                "ALTER TABLE matches ADD COLUMN predicted_team2_win_prob REAL"
            ))
            conn.commit()
            print("✓ Added 'predicted_team2_win_prob'")

        if team1_exists and team2_exists:
            print("All columns already exist. No migration needed.")
        else:
            print()
            print("Migration completed successfully!")
            print()
            print("Note: Existing matches will have NULL values for these columns.")
            print("Predictions are calculated only for new matches during upload.")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
