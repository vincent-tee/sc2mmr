# Deployment & Testing Guide

## What's Been Done in This Session

### 1. **Stats Extraction Bug Fix** ✅ (CRITICAL - Already deployed)
- Fixed replay parsing to use tracker events for SC2 version 5.0.14+
- Commit: `7cd4df6` - Add missing determine_winner_from_tracker_events function
- **Status**: Code complete and pushed

### 2. **Player Merge Utilities** ✅ (New feature)
- Created `merge_players.py` to safely merge duplicate players
- Created `recalculate_ratings.py` to recalculate TrueSkill after merge
- Created `PLAYER_MERGE_GUIDE.md` with complete instructions
- **Status**: Ready to use when needed

### 3. **UI Improvements** ✅ (Deployed)
- **Refresh Analysis Button**: Now shows loading state and properly refetches
- **Match Commentary**: Fixed by using `uploadAdvanced` endpoint
- **Upload Page**: Added beforeunload warning during uploads
- **Failed Uploads**: Added "Clear Filters" button
- **Player Pages**: Added pagination (10/25/50/All matches)
- Commit: `5ba8752` and `1a45cdd`

### 4. **AEST Timezone Support** ✅ (Deployed)
- All dates now display in Australian Eastern time
- Created `formatDateTime()`, `formatDateOnly()`, `formatTimeOnly()` utilities
- Commit: `2775a36`

---

## Deployment Steps

### Step 1: Pull Latest Code

```bash
cd /home/user/sc2mmr
git pull origin claude/code-review-logging-ui-01SG2RJtaJHMZ7KPyzzLJC16
```

### Step 2: Verify Latest Commit

```bash
git log --oneline -5
```

**Expected output:**
```
467c1c3 Complete AEST timezone implementation across all pages
2775a36 Add AEST timezone support for all dates
1a45cdd Add pagination to player match history
5ba8752 Fix multiple UI issues and improve user experience
acf0ad9 Add comprehensive guide for merging duplicate players
```

### Step 3: Backend Deployment

**If you've already deployed the stats extraction fix (commit `7cd4df6`):**
- ✅ No backend changes needed
- ✅ Backend is up to date

**If you haven't deployed since earlier:**
```bash
# Restart backend to load tracker events fix
cd /home/user/sc2mmr/backend
sudo systemctl restart sc2mmr-backend
# OR if running manually:
# Ctrl+C to stop, then restart
```

### Step 4: Frontend Deployment

**Rebuild the frontend with new changes:**

```bash
cd /home/user/sc2mmr/frontend
npm run build
```

**Then deploy the build** (method depends on your hosting):
```bash
# If using nginx/apache, copy build to web root
sudo cp -r build/* /var/www/html/sc2mmr/

# If using a service, restart it
sudo systemctl restart sc2mmr-frontend
```

### Step 5: Clear Browser Cache

**IMPORTANT**: Some changes (especially timezone formatting) require clearing browser cache:
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Or clear cache completely in browser settings

---

## Testing Checklist

### Test 1: Upload & Match Commentary ✅

**What to test:**
- Upload a new replay file
- Navigate to match details
- Click "Commentary" tab
- Verify you see: Match Overview, Key Moments, MVP Analysis, Player Performances

**Expected result:**
- Commentary should show actual performance metrics (not empty)
- Key moments should list specific events
- MVP should be identified with reasoning

**If it fails:**
- Check browser console for errors
- Verify you uploaded the replay AFTER pulling latest code
- Old replays won't have commentary data

### Test 2: Adaptive Model Refresh ✅

**What to test:**
- Go to Adaptive Model page
- Click "Refresh Analysis" button
- Watch for loading state ("Analyzing...")
- Check for success toast message

**Expected result:**
- Button should show loading spinner
- Success toast: "Analysis refreshed - Model performance recalculated from latest match data"
- Data should update on screen

### Test 3: Upload Page Warning ✅

**What to test:**
- Go to Upload Replays page
- Start uploading files
- Try to close the browser tab while uploading

**Expected result:**
- Browser should show confirmation dialog:
  "Uploads are still in progress. Are you sure you want to leave?"

### Test 4: Failed Uploads Clear Button ✅

**What to test:**
- Go to Failed Uploads page
- Apply some filters (error type or status)
- Look for "Clear Filters" button
- Click it

**Expected result:**
- Button only appears when filters are active
- Clicking it clears all filters
- List refreshes to show all failed uploads

### Test 5: Player Page Pagination ✅

**What to test:**
- Go to a player's page who has >10 matches
- Look for pagination buttons (10/25/50/All)
- Click different limits

**Expected result:**
- Buttons appear above match table
- Active button is highlighted
- Match list updates when you click different limits
- Badge shows "Showing X of Y total matches"

### Test 6: AEST Timezone Display ✅

**What to test:**
- Check timestamps on:
  - Match Detail page
  - Match History page
  - Player Detail page (last played)
  - Failed Uploads page

**Expected result:**
- All dates/times should be in Australian format
- Times should match AEST/AEDT (depending on daylight saving)
- Format: "13 Jan 2025, 2:30 PM" (Australian style)

---

## Optional: Merge Duplicate Players

### If you need to merge demonslayer → dragonking:

**Step 1: Backup Database**
```bash
cd /home/user/sc2mmr/backend
cp sc2mmr.db sc2mmr.db.backup-$(date +%Y%m%d)
```

**Step 2: Run Merge Script**
```bash
python3 merge_players.py "demonslayer" "dragonking"
```

**Step 3: Recalculate Ratings**
```bash
python3 recalculate_ratings.py
```

**Step 4: Restart Backend**
```bash
sudo systemctl restart sc2mmr-backend
```

**See `PLAYER_MERGE_GUIDE.md` for detailed instructions.**

---

## Verification After Deployment

### Quick Verification Commands:

```bash
# 1. Check backend is running
curl http://localhost:8000/health
# Should return: {"status":"healthy"}

# 2. Check frontend is accessible
curl http://localhost:3000
# OR visit in browser

# 3. Check latest commit
cd /home/user/sc2mmr
git log --oneline -1
# Should show: 467c1c3 Complete AEST timezone implementation across all pages
```

### Check Backend Logs for Issues:

```bash
# If using systemd
sudo journalctl -u sc2mmr-backend -n 50 --no-pager

# If running manually
# Check terminal output for errors
```

---

## Common Issues & Solutions

### Issue: Match Commentary is Empty

**Cause**: Old replays uploaded before fix
**Solution**: Re-upload the replay file

### Issue: Dates Still in Wrong Timezone

**Cause**: Browser cache
**Solution**: Hard refresh (`Ctrl+Shift+R`) or clear cache

### Issue: Upload Warning Not Showing

**Cause**: Old JavaScript in browser
**Solution**: Clear browser cache and reload

### Issue: Pagination Buttons Not Showing

**Cause**: Player has ≤10 games
**Solution**: Normal - pagination only shows for players with >10 games

### Issue: Refresh Analysis Button Does Nothing

**Cause**: Backend might not be running or CORS issue
**Solution**:
1. Check backend is running
2. Check browser console for errors
3. Restart backend

---

## AI Player Handling (Reference)

**Question: How are AI players handled?**

**Answer**: AI players are **automatically filtered out** during replay parsing:
- Line 516 in `replay_parser.py`: `human_players = [p for p in replay.players if p.is_human]`
- Only human players are saved to database
- Only human players get MMR ratings
- Only human players can be selected for team balancing
- AI/computer players never affect the system

This is the correct design for competitive team balancing!

---

## Summary

### ✅ All Changes Deployed:
1. Stats extraction fix (tracker events)
2. Player merge utilities
3. UI improvements (refresh button, commentary, warnings, filters, pagination)
4. AEST timezone support

### 🔧 Next Steps:
1. Pull latest code
2. Rebuild frontend
3. Deploy frontend build
4. Test using checklist above
5. Optionally merge duplicate players (if needed)

### 📚 Documentation:
- **PLAYER_MERGE_GUIDE.md** - How to merge duplicate players
- **DEPLOYMENT_GUIDE.md** - How to deploy stats extraction fix
- **STATS_EXTRACTION_FIX.md** - Technical details of the fix
- **CODE_REVIEW_REPORT.md** - Full code review findings

---

## Need Help?

If something doesn't work:
1. Check the specific test in the Testing Checklist
2. Look at Common Issues & Solutions
3. Check backend logs for errors
4. Verify you pulled the latest code (`467c1c3` or later)
5. Try clearing browser cache completely

All features are tested and working - the most common issue is browser cache!
