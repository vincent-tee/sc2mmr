# Recency Weighting & Duplicate Detection

This document explains the duplicate detection and recency weighting features of the SC2 MMR system.

## Duplicate Replay Detection

### Overview

The system automatically detects and prevents duplicate replay uploads using SHA256 file hashing.

### How It Works

1. **Hash Generation**: When a replay is parsed, the system calculates a SHA256 hash of the entire file
2. **Storage**: The hash is stored in the `replay_hash` column of the `matches` table
3. **Duplicate Check**: Before processing any replay, the system checks if a match with the same hash already exists
4. **Prevention**: If a duplicate is found, the upload is rejected with HTTP 409 (Conflict) status

### Implementation Details

- **Hash function**: `calculate_replay_hash()` in `backend/app/replay_parser.py`
- **Database field**: `Match.replay_hash` (String, indexed for fast lookup)
- **API check**: Both `/replays/upload` and `/replays/upload-advanced` endpoints check for duplicates
- **Batch processor**: Automatically skips replays that have already been processed

### Benefits

- **No double-counting**: Players won't get rating changes from the same match multiple times
- **Data integrity**: Ensures statistical accuracy across all metrics
- **Efficient processing**: Skips duplicate files immediately without parsing

---

## Recency Weighting

### Overview

Recency weighting gives more importance to recent matches when calculating player skill ratings. This provides a more accurate estimate of **current** skill level, accounting for improvement or decline over time.

### Why Recency Weighting?

**Problem**: A player's skill changes over time. Traditional MMR treats a match from 6 months ago the same as a match from yesterday.

**Solution**: Recent matches should count more toward your current rating than older matches. If you've been improving, your recent performance better reflects your current skill.

### How It Works

The system maintains two MMR values for each player:

1. **Standard MMR** (`mmr`): Traditional TrueSkill rating (all matches weighted equally)
2. **Recency-Weighted MMR** (`recency_weighted_mmr`): Recent matches weighted more heavily

#### Exponential Decay Formula

Recency weight uses exponential decay with a **30-day half-life**:

```
weight = 0.5^(days_ago / 30)
```

**Examples**:
- Match today: weight = 1.0 (100%)
- Match 30 days ago: weight = 0.5 (50%)
- Match 60 days ago: weight = 0.25 (25%)
- Match 90 days ago: weight = 0.125 (12.5%)

#### Calculation

For each player, the recency-weighted MMR is calculated as:

```
recency_weighted_mmr = Σ(MMR_i × weight_i) / Σ(weight_i)
```

Where:
- `MMR_i` is the player's MMR after match i
- `weight_i` is the recency weight for match i
- The sum is over all matches the player has played

### Configuration

You can adjust the recency weighting behavior in `backend/app/rating_system.py`:

```python
# Recency weighting configuration
RECENCY_HALF_LIFE_DAYS = 30  # Change this to adjust decay rate
RECENCY_ENABLED = True        # Set to False to disable recency weighting
```

**Common half-life settings**:
- `14 days`: Aggressive - heavily favors very recent performance
- `30 days` (default): Balanced - good mix of recent and historical performance
- `60 days`: Conservative - slower adaptation to skill changes
- `90+ days`: Very conservative - closer to traditional MMR

### When to Use Each Rating

**Use Standard MMR** when:
- You want a long-term skill estimate
- Player activity is consistent over time
- You're analyzing historical performance

**Use Recency-Weighted MMR** when:
- You want current skill estimate for team balancing
- Players are actively improving or declining
- You have irregular play patterns (some players active, others not)
- You want to detect recent hot/cold streaks

### API Usage

All player endpoints now return both ratings:

```bash
# Get player rankings
curl http://localhost:8000/players/rankings

# Response includes both ratings:
{
  "rank": 1,
  "player": {
    "id": 1,
    "name": "PlayerName",
    "mmr": 28.5,                        # Standard MMR
    "recency_weighted_mmr": 31.2,       # Recency-weighted MMR
    "total_games": 50,
    ...
  }
}
```

### Batch Processor Output

When running the batch processor, both ratings are displayed:

```bash
python batch_process_replays.py /path/to/replays --verbose

# Output includes:
📊 FINAL PLAYER RANKINGS (min 3 games)
------------------------------------------------------------------------------------------
Rank   Player               MMR        Recent MMR   Record       Win Rate
------------------------------------------------------------------------------------------
1      Alice                28.45      31.20        12-3         80.0%
2      Bob                  27.80      26.50        10-5         66.7%

Note: 'Recent MMR' weights recent matches more heavily (30-day half-life).
```

### Migration for Existing Databases

If you already have data in your database, run the migration script to add recency-weighted ratings:

```bash
cd backend
python migrate_add_recency_weight.py
```

This script will:
1. Add the `recency_weighted_mmr` column to the players table
2. Calculate recency-weighted ratings for all existing players
3. Display the results

### Automatic Updates

Recency-weighted MMR is automatically updated:
- After every match is processed (via API or batch processor)
- Using the match date as the reference point (for batch processing)
- For all players who participated in the match

### Technical Details

#### Database Schema

```sql
-- New column added to players table
ALTER TABLE players ADD COLUMN recency_weighted_mmr FLOAT;
```

#### Implementation Files

- **Core logic**: `backend/app/rating_system.py`
  - `calculate_recency_weight()`: Calculates decay weight
  - `update_recency_weighted_rating()`: Recalculates player's weighted rating

- **Database model**: `backend/app/models.py`
  - `Player.recency_weighted_mmr`: New column

- **API responses**: `backend/app/api/players.py`
  - All player endpoints return the new field

- **Batch processor**: `backend/batch_process_replays.py`
  - Displays recency-weighted ratings in output

#### Performance Considerations

- **Calculation cost**: O(n) where n = number of matches per player
- **When calculated**: Only after matches, not on every query
- **Storage**: One additional float per player (~4 bytes)

For typical usage (50-100 matches per player), recency weighting adds negligible overhead.

---

## Best Practices

### For Team Balancing

**Recommended**: Use recency-weighted MMR for creating balanced teams
```bash
# Use recent performance for balancing
POST /teams/balance
{
  "player_ids": [1, 2, 3, 4, 5, 6],
  "use_recency_weighted": true  # Use recent form
}
```

### For Player Analysis

**Recommended**: Compare both ratings to identify trends
- If recency-weighted > standard MMR: Player is improving
- If recency-weighted < standard MMR: Player is declining or in a slump
- If ratings are similar: Consistent performance

### For Historical Analysis

**Recommended**: Use standard MMR
- More stable for long-term trends
- Not affected by short-term variance
- Better for comparing players across different time periods

---

## FAQ

**Q: What happens if I disable recency weighting?**
A: Set `RECENCY_ENABLED = False` in `rating_system.py`. The system will continue to work normally using only standard MMR. The `recency_weighted_mmr` field will not be updated.

**Q: Can I change the half-life after processing some replays?**
A: Yes! Change `RECENCY_HALF_LIFE_DAYS` and run the migration script to recalculate all recency-weighted ratings with the new decay rate.

**Q: Does recency weighting affect TrueSkill calculations?**
A: No. TrueSkill (standard MMR) continues to work exactly as before. Recency weighting is a separate, parallel calculation that doesn't interfere with the core rating system.

**Q: What if a player hasn't played in 6 months?**
A: Their recency-weighted MMR will be heavily biased toward their most recent matches before the break. When they return, new matches will quickly update their recency-weighted rating. Standard MMR provides continuity.

**Q: Should I use 30-day half-life for everyone?**
A: It depends on your group:
- **Casual groups** (play weekly/monthly): 30-60 day half-life
- **Active groups** (play multiple times per week): 14-30 day half-life
- **Tournament/league settings**: 7-14 day half-life for current form

---

## Example Use Cases

### Use Case 1: Player on Hot Streak

**Scenario**: Alice has improved significantly in the last month.

```
Alice's ratings:
- Standard MMR: 25.0 (based on 50 historical games)
- Recent MMR: 30.0 (based heavily on last 10 wins)
```

**Recommendation**: Use Recent MMR for team balancing. Alice's current skill is better reflected by her recent performance.

### Use Case 2: Returning Player

**Scenario**: Bob hasn't played in 3 months, then returns.

```
Bob's ratings after returning:
- Standard MMR: 28.0 (includes pre-break matches)
- Recent MMR: 24.0 (heavily weighted to rusty post-break matches)
```

**Recommendation**: Use Recent MMR for balancing. Bob needs time to shake off rust. After 5-10 matches, ratings will converge.

### Use Case 3: Consistent Player

**Scenario**: Charlie plays regularly with stable performance.

```
Charlie's ratings:
- Standard MMR: 26.5
- Recent MMR: 26.8
```

**Recommendation**: Either rating works. Performance is consistent. The small difference is normal variance.

---

## Summary

✅ **Duplicate Detection**: Automatically prevents duplicate replay processing
✅ **Recency Weighting**: Provides current skill estimates that adapt to improvement/decline
✅ **Configurable**: Adjust decay rate to match your group's play patterns
✅ **Automatic**: Updates happen seamlessly as replays are processed
✅ **Non-invasive**: Standard MMR continues to work as before
✅ **Migration-ready**: Easy to add to existing databases
