#!/usr/bin/env python3
"""
Database Migration: Add Prediction Fields to Match Table

Adds predicted_team1_win_prob and predicted_team2_win_prob columns
to store TrueSkill-based win predictions before matches.
"""
from app.database import SessionLocal, engine
from sqlalchemy import text

def add_prediction_columns():
    """Add prediction columns to matches table."""
    db = SessionLocal()
    try:
        print("Adding prediction columns to matches table...")

        # Add predicted_team1_win_prob column
        db.execute(text(
            "ALTER TABLE matches ADD COLUMN predicted_team1_win_prob REAL"
        ))
        print("  ✓ Added predicted_team1_win_prob column")

        # Add predicted_team2_win_prob column
        db.execute(text(
            "ALTER TABLE matches ADD COLUMN predicted_team2_win_prob REAL"
        ))
        print("  ✓ Added predicted_team2_win_prob column")

        db.commit()
        print("\n✅ Migration complete!")
        print("   Existing matches will have NULL predictions.")
        print("   New matches will calculate predictions automatically.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        print("   (Columns may already exist - check schema)")
    finally:
        db.close()


if __name__ == '__main__':
    print("Match Prediction Migration")
    print("=" * 50)
    confirm = input("Add prediction columns to matches table? (yes/no): ")

    if confirm.lower() == 'yes':
        add_prediction_columns()
    else:
        print("Cancelled.")
