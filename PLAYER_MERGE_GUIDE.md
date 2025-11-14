# Player Merge Guide

## Merging Duplicate Players (demonslayer + dragonking)

When you have duplicate player accounts that represent the same person, you can merge them using the `merge_players.py` script.

## Step 1: Decide Which Name to Keep

You need to choose which player name will be the **primary** (kept) and which will be the **duplicate** (deleted).

**Current situation:**
- `demonslayer` - will be merged FROM
- `dragonking` - will be kept

**Note**: Choose the name you want to keep carefully! The duplicate player will be permanently deleted.

## Step 2: Backup Your Database (IMPORTANT!)

```bash
# If using SQLite
cp backend/sc2mmr.db backend/sc2mmr.db.backup

# If using PostgreSQL
pg_dump your_database > backup.sql
```

## Step 3: Run the Merge Script

```bash
cd /home/user/sc2mmr/backend
python3 merge_players.py "demonslayer" "dragonking"
```

**What this does:**
1. Shows you stats for both players
2. Asks for confirmation
3. Transfers all match records from demonslayer → dragonking
4. Merges PlayerSynergy records (games played with teammates)
5. Combines statistics (total games, wins, losses, race preferences)
6. Deletes the duplicate player

**Example output:**
```
============================================================
MERGING PLAYERS
============================================================
FROM (will be deleted): demonslayer (ID: 5)
  - Total games: 47
  - W/L: 25/22
  - MMR: 1245 (mu=26.5, sigma=5.2)

INTO (will be kept): dragonking (ID: 12)
  - Total games: 38
  - W/L: 20/18
  - MMR: 1210 (mu=26.1, sigma=5.5)
============================================================

Proceed with merge? This will DELETE 'demonslayer' and move all their data to 'dragonking'. Type 'yes' to confirm: yes

1. Updating 47 MatchPlayer records...
2. Merging PlayerSynergy records...
   - Found 3 synergies where duplicate is player1
   - Found 2 synergies where duplicate is player2
   - Merging synergy with player 3
   - Moving synergy with player 7
3. Merging player statistics...
   - New total games: 85
   - New W/L: 45/40
   - Win rate: 52.9%
4. TrueSkill rating will need to be recalculated...
   NOTE: You should run recalculate_ratings.py after this merge
   to properly recalculate TrueSkill ratings from match history

✓ MERGE COMPLETE
Player 'demonslayer' has been merged into 'dragonking'

Final stats for 'dragonking':
  - Total games: 85
  - W/L: 45/40 (52.9% win rate)
  - Favorite race: Zerg

IMPORTANT: Run 'python3 recalculate_ratings.py' to recalculate TrueSkill ratings!
```

## Step 4: Recalculate TrueSkill Ratings

After merging, the TrueSkill ratings will be incorrect because we just combined stats from two players. You need to recalculate from scratch:

```bash
cd /home/user/sc2mmr/backend
python3 recalculate_ratings.py
```

**What this does:**
1. Resets ALL players to default TrueSkill (mu=25.0, sigma=8.333)
2. Processes ALL matches in chronological order
3. Recalculates ratings using the TrueSkill algorithm
4. Updates all player statistics
5. Recalculates recency-weighted MMR

**Example output:**
```
⚠️  WARNING: This will recalculate ALL player ratings!
This process will:
  - Reset all players to default TrueSkill (mu=25.0, sigma=8.333)
  - Process all matches in chronological order
  - Recalculate ratings and statistics
  - Update all MatchPlayer records

This is IRREVERSIBLE. Make a database backup first!

Do you want to continue? Type 'yes' to confirm: yes

Step 1: Resetting all players to default ratings...
   Reset 15 players to default (mu=25.0, sigma=8.333)

Step 2: Loading all matches in chronological order...
   Found 342 matches to process

Step 3: Backing up match participation data...
   Backed up participation data for 342 matches

Step 4: Clearing existing MatchPlayer records...
   ✓ Cleared all MatchPlayer records

Step 5: Processing matches and recalculating ratings...
   Progress        Match Date           Map                       Game Mode
   --------------- -------------------- ------------------------- ---------------
   100/342        2024-01-15 14:32:18  Oceanborn                 4v4
   200/342        2024-02-08 19:45:22  Stargazers                4v4
   300/342        2024-03-12 16:21:09  Floodplain                4v4
   342/342        2024-04-01 20:15:44  Dynasty                   4v4

Step 6: Applying final ratings to all players...

Step 7: Recalculating recency-weighted MMR...
   ✓ Updated recency-weighted MMR for 15 players

======================================================================
✓ RECALCULATION COMPLETE
======================================================================
Processed: 342 matches
Skipped: 0 matches
Total players: 15
======================================================================
```

## Step 5: Restart Your Backend

After merging and recalculating, restart your backend server:

```bash
# If using systemd
sudo systemctl restart sc2mmr-backend

# If running manually
# Ctrl+C to stop, then restart
cd /home/user/sc2mmr/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Step 6: Verify in Frontend

1. Go to your SC2MMR frontend
2. Check the **Leaderboard** - you should only see "dragonking"
3. Check "dragonking's" **Player Profile** - should show combined stats (85 games)
4. Check **Match History** - should show all matches from both accounts

## Troubleshooting

### "Player not found"
- Check spelling - player names are case-sensitive
- Run `sqlite3 backend/sc2mmr.db "SELECT name FROM players;"` to see all player names

### "Rating seems wrong after merge"
- Make sure you ran `recalculate_ratings.py` after merging
- The recalculation processes all matches chronologically to get accurate ratings

### "Some matches missing"
- Matches aren't missing - they're just now associated with "dragonking" instead of "demonslayer"
- Check the match history for "dragonking" - it should have all matches from both accounts

### "Can I undo this?"
- Only if you made a database backup before merging
- Restore from backup: `cp backend/sc2mmr.db.backup backend/sc2mmr.db`

## Summary Commands

```bash
# 1. Backup database
cp backend/sc2mmr.db backend/sc2mmr.db.backup

# 2. Merge players
cd /home/user/sc2mmr/backend
python3 merge_players.py "demonslayer" "dragonking"

# 3. Recalculate ratings
python3 recalculate_ratings.py

# 4. Restart backend
sudo systemctl restart sc2mmr-backend
```

## What Gets Merged

✅ **Merged/Combined:**
- All match records (MatchPlayer)
- Player synergies (PlayerSynergy)
- Total games, wins, losses
- Race statistics (Terran/Protoss/Zerg/Random games)
- Impact score history
- All timestamps (keeps earliest created_at, latest last_played)

✅ **Recalculated:**
- TrueSkill ratings (mu, sigma)
- MMR
- Recency-weighted MMR
- Average impact scores
- Win rate

❌ **Not Affected:**
- Match records themselves
- PlayerMatchMetrics (detailed match stats)
- Failed uploads
- Other players

## Notes

- The merge is **permanent** - make a backup first!
- Always run `recalculate_ratings.py` after merging
- The recalculation can take 1-2 minutes for hundreds of matches
- All other players' ratings will also be recalculated (this is good - ensures accuracy)
