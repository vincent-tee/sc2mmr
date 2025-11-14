# Reset Database & Recalculation Guide

## How to Clear All Replays and Start Fresh

### Option 1: Clear Matches Only (Keep Players)
This clears all match data but preserves player records (with reset stats):

```bash
cd /home/user/sc2mmr/backend
python3 reset_database.py matches
# Type 'yes' to confirm
```

**What it does:**
- ✅ Deletes all matches
- ✅ Deletes all match player records
- ✅ Deletes all player metrics
- ✅ Clears failed uploads
- ✅ Resets player stats (games=0, MMR=1500, TrueSkill=25.0/8.333)
- ✅ Keeps player names in database

**Use this when:** You want to re-upload replays for the same player group

### Option 2: Clear Everything (Fresh Database)
This completely wipes the database:

```bash
cd /home/user/sc2mmr/backend
python3 reset_database.py everything
# Type 'yes' to confirm
```

**What it does:**
- ✅ Deletes everything from Option 1
- ✅ Deletes all players
- ✅ Resets auto-increment IDs

**Use this when:** You want a completely fresh start with new players

---

## How Recalculation Works During Uploads

### Automatic Recalculation (Current System)

The system **automatically recalculates ratings** as you upload replays:

1. **During Upload** (`uploadAdvanced` endpoint):
   - Parses replay file
   - Extracts player names and match data
   - **Creates/updates player records**
   - Saves match to database

2. **After Each Match Saved**:
   - **TrueSkill ratings updated** for all players in match
   - **MMR calculated** from TrueSkill (mu - 3*sigma)
   - **Stats incremented** (games, wins, losses, race stats)
   - **Synergy records updated** for team pairings

3. **Real-Time Updates**:
   - Players page shows updated ratings immediately
   - Leaderboard reflects new rankings
   - Match history includes new matches

### What Gets Recalculated

| Data | When | How |
|------|------|-----|
| **TrueSkill (mu/sigma)** | After each match | Incremental - uses current ratings + new match result |
| **MMR** | After each match | Derived from TrueSkill: `mu - 3*sigma` |
| **Win/Loss Stats** | After each match | Incremental - counts updated |
| **Race Stats** | After each match | Incremental - race-specific games tracked |
| **Player Synergies** | After each match | Incremental - team performance tracked |
| **Adaptive Model** | On-demand | Click "Refresh Analysis" to recalculate from all matches |

### Important: Match Order Matters

TrueSkill ratings are **order-dependent**:
- Each match uses the current ratings as input
- The system processes replays in the order you upload them
- If you want accurate ratings, upload replays chronologically

**Example:**
```
Match 1 (Jan 1): Alice (25.0) vs Bob (25.0) → Alice wins → Alice (27.5), Bob (22.5)
Match 2 (Jan 2): Alice (27.5) vs Bob (22.5) → Bob wins → Alice (25.8), Bob (25.2)
```

If uploaded in reverse order, ratings would be different!

---

## Best Practices for Fresh Start

### 1. Upload Chronologically
Sort your replay files by date before uploading:

```bash
# In your replays folder
ls -lt *.SC2Replay | tac  # Shows oldest first
```

### 2. Batch Upload Strategy
For many replays:
- Upload in batches of 20-50
- Wait for each batch to complete
- Check failed uploads between batches
- Fix any parsing errors before continuing

### 3. Monitor Progress
Watch the backend logs during upload:

```bash
# If using systemd
sudo journalctl -u sc2mmr-backend -f

# Or check the file logs
tail -f /path/to/backend/logs/app.log
```

### 4. Verify Ratings After Upload
After all uploads complete:
- Check Players page - ratings should be distributed
- Look at Match History - verify all matches saved
- Review Failed Uploads - fix any errors
- Check Adaptive Model - should have sufficient data after 50+ matches

---

## Re-upload Same Replays After Reset

If you want to re-upload the exact same replays:

### Method 1: Clear Failed Uploads Table
The system tracks uploaded files by hash to prevent duplicates. After reset:

```bash
cd /home/user/sc2mmr/backend
python3 reset_database.py matches  # This clears failed_uploads too
```

Now you can re-upload the same files.

### Method 2: Manual Hash Clear (If Needed)
If duplicates are still blocked:

```python
# In Python console
from app.database import SessionLocal
from app.models import FailedUpload

db = SessionLocal()
db.query(FailedUpload).delete()
db.commit()
db.close()
```

---

## Troubleshooting

### "Why are ratings not updating?"

**Check:**
1. Using `uploadAdvanced` endpoint (not basic `upload`)
2. Backend logs show "Updating ratings for match X"
3. No errors in backend logs
4. Players actually exist in database

### "Ratings seem wrong after reset"

**Likely causes:**
1. Uploaded replays out of chronological order
2. Some replays failed to parse (check Failed Uploads)
3. Mixing different player pools (e.g., different game modes)

**Solution:**
- Reset again
- Sort replays by date
- Upload chronologically
- Verify each batch completes successfully

### "Adaptive Model shows 'insufficient_data'"

**This is normal!**
- Needs 50+ matches with PlayerMatchMetrics
- Only `uploadAdvanced` saves metrics
- Check: Do matches in history have Commentary tab data?
- If not, re-upload using uploadAdvanced

---

## Quick Reference Commands

```bash
# Backup database first
cp /home/user/sc2mmr/backend/sc2mmr.db /home/user/sc2mmr/backend/sc2mmr.db.backup

# Clear matches only
cd /home/user/sc2mmr/backend
python3 reset_database.py matches

# Clear everything
python3 reset_database.py everything

# Check database status
sqlite3 sc2mmr.db "SELECT COUNT(*) FROM matches;"
sqlite3 sc2mmr.db "SELECT COUNT(*) FROM players;"
sqlite3 sc2mmr.db "SELECT name, mmr, total_games FROM players ORDER BY mmr DESC LIMIT 10;"

# Restart backend after reset
sudo systemctl restart sc2mmr-backend
```

---

## Summary

- ✅ Use `reset_database.py` to clear data
- ✅ System recalculates automatically during upload
- ✅ Upload replays chronologically for accurate ratings
- ✅ Monitor progress via backend logs
- ✅ Check Players page after upload to verify
- ✅ Adaptive Model needs 50+ matches with metrics
