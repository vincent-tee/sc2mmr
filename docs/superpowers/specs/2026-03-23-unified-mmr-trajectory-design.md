# Design Specification: Unified MMR Performance Trajectory

**Created:** 2026-03-23
**Status:** Approved
**Author:** R2-D2 + User

---

## Problem Statement

### Issue 1: Performance Trajectory MMR Mismatch

**Current State:**
- Player rankings and leaderboard use `unified_mmr` (e.g., 3700)
- Performance trajectory chart displays raw `mmr` values (e.g., 2800)
- Creates confusion between rank badge and trajectory visualization

**Root Cause:**
- `MatchPlayer` table stores only `mmr_before/mmr_after` (raw TrueSkill)
- No historical storage of `unified_mmr` values
- Current `unified_mmr` calculated using player's average combat score, not per-match values

**User Impact:**
- Player sees rank badge showing 3700 MMR
- Chart peaks at 2800 MMR
- Appears to be 900 MMR discrepancy

---

### Issue 2: Recalculate Script Data Quality

**Current State:**
- `recalculate_all_mmrs.py` processes all matches
- Includes matches without `PlayerMatchMetrics` data
- Causes errors when combat scores are missing

**Root Cause:**
- No validation filter for match data completeness
- Scripts assume all matches have parsed metrics
- Silent failures or default values mask data quality issues

**User Impact:**
- Recalculate scripts may fail or produce incorrect results
- Unified MMR calculations use placeholder values
- Data quality degradation over time

---

## Solution Overview

### Core Strategy

**Store unified MMR historically** in the `MatchPlayer` table rather than calculating on-demand:

1. **Database Schema**: Add `unified_mmr_before` and `unified_mmr_after` columns to `MatchPlayer`
2. **Backfill Script**: One-time migration to populate historical values
3. **Ongoing Uploads**: Calculate unified MMR during replay processing
4. **Recalculate Integration**: Include unified MMR in full recalculation
5. **Data Quality**: Filter matches without complete metrics

---

## Technical Design

### 1. Database Schema Changes

**Migration File:** `backend/migrations/015_add_unified_mmr_to_match_players.sql`

```sql
-- Add unified MMR storage to MatchPlayer table
ALTER TABLE match_players ADD COLUMN unified_mmr_before FLOAT;
ALTER TABLE match_players ADD COLUMN unified_mmr_after FLOAT;

-- Create index for performance
CREATE INDEX idx_match_players_unified_mmr ON match_players(unified_mmr_after);
```

**Schema Comparison:**

| Column | Current | New | Purpose |
|--------|---------|-----|---------|
| `mmr_before` | ✅ Exists | ✅ Keeps | Raw TrueSkill before match |
| `mmr_after` | ✅ Exists | ✅ Keeps | Raw TrueSkill after match |
| `unified_mmr_before` | ❌ Missing | ✅ Add | Unified MMR before match |
| `unified_mmr_after` | ❌ Missing | ✅ Add | Unified MMR after match |

---

### 2. Unified MMR Calculation Formula

**Components:**
```
Unified MMR = Raw TrueSkill + Handicap Correction + Combat Bonus

Where:
- Raw TrueSkill = mu - 3*sigma (already stored in mmr_before/after)
- Handicap Correction = (actual_WR - expected_WR) * 3000
- Combat Bonus = 20 * combat_score
```

**Handicap Correction Details:**
```python
def calculate_handicap_correction(player_stats):
    """
    Calculate handicap correction based on running win rate vs expected.

    Expected WR formula:
        expected_WR = 1 / (1 + 10^(-handicap/400))

    Where handicap = (my_team_mmr - opponent_team_mmr) / my_team_size
    """
    actual_wr = player_stats['total_wins'] / player_stats['total_games']
    avg_expected_wr = player_stats['sum_expected_wr'] / player_stats['total_games']
    outperformance = actual_wr - avg_expected_wr

    return outperformance * 3000
```

**Combat Score Lookup:**
```python
def get_combat_score(session, match_player_id, fallback_avg):
    """
    Get combat score for a specific match.
    Falls back to player average if metrics missing.
    """
    metrics = session.query(PlayerMatchMetrics).filter(
        PlayerMatchMetrics.match_player_id == match_player_id
    ).first()

    return metrics.combat_score if metrics else fallback_avg
```

---

### 3. Backfill Script (One-Time Migration)

**File:** `backend/scripts/backfill_unified_mmr_history.py`

**Purpose:**
- Populate `unified_mmr_before/after` for all existing `MatchPlayer` records
- Process chronologically to maintain correct running statistics

**Algorithm:**
```python
def backfill_unified_mmr(session):
    """
    Backfill unified MMR for all existing matches.
    Processes chronologically per player to calculate correct handicap.
    """
    players = session.query(Player).all()
    total_updated = 0

    for player in players:
        logger.info(f"Processing {player.name}...")

        # Get all matches chronologically
        match_players = (
            session.query(MatchPlayer)
            .join(Match)
            .filter(MatchPlayer.player_id == player.id)
            .order_by(Match.played_at.asc())
            .all()
        )

        # Track running stats for handicap calculation
        running_stats = {
            'total_wins': 0,
            'total_games': 0,
            'sum_expected_wr': 0.0
        }

        for mp in match_players:
            # 1. Get combat score for this match
            metrics = session.query(PlayerMatchMetrics).filter(
                PlayerMatchMetrics.match_player_id == mp.id
            ).first()

            combat_score = metrics.combat_score if metrics else player.avg_combat_score

            # 2. Calculate team handicap for this match
            team_handicap = calculate_team_handicap(session, mp)
            expected_wr = 1 / (1 + 10**(-team_handicap/400))

            # 3. Update running stats
            running_stats['total_games'] += 1
            if mp.won:
                running_stats['total_wins'] += 1
            running_stats['sum_expected_wr'] += expected_wr

            # 4. Calculate handicap correction at this point in time
            actual_wr = running_stats['total_wins'] / running_stats['total_games']
            avg_expected_wr = running_stats['sum_expected_wr'] / running_stats['total_games']
            outperformance = actual_wr - avg_expected_wr
            handicap_bonus = outperformance * 3000

            # 5. Calculate and store unified MMR
            combat_bonus = 20 * combat_score

            mp.unified_mmr_before = mp.mmr_before + handicap_bonus + combat_bonus
            mp.unified_mmr_after = mp.mmr_after + handicap_bonus + combat_bonus

            total_updated += 1

        # Commit per player to avoid memory issues
        session.commit()

    logger.info(f"Backfill complete: {total_updated} MatchPlayer records updated")
    return total_updated


def calculate_team_handicap(session, match_player):
    """
    Calculate team handicap for a specific match.
    Returns: (my_team_avg_mmr - opponent_team_avg_mmr) / my_team_size
    """
    match_id = match_player.match_id
    my_team = match_player.team_number
    opponent_team = 1 if my_team == 2 else 2

    # Get team MMRs
    my_team_players = session.query(MatchPlayer).filter(
        MatchPlayer.match_id == match_id,
        MatchPlayer.team_number == my_team
    ).all()

    opponent_players = session.query(MatchPlayer).filter(
        MatchPlayer.match_id == match_id,
        MatchPlayer.team_number == opponent_team
    ).all()

    my_avg = sum(p.mmr_before for p in my_team_players) / len(my_team_players)
    opp_avg = sum(p.mmr_before for p in opponent_players) / len(opponent_players)

    return (my_avg - opp_avg) / len(my_team_players)
```

**Usage:**
```bash
cd /home/vtee/projects/sc2mmr/backend
python scripts/backfill_unified_mmr_history.py
```

**Expected Output:**
```
Processing Sirhc...
Processing Stephan...
Processing androidsine...
...
Backfill complete: 2,450 MatchPlayer records updated
```

---

### 4. Ongoing Replay Uploads

**File:** `backend/app/services/match_orchestrator.py` (or replay processing logic)

**When:** After `MatchPlayer` record is created and `PlayerMatchMetrics` are saved

**Implementation:**
```python
def process_replay_and_update_ratings(session, replay_data, ...):
    # ... existing TrueSkill calculation ...
    # ... existing MatchPlayer creation ...

    # NEW: Calculate unified MMR for each participant
    for mp in newly_created_match_players:
        player = session.query(Player).get(mp.player_id)

        # Get combat score from just-parsed metrics
        metrics = session.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id == mp.id
        ).first()

        combat_score = metrics.combat_score if metrics else player.avg_combat_score
        combat_bonus = 20 * combat_score

        # Use player's current handicap stats (updated after each match)
        handicap_bonus = (player.outperformance_pct or 0) * 3000

        # Calculate and store unified MMR
        mp.unified_mmr_before = mp.mmr_before + handicap_bonus + combat_bonus
        mp.unified_mmr_after = mp.mmr_after + handicap_bonus + combat_bonus

    session.commit()
```

**Note:** For ongoing uploads, we use the player's current handicap stats as an approximation. This is acceptable because:
- Handicap changes slowly over many matches
- Exact historical accuracy less critical for recent matches
- Can recalculate precisely anytime using backfill script

---

### 5. Recalculate Script Integration

**File:** `backend/scripts/recalculate_all_mmrs.py`

**Changes Around Line 195:**

```python
# After creating MatchPlayer record:
mp = MatchPlayer(
    match_id=match.id,
    player_id=pid,
    team_number=team_idx + 1,
    race=p_data["race"],
    won=p_data["won"],
    mu_before=mu_before,
    sigma_before=sigma_before,
    mu_after=mu_after,
    sigma_after=sigma_after,
    mmr_before=mmr_before,
    mmr_after=mmr_after,
)
session.add(mp)
session.flush()  # Get mp.id

# NEW: Calculate unified MMR
metrics = session.query(PlayerMatchMetrics).filter(
    PlayerMatchMetrics.match_player_id == mp.id
).first()

combat_score = metrics.combat_score if metrics else 25.0
combat_bonus = 20 * combat_score

# Calculate running handicap for this player
handicap_bonus = calculate_running_handicap_for_player(
    session,
    player_id=pid,
    up_to_match_id=match.id
)

mp.unified_mmr_before = mmr_before + handicap_bonus + combat_bonus
mp.unified_mmr_after = mmr_after + handicap_bonus + combat_bonus
```

**Add Helper Function:**
```python
def calculate_running_handicap_for_player(session, player_id, up_to_match_id):
    """
    Calculate handicap correction for a player up to a specific match.
    Used during recalculate to maintain chronological accuracy.
    """
    # Get all prior matches for this player (chronologically)
    prior_matches = (
        session.query(MatchPlayer)
        .join(Match)
        .filter(
            MatchPlayer.player_id == player_id,
            Match.id <= up_to_match_id
        )
        .order_by(Match.played_at.asc())
        .all()
    )

    total_wins = sum(1 for mp in prior_matches if mp.won)
    total_games = len(prior_matches)

    if total_games == 0:
        return 0.0

    # Calculate expected win rate
    sum_expected_wr = 0.0
    for mp in prior_matches:
        team_handicap = calculate_team_handicap(session, mp)
        expected_wr = 1 / (1 + 10**(-team_handicap/400))
        sum_expected_wr += expected_wr

    actual_wr = total_wins / total_games
    avg_expected_wr = sum_expected_wr / total_games
    outperformance = actual_wr - avg_expected_wr

    return outperformance * 3000
```

---

### 6. Match Validation Filter (Data Quality)

**File:** `backend/scripts/recalculate_all_mmrs.py` and `backend/recalculate_ratings.py`

**Add Validation Function:**
```python
def should_process_match(session, match_id):
    """
    Determine if a match should be included in recalculation.

    Criteria:
    1. Must have PlayerMatchMetrics for ALL participants
    2. Game duration >= 180 seconds (3 minutes minimum)
    3. All participants have valid combat_score > 0

    Returns:
        bool: True if match should be processed
    """
    # Get match
    match = session.query(Match).get(match_id)
    if not match:
        return False

    # Check minimum duration
    if match.duration_seconds < 180:
        logger.debug(f"Match {match_id}: Too short ({match.duration_seconds}s)")
        return False

    # Get all match players
    match_players = session.query(MatchPlayer).filter(
        MatchPlayer.match_id == match_id
    ).all()

    if not match_players:
        return False

    # Check if all have valid metrics
    for mp in match_players:
        metrics = session.query(PlayerMatchMetrics).filter(
            PlayerMatchMetrics.match_player_id == mp.id
        ).first()

        if not metrics:
            logger.warning(f"Match {match_id}: Player {mp.player_id} has no metrics")
            return False

        if not metrics.combat_score or metrics.combat_score <= 0:
            logger.warning(f"Match {match_id}: Player {mp.player_id} has invalid combat_score={metrics.combat_score}")
            return False

    return True
```

**Apply Filter in Recalculate Loop:**
```python
# Line 107 in recalculate_all_mmrs.py
for idx, match in enumerate(matches, 1):
    participants = match_participants.get(match.id, [])
    if not participants:
        continue

    # NEW: Validate match has required metrics
    if not should_process_match(session, match.id):
        skipped += 1
        logger.debug(f"Skipping match {match.id} - incomplete data")
        continue

    # Continue with existing TrueSkill logic...
```

**Add Summary Statistics:**
```python
# At end of recalculate script
logger.info(f"\n{'='*70}")
logger.info("✓ RECALCULATION COMPLETE")
logger.info(f"{'='*70}")
logger.info(f"Processed: {processed} matches")
logger.info(f"Skipped: {skipped} matches")
logger.info(f"  - Missing metrics: {skipped_no_metrics}")
logger.info(f"  - Invalid combat scores: {skipped_invalid_combat}")
logger.info(f"  - Too short: {skipped_duration}")
logger.info(f"Total players: {len(players)}")
logger.info(f"{'='*70}\n")
```

---

### 7. Frontend API Update

**File:** `backend/app/api/players.py`

**Endpoint:** `GET /players/{player_id}/history`

**Changes:**
```python
@router.get("/{player_id}/history", response_model=PlayerHistoryResponse)
def get_player_mmr_history(
    player_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get historical MMR data for a player to display on a chart.
    Now returns unified MMR values for consistency with rankings.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    from sqlalchemy.orm import joinedload

    match_players = (
        db.query(MatchPlayer)
        .options(joinedload(MatchPlayer.match))
        .filter(MatchPlayer.player_id == player_id)
        .join(Match)
        .order_by(Match.played_at.asc())
        .limit(limit)
        .all()
    )

    history = []
    for mp in match_players:
        if mp.match:
            # Use unified MMR if available, fallback to raw MMR
            mmr_after = mp.unified_mmr_after or mp.mmr_after
            mmr_before = mp.unified_mmr_before or mp.mmr_before

            history.append(
                MMRHistoryEntry(
                    match_id=mp.match.id,
                    played_at=mp.match.played_at,
                    mmr=round(mmr_after, 1),
                    mmr_change=round(mmr_after - mmr_before, 1),
                    won=bool(mp.won),
                    map_name=mp.match.map_name,
                )
            )

    return PlayerHistoryResponse(
        player_id=player.id,
        player_name=player.name,
        history=history
    )
```

**No Changes Needed:**
- Response model stays the same
- Frontend receives correct unified MMR values automatically
- Chart will display values matching rank badge

---

### 8. Frontend Chart Labels

**File:** `frontend/src/pages/PlayerDetail.tsx`

**Changes Around Line 268:**
```typescript
<Heading size="md" fontFamily="heading" color="gray.100" textTransform="uppercase" letterSpacing="widest">
  Performance Trajectory
</Heading>
<Text fontSize="xs" color="gray.500">
  Unified MMR progression over last 50 matches
</Text>
```

**Tooltip Update (if needed):**
```typescript
<RechartsTooltip
  contentStyle={{ backgroundColor: '#1A202C', border: '1px solid #2D3748' }}
  labelStyle={{ color: '#A0AEC0' }}
  formatter={(value: number) => [`${Math.round(value)} Unified MMR`, 'MMR']}
/>
```

---

## Implementation Checklist

### Phase 1: Database & Backfill
- [ ] Create migration `015_add_unified_mmr_to_match_players.sql`
- [ ] Run migration on database
- [ ] Write `backfill_unified_mmr_history.py` script
- [ ] Test backfill on subset of players (validation)
- [ ] Run full backfill on all players
- [ ] Verify unified MMR values match current player unified_mmr

### Phase 2: Ongoing Calculation
- [ ] Update replay upload logic to calculate unified MMR
- [ ] Test with new replay upload
- [ ] Verify new MatchPlayer records have unified_mmr_before/after

### Phase 3: Recalculate Script Updates
- [ ] Add `should_process_match()` validation function
- [ ] Integrate validation filter in recalculate loop
- [ ] Add unified MMR calculation to recalculate script
- [ ] Add summary statistics output
- [ ] Test recalculate with validation logging

### Phase 4: API & Frontend
- [ ] Update `/players/{id}/history` endpoint to return unified MMR
- [ ] Test API response has correct values
- [ ] Update frontend chart labels
- [ ] Verify chart displays unified MMR matching rank badge

### Phase 5: Testing & Validation
- [ ] Compare trajectory chart values with current unified_mmr
- [ ] Verify recalculate scripts log skipped matches
- [ ] Test with player who has incomplete match data
- [ ] Check performance of history endpoint (should be fast)
- [ ] Run full recalculate and verify no errors

---

## Files to Modify

| File | Type | Changes |
|------|------|---------|
| `backend/migrations/015_add_unified_mmr_to_match_players.sql` | New | Add unified_mmr_before/after columns |
| `backend/scripts/backfill_unified_mmr_history.py` | New | One-time migration script |
| `backend/scripts/recalculate_all_mmrs.py` | Modify | Add validation filter + unified MMR calculation |
| `backend/recalculate_ratings.py` | Modify | Add validation filter |
| `backend/app/services/match_orchestrator.py` | Modify | Calculate unified MMR on replay upload |
| `backend/app/api/players.py` | Modify | Return unified MMR in history endpoint |
| `frontend/src/pages/PlayerDetail.tsx` | Modify | Update chart labels to "Unified MMR" |

---

## Performance Considerations

### Database Performance
- **Index:** Added on `unified_mmr_after` for leaderboard queries
- **Storage:** +8 bytes per MatchPlayer record (2 FLOAT columns)
- **Total Impact:** ~20KB for 2500 records (negligible)

### API Performance
- **Before:** Calculate unified MMR for 50 matches = 50+ queries
- **After:** Read stored values = 1 query with joins
- **Improvement:** ~50x faster

### Backfill Performance
- **Expected Time:** ~30 seconds for 2500 MatchPlayer records
- **Memory:** Processes per-player, commits frequently
- **Safety:** Can run multiple times (idempotent)

---

## Data Quality Improvements

### Match Validation Criteria
1. ✅ All participants have PlayerMatchMetrics
2. ✅ All combat_score values > 0
3. ✅ Match duration >= 180 seconds

### Benefits
- Prevents calculation errors from missing data
- Clear logging of data quality issues
- Easy to identify matches needing reprocessing

### Example Log Output
```
Processed 2,234 matches
Skipped 216 matches
  - Missing metrics: 142
  - Invalid combat scores: 52
  - Too short: 22
```

---

## Rollback Plan

If issues arise:

1. **Revert Migration:**
   ```sql
   ALTER TABLE match_players DROP COLUMN unified_mmr_before;
   ALTER TABLE match_players DROP COLUMN unified_mmr_after;
   ```

2. **Revert API:**
   - Change endpoint to return `mmr_after` instead of `unified_mmr_after`
   - Frontend shows raw TrueSkill (original behavior)

3. **Data Preserved:**
   - Original `mmr_before/after` columns untouched
   - Can recalculate unified MMR anytime

---

## Testing Strategy

### Unit Tests
```python
def test_unified_mmr_calculation():
    """Test unified MMR formula components."""
    raw_mmr = 2500
    handicap_bonus = 300  # 10% outperformance
    combat_score = 28
    combat_bonus = 20 * 28  # = 560

    expected = 2500 + 300 + 560  # = 3360
    actual = calculate_unified_mmr(raw_mmr, handicap_bonus, combat_score)

    assert actual == expected

def test_should_process_match_valid():
    """Test validation accepts complete matches."""
    # Create match with all metrics
    match = create_test_match_with_metrics()
    assert should_process_match(session, match.id) == True

def test_should_process_match_missing_metrics():
    """Test validation rejects incomplete matches."""
    # Create match without metrics
    match = create_test_match_without_metrics()
    assert should_process_match(session, match.id) == False
```

### Integration Tests
1. Upload replay → verify unified MMR calculated
2. Run recalculate → verify unified MMR matches player.unified_mmr
3. Call history API → verify response contains unified MMR
4. Frontend chart → verify values match rank badge

### Manual Validation
```python
# Check unified MMR consistency
player = session.query(Player).filter(Player.name == "Sirhc").first()
latest_mp = session.query(MatchPlayer).filter(
    MatchPlayer.player_id == player.id
).order_by(MatchPlayer.id.desc()).first()

print(f"Player unified_mmr: {player.unified_mmr}")
print(f"Latest match unified_mmr_after: {latest_mp.unified_mmr_after}")
# Should be nearly identical (within 1-2 points due to rounding)
```

---

## Success Criteria

✅ Performance trajectory chart displays unified MMR values
✅ Chart values match current player unified_mmr
✅ API endpoint returns unified MMR without on-demand calculation
✅ Recalculate scripts skip matches with incomplete data
✅ Clear logging of data quality issues
✅ No performance regression in history endpoint
✅ Frontend chart labeled clearly as "Unified MMR"

---

## Future Enhancements

### Potential Improvements
1. **Admin Dashboard:** Show data quality metrics (% matches with complete parsing)
2. **Historical Charts:** Add toggle to view raw TrueSkill vs Unified MMR
3. **Component Breakdown:** Show handicap correction and combat bonus separately
4. **Trend Analysis:** Calculate MMR velocity (rate of change)

### Not in Scope
- ❌ Recalculating historical combat scores (use current per-match values)
- ❌ Changing unified MMR formula (scope is storage only)
- ❌ Modifying TrueSkill parameters (separate concern)

---

## References

- **SPEC-UNIFIED-MMR.md:** Original unified MMR specification
- **Player Model (Line 151-154):** unified_mmr definition
- **MatchPlayer Model (Line 249-292):** mmr_before/after storage
- **HandicapCorrectedMMRService:** Current handicap calculation logic

---

## Approval

**Design approved by:** User
**Date:** 2026-03-23
**Ready for implementation:** ✅ Yes
