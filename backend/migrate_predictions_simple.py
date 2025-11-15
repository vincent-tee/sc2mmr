#!/usr/bin/env python3
"""
Simple migration using sqlite3 module (no dependencies)
Adds prediction columns to matches table
"""
import sqlite3
import os

# Database path
db_path = os.path.join(os.path.dirname(__file__), "data", "sc2mmr.db")

print(f"Migrating database: {db_path}")
print()

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check current schema
    cursor.execute("PRAGMA table_info(matches)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    print("Current matches table columns:")
    for col_name, col_type in columns.items():
        print(f"  - {col_name}: {col_type}")
    print()

    # Check if columns need to be added
    needs_team1 = 'predicted_team1_win_prob' not in columns
    needs_team2 = 'predicted_team2_win_prob' not in columns

    if needs_team1:
        print("Adding column: predicted_team1_win_prob...")
        cursor.execute("ALTER TABLE matches ADD COLUMN predicted_team1_win_prob REAL")
        print("✓ Added predicted_team1_win_prob")
    else:
        print("✓ Column predicted_team1_win_prob already exists")

    if needs_team2:
        print("Adding column: predicted_team2_win_prob...")
        cursor.execute("ALTER TABLE matches ADD COLUMN predicted_team2_win_prob REAL")
        print("✓ Added predicted_team2_win_prob")
    else:
        print("✓ Column predicted_team2_win_prob already exists")

    if needs_team1 or needs_team2:
        conn.commit()
        print()
        print("✅ Migration completed successfully!")
        print()
        print("Existing matches will have NULL for prediction columns.")
        print("New matches will have predictions calculated during upload.")
    else:
        print()
        print("✅ No migration needed - all columns exist.")

except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
    raise
finally:
    conn.close()
