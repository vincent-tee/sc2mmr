# Deployment Guide - Stats Extraction Fix

## Overview

This guide covers deploying the stats extraction fix that resolves the "all zeros" issue in failed replay error messages. The fix implements a dual-method approach using tracker events as the primary source and player.stats as a fallback.

## What Was Fixed

### Problem
Failed replay error messages showed all zeros for supply and resources:
```
Team 1: Total supply: 0, Total resources: 0
Team 2: Total supply: 0, Total resources: 0
```

This made manual winner determination impossible.

### Root Cause
1. **Initial issue**: Code was accessing non-existent attributes (`p.supply`, `p.stats.resources_collected`)
2. **Deeper issue**: SC2 version 5.0.14.94137+ has unknown abilities that cause sc2reader to fail silently - `player.stats` object never gets created

### Solution
Implemented dual-method stats extraction:
- **Primary**: Extract from `PlayerStatsEvent` in tracker_events (works across all SC2 versions)
- **Fallback**: Use `player.stats` attributes if tracker events have no data

## Deployment Steps

### 1. Pull Latest Code

```bash
cd /home/user/sc2mmr
git fetch origin
git checkout claude/code-review-logging-ui-01SG2RJtaJHMZ7KPyzzLJC16
git pull origin claude/code-review-logging-ui-01SG2RJtaJHMZ7KPyzzLJC16
```

### 2. Verify Commits

Check that you have the tracker events fix:

```bash
git log --oneline -5
```

Expected output:
```
7cd4df6 Fix critical bug: Add missing determine_winner_from_tracker_events function
0af3ff8 Add comprehensive deployment guide for stats extraction fix
a32ebf0 Update documentation to reflect tracker events solution
54ef378 Add tracker events fallback for stats extraction (INCOMPLETE - missing function)
1700d4a Change diagnostic logging from DEBUG/WARNING to INFO level
```

Key commit: **7cd4df6** - Fix critical bug: Add missing determine_winner_from_tracker_events function

### 3. Restart Backend

Stop and restart your backend service to load the new code:

```bash
# If using systemd
sudo systemctl restart sc2mmr-backend

# If running manually
# Ctrl+C to stop, then restart with:
cd /home/user/sc2mmr/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Test the Fix

#### Option A: Upload a New Replay

1. Go to your SC2MMR frontend
2. Upload a replay (preferably one from SC2 version 5.0.14+)
3. If it fails winner determination, check the error message
4. You should see **actual stats** instead of zeros

#### Option B: Re-upload a Previous Failed Replay

1. Find a replay file that previously failed (e.g., "Floodplain (3).SC2Replay")
2. Upload it again through the frontend
3. Check if the error message now shows real stats

### 5. Monitor Backend Logs

Watch your backend logs during upload. You should see:

**Success indicators:**
```
INFO Attempting winner determination from tracker events
INFO Extracted stats from tracker events for 8 players
INFO Player ChrisO (Team 1): minerals=15,000, vespene=8,000, supply=150, total_resources=23,000
INFO Team stats extracted - Team 1: 4 still in, 450 supply, 85,000 resources
```

**If tracker events work:**
- Stats will be extracted successfully
- You'll see player-by-player stats in logs
- Team totals will show real numbers (not zeros)

**If tracker events fail but player.stats works:**
```
INFO Attempting winner determination from tracker events
INFO Tracker events had no data, falling back to player.stats method
INFO Player ChrisO (Team 1): minerals=15,000, vespene=8,000, supply=150
```

**If both fail (corrupted replay):**
```
INFO Attempting winner determination from tracker events
INFO Tracker events had no data, falling back to player.stats method
INFO Player ChrisO: NO stats object available!
INFO Team stats extracted - Team 1: 4 still in, 0 supply, 0 resources
```

### 6. Test Manual Winner Selection

Once replays have real stats in the error messages:

1. Go to **Failed Uploads** page
2. Click on a failed replay to expand details
3. Review the stats shown
4. Click **"Team 1 Won"** or **"Team 2 Won"** based on the stats
5. Verify the replay gets processed correctly

## Verification Checklist

- [ ] Backend code updated to commit `7cd4df6` or later (critical: includes tracker events function)
- [ ] Backend service restarted
- [ ] New replay uploaded OR old failed replay re-uploaded
- [ ] Backend logs show "Attempting winner determination from tracker events"
- [ ] Backend logs show player stats with non-zero values
- [ ] Failed upload error message shows real stats (not all zeros)
- [ ] Manual winner selection works (clicking "Team X Won" processes the replay)

## Troubleshooting

### Still Seeing All Zeros

**Check 1: Is this an old failed upload?**
- Old failed uploads have error messages stored in the database from before the fix
- Solution: Re-upload the same replay file

**Check 2: Is backend running updated code?**
```bash
cd /home/user/sc2mmr
git log --oneline -1
```
Should show commit `7cd4df6` or later (CRITICAL - this includes the tracker events function).

**Check 3: Are logs showing the new messages?**
```bash
# Check backend logs for:
grep "Attempting winner determination from tracker events" backend.log
```
If not found, backend wasn't restarted or code not pulled.

**Check 4: Test with debug script**
```bash
cd /home/user/sc2mmr/backend
python3 debug_replay_stats.py /path/to/replay.SC2Replay
```
This will show exactly what stats are available in the replay file.

### Frontend Not Showing Updated Stats

The frontend displays error messages from the database. If you're looking at an old failed upload:
1. The error message is what was stored when it first failed
2. Re-upload the replay to get a new error message with real stats

### Backend Crashes on Upload

Check logs for Python errors:
- Syntax errors suggest code wasn't fully pulled
- Import errors suggest missing dependencies
- Check you're on the correct branch

## What to Expect

### Before Fix
```
Unable to determine game winner from 18.7 minute game.
Team Stats Comparison:
  Team 1: Players still in: 4, Total supply: 0, Total resources: 0
    - ChrisO: IN GAME | Supply: 0 | Resources: 0
    - Tingmore: IN GAME | Supply: 0 | Resources: 0
```

### After Fix
```
Unable to determine game winner from 18.7 minute game.
Team Stats Comparison:
  Team 1: Players still in: 4, Total supply: 450, Total resources: 85,000
    - ChrisO: IN GAME | Supply: 150 | Resources: 28,000
    - Tingmore: IN GAME | Supply: 120 | Resources: 22,000
    - DragonKing: IN GAME | Supply: 100 | Resources: 20,000
    - LayManFan: IN GAME | Supply: 80 | Resources: 15,000
  Team 2: Players still in: 2, Total supply: 80, Total resources: 15,000
    - PlayerA: QUIT | Supply: 50 | Resources: 8,000
    - PlayerB: QUIT | Supply: 30 | Resources: 7,000
```

Now you can clearly see Team 1 was dominating (450 vs 80 supply) and manually select them as the winner!

## Additional Documentation

- **STATS_EXTRACTION_FIX.md** - Technical details of the fix
- **DIAGNOSING_ZERO_STATS.md** - Troubleshooting guide for zero stats issues
- **CODE_REVIEW_REPORT.md** - Comprehensive code review with all improvements

## Questions?

If stats still show zeros after following this guide:
1. Check the troubleshooting section above
2. Verify commit hash and backend restart
3. Test with the debug script on your replay file
4. Check backend logs for error messages
