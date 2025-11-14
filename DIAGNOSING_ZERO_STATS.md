# Diagnosing Zero Stats Issue

## The Problem

You're still seeing all zeros in failed upload error messages:
```
Team 1: Total supply: 0, Total resources: 0
Team 2: Total supply: 0, Total resources: 0
```

## Critical Question: When was this replay uploaded?

**The error message is stored in the database when the replay first fails.**

### If the replay was uploaded BEFORE the fix:
- ❌ The error message in the database still has zeros (from the old code)
- ✅ The fix won't retroactively update old failed uploads
- **Solution**: Re-upload the replay or manually select a winner

### If the replay was uploaded AFTER deploying the fix:
- ❌ The replay genuinely doesn't have stats data
- **Possible reasons**:
  1. Corrupted or incomplete replay file
  2. Very old SC2 version (pre-stats era)
  3. Replay ended too early (no stats recorded)
  4. Backend not restarted after deploying fix
  5. **SC2 version incompatibility** - newer SC2 versions (5.0.14+) may have unknown abilities that prevent stats extraction

## Important: Tracker Events vs Player Stats

**The final fix uses TWO methods:**

1. **Primary: Tracker Events** - Extracts stats from `PlayerStatsEvent` in tracker_events
   - More reliable across all SC2 versions
   - Works even when player.stats is None
   - This is what should work for SC2 version 5.0.14.94137+

2. **Fallback: Player Stats** - Uses player.stats.food_used[-1] if tracker events fail
   - Works for older replays
   - May fail silently on newer SC2 versions with unknown abilities

## How to Check: Frontend vs Backend

### Step 1: Check Backend Logs

After deploying the fix, look for these log messages when uploading a new replay:

**Good (working with tracker events):**
```
INFO Attempting winner determination from tracker events
INFO Extracted stats from tracker events for 8 players
INFO Player ChrisO (Team 1): minerals=15,000, vespene=8,000, supply=150, total_resources=23,000
INFO Player Tingmore (Team 1): minerals=12,000, vespene=6,000, supply=120, total_resources=18,000
INFO Team stats extracted - Team 1: 4 still in, 450 supply, 85,000 resources
INFO Team stats extracted - Team 2: 2 still in, 80 supply, 15,000 resources
```

**Good (working with player.stats fallback):**
```
INFO Attempting winner determination from tracker events
INFO Tracker events had no data, falling back to player.stats method
INFO Player ChrisO (Team 1): minerals=15,000, vespene=8,000, supply=150, total_resources=23,000
INFO Team stats extracted - Team 1: 4 still in, 450 supply, 85,000 resources
```

**Bad (not working):**
```
INFO Attempting winner determination from tracker events
INFO Tracker events had no data, falling back to player.stats method
INFO Player ChrisO: NO stats object available!
INFO Team stats extracted - Team 1: 4 still in, 0 supply, 0 resources
INFO Team stats extracted - Team 2: 4 still in, 0 supply, 0 resources
```

### Step 2: Test a Specific Replay File

Run the debug script on one of your failed replay files:

```bash
cd /home/user/sc2mmr/backend
python3 debug_replay_stats.py /path/to/failed-replay.SC2Replay
```

This will show you:
- ✅ What stat attributes are available
- ✅ Whether the replay has stats data
- ✅ What values are actually extracted

**Example good output:**
```
Player: ChrisO (Team 1)
Result: Win
Has stats: True

Available stat attributes:
  food_used: list with 1200 entries
    First: 12, Last: 150
  minerals_collection_rate: list with 1200 entries
    First: 0, Last: 15000

Extracted stats:
  Supply (food_used): 150
  Minerals: 15,000
  Vespene: 8,000
  Total Resources: 23,000
```

**Example bad output:**
```
Player: ChrisO (Team 1)
Result: Win
Has stats: False
  WARNING: No stats available for this player!
```

### Step 3: Check if Backend is Running Updated Code

The tracker events fix was committed in commit `7cd4df6`. Check your backend is running this version:

```bash
cd /home/user/sc2mmr
git log --oneline -5
```

Should show:
```
7cd4df6 Fix critical bug: Add missing determine_winner_from_tracker_events function
0af3ff8 Add comprehensive deployment guide for stats extraction fix
a32ebf0 Update documentation to reflect tracker events solution
54ef378 Add tracker events fallback for stats extraction (INCOMPLETE)
1700d4a Change diagnostic logging from DEBUG/WARNING to INFO level
```

**CRITICAL**: You MUST have commit `7cd4df6` or later. Commit `54ef378` was incomplete and will cause a NameError.

**Then restart your backend**:
```bash
# Stop the backend
# Start the backend again
```

## Frontend Display

The frontend just displays the error message from the database. It doesn't process stats itself.

**Data flow:**
1. Backend: Replay uploaded → Stats extracted → Stored in DB
2. Backend: If winner determination fails → Error message with stats stored in `failed_uploads` table
3. Frontend: Fetches `failed_uploads` from DB → Displays error message

So if you're seeing zeros:
- ✅ Frontend is working correctly
- ❌ Backend either:
  - Hasn't been updated/restarted
  - OR the replay genuinely has no stats

## Solution Steps

### 1. For OLD Failed Uploads (uploaded before fix)

These will always show zeros because that's what was stored in the database.

**Option A: Re-upload the replay**
- Upload it again with the new code
- New stats will be extracted

**Option B: Manually select winner**
- Look at the replay in SC2
- Click "Team 1 Won" or "Team 2 Won" in the failed uploads UI
- This bypasses automatic winner determination

### 2. For NEW Uploads (after deploying fix)

**Test with a fresh replay:**
```bash
# 1. Make sure backend is updated and restarted
cd /home/user/sc2mmr
git pull
# Restart backend

# 2. Upload a NEW replay through the UI

# 3. Check backend logs for the stat extraction messages

# 4. If it still shows zeros, run the debug script on that replay file
```

### 3. Enable Debug Logging

To see all the detailed logs, set your backend logging level to DEBUG:

```python
# In backend/app/main.py or wherever logging is configured
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Then you'll see messages like:
```
DEBUG Player ChrisO stats attributes: ['__class__', 'food_used', 'minerals_collection_rate', ...]
DEBUG Player ChrisO: food_used is list with 1200 entries, final=150
DEBUG Player ChrisO: minerals_collection_rate final=15000
```

## Expected Behavior After Fix

**When a replay fails winner determination:**

**Before (broken):**
```
Team 1: Total supply: 0, Total resources: 0
  - ChrisO: IN GAME | Supply: 0 | Resources: 0
```

**After (fixed):**
```
Team 1: Total supply: 450, Total resources: 85,000
  - ChrisO: IN GAME | Supply: 150 | Resources: 23,000
  - Tingmore: IN GAME | Supply: 120 | Resources: 18,000
```

With actual stats, you can:
- ✅ See which team was winning
- ✅ Manually determine the correct winner
- ✅ Understand why the game was ambiguous

## TL;DR Checklist

- [ ] Backend code updated to commit `7cd4df6` (tracker events fix - COMPLETE) or later
- [ ] **CRITICAL**: Do NOT use commit `54ef378` - it's incomplete and will crash
- [ ] Backend restarted after updating
- [ ] Test with a NEW replay upload (not an old failed one)
- [ ] Check backend logs for:
  - [ ] "Attempting winner determination from tracker events"
  - [ ] "Extracted stats from tracker events for X players"
  - [ ] "Player X (Team Y): minerals=..., vespene=..., supply=..."
- [ ] If still zeros, run `debug_replay_stats.py` on the replay file
- [ ] If replay has no stats, file is corrupted/incomplete/too old

---

**Most likely issues:**
1. **OLD failed upload** - Error from BEFORE the fix was deployed → Re-upload the replay
2. **SC2 version 5.0.14+** - Newer versions need tracker events fix (commit `7cd4df6`)
3. **Incomplete fix** - If you have commit `54ef378`, upgrade to `7cd4df6` (the function was missing)
4. **Backend not restarted** - Old code still running → Restart backend after pulling latest code
