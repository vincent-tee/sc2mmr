# Stats Extraction Bug Fix

## What Was Wrong

Your failed replays showed **all zeros** for supply and resources:
```
Team 1: 0 supply, 0 resources
Team 2: 0 supply, 0 resources
```

This made it impossible to determine winners, even for games where one team clearly dominated.

## Root Cause

The replay parser was accessing stats incorrectly. SC2Reader stores stats as **time-series arrays**, not single values:

```python
# WRONG (always returns 0)
supply = p.supply  # Doesn't exist
resources = p.stats.resources_collected  # Doesn't exist

# RIGHT (gets final value from array)
supply = p.stats.food_used[-1]  # Last value in time series
minerals = p.stats.minerals_collection_rate[-1]  # Last value
vespene = p.stats.vespene_collection_rate[-1]  # Last value
resources = minerals + vespene
```

## What Changed

### 1. Proper Stats Extraction
- ✅ Extract final supply from `food_used` time series
- ✅ Calculate total resources from minerals + vespene collection rates
- ✅ Handle both list and single value formats safely

### 2. Better Debugging
- ✅ Per-player debug logging: `Player ChrisO: minerals=15000, vespene=8000, supply=150`
- ✅ Team totals logging: `Team 1: 4 still in, 450 supply, 85,000 resources`
- ✅ Winner determination method logging

### 3. Example Output (After Fix)

**Old Error Message** (useless):
```
Team Stats Comparison:
  Team 1:
    Players still in: 4
    Total supply: 0
    Total resources: 0
      - ChrisO: IN GAME | Supply: 0 | Resources: 0
      - Tingmore: IN GAME | Supply: 0 | Resources: 0
```

**New Error Message** (actionable):
```
Team Stats Comparison:
  Team 1:
    Players still in: 4
    Total supply: 450
    Total resources: 85,000
      - ChrisO: IN GAME | Supply: 150 | Resources: 28,000
      - Tingmore: IN GAME | Supply: 120 | Resources: 22,000
      - DragonKing: IN GAME | Supply: 100 | Resources: 20,000
      - LayManFan: IN GAME | Supply: 80 | Resources: 15,000
  Team 2:
    Players still in: 2
    Total supply: 80
    Total resources: 15,000
      - PlayerA: QUIT | Supply: 50 | Resources: 8,000
      - PlayerB: QUIT | Supply: 30 | Resources: 7,000
```

**Automatic Winner Detection**:
```
✅ Team 1 determined winner by supply advantage (450 vs 80)
```

## Impact on Your Failed Replays

Now you can:
1. **See actual stats** instead of zeros
2. **Manually determine winners** based on supply/resources
3. **Understand why games failed** (close stats vs missing data)
4. **Better decide** which team actually won

## How to Use Manual Winner Selection

1. Go to **Failed Uploads** page
2. Click on a failed replay to expand details
3. Review the **Team Stats Comparison**
4. Look at:
   - Players still in game
   - Total supply (army + workers)
   - Total resources collected
5. Click **"Team 1 Won"** or **"Team 2 Won"** based on stats
6. Replay will be processed with manual winner determination

## Next Steps

1. **Deploy this fix** to your server
2. **Check existing failed replays** - they should now show stats
3. **Manually process** replays with ambiguous results
4. **Monitor logs** for `Team stats extracted` messages

## Troubleshooting

If stats still show zeros after this fix:
- Check logs for `Player X: minerals=X, vespene=X, supply=X`
- If you see `minerals=0, vespene=0`, the replay might be corrupted
- Try opening the replay in SC2 to verify it's valid

## Core Player vs Outsider

**Everyone shows "Core Player" because**:
- Default database value is `is_core_player = 1` (TRUE)
- This is intentional design:
  - **Core Players** = Regular group members (default)
  - **Outsiders** = Guest players who don't play regularly

**To mark someone as an outsider**:
```bash
# Use the create player endpoint with is_core_player=false
POST /players
{
  "name": "GuestPlayer",
  "is_core_player": false
}
```

**Why this design?**:
- Most players in your group are regulars
- Outsiders/guests are the exception
- Outsiders can be quick-calibrated to similar core player's rating
- Leaderboards can filter to core-only

**Optional: Hide "Core Player" badge** (since it's redundant):
- We can change it to only show "Outsider" badge for non-core players
- Let me know if you want this change!
