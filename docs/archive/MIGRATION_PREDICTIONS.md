# Migration: Add Prediction Columns

## Issue

The `matches` table is missing columns that the model expects:
- `predicted_team1_win_prob`
- `predicted_team2_win_prob`

This causes 500 errors when uploading replays:
```
sqlite3.OperationalError: no such column: matches.predicted_team1_win_prob
```

## Solution

Run the migration script to add these columns.

## Instructions

### Option 1: Using the Simple Migration Script (Recommended)

```bash
cd backend
python3 migrate_predictions_simple.py
```

### Option 2: Manual SQL Migration

If the script doesn't work, run these SQL commands directly:

```bash
# Navigate to backend directory
cd backend

# Run SQL commands
python3 << 'EOF'
import sqlite3
import os

db_path = "data/sc2mmr.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    print("Please update the path in this script to match your setup")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE matches ADD COLUMN predicted_team1_win_prob REAL")
    cursor.execute("ALTER TABLE matches ADD COLUMN predicted_team2_win_prob REAL")
    conn.commit()
    print("✅ Migration successful!")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✅ Columns already exist - no migration needed")
    else:
        print(f"❌ Error: {e}")
        raise
finally:
    conn.close()
EOF
```

### Option 3: Using SQLite CLI

If you have `sqlite3` command-line tool:

```bash
cd backend

sqlite3 data/sc2mmr.db << 'EOF'
ALTER TABLE matches ADD COLUMN predicted_team1_win_prob REAL;
ALTER TABLE matches ADD COLUMN predicted_team2_win_prob REAL;
.quit
EOF
```

## Verification

After running the migration, verify the columns exist:

```bash
cd backend

python3 << 'EOF'
import sqlite3

conn = sqlite3.connect("data/sc2mmr.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(matches)")
columns = [row[1] for row in cursor.fetchall()]

if 'predicted_team1_win_prob' in columns and 'predicted_team2_win_prob' in columns:
    print("✅ Migration successful - columns exist!")
else:
    print("❌ Columns still missing")

conn.close()
EOF
```

## What These Columns Do

These columns store pre-match win probability predictions based on TrueSkill ratings:

- **predicted_team1_win_prob**: Probability (0.0-1.0) that Team 1 will win
- **predicted_team2_win_prob**: Probability (0.0-1.0) that Team 2 will win
- The two probabilities should sum to 1.0

These are calculated **before** the match is processed (using current player ratings) and stored for later analysis of prediction accuracy.

## Impact on Existing Data

- **Existing matches**: Will have `NULL` for these columns (that's okay)
- **New matches**: Will have predictions calculated automatically during upload
- No data loss - only adds new columns

## Troubleshooting

**Error: "unable to open database file"**
- Check that `backend/data/sc2mmr.db` exists
- Verify you're in the correct directory
- Update the path in the script if your database is elsewhere

**Error: "duplicate column name"**
- Columns already exist - migration already completed
- No action needed

**Error: "attempt to write a readonly database"**
- Check file permissions: `chmod 664 data/sc2mmr.db`
- Ensure you own the file: `chown $USER data/sc2mmr.db`

## Restart Backend

After successful migration, restart your backend server:

```bash
# If using systemd
sudo systemctl restart sc2mmr-backend

# If running manually
# Ctrl+C to stop, then:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing

Upload a replay to verify the fix:
1. Go to frontend upload page
2. Upload any .SC2Replay file
3. Should succeed without 500 errors
4. Check backend logs - no more "no such column" errors
