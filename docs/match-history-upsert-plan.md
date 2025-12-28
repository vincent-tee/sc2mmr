# Implementation Plan: Match History & Database Upsert

---

## Overview

This plan documents the strategy for updating the match history page to support enhanced dramatic analytics and implementing database upsert logic to allow re-processing existing matches.

---

## Part 1: Critical Bug Fix

### 1.1 Problem
The `damage_taken` metric is always 0 because the code incorrectly tries to access `event.unit_pid` which doesn't exist in sc2reader's `UnitDiedEvent`.

### 1.2 Solution

**File:** `backend/app/advanced_parser.py`, lines 487-497

```python
# DAMAGE DEALT (killer tracking)
if event.killer_pid and event.killer_pid in player_metrics:
    killer_pid = event.killer_pid
    player_metrics[killer_pid].army_value_killed += unit_cost
    player_metrics[killer_pid].units_killed += 1

# DAMAGE TAKEN (owner tracking)
if event.unit and hasattr(event.unit, "owner"):
    owner = event.unit.owner
    if hasattr(owner, "pid") and owner.pid in player_metrics:
        owner_pid = owner.pid
        player_metrics[owner_pid].army_value_lost += unit_cost
        player_metrics[owner_pid].units_lost += 1
```

### 1.3 Frontend Display Enhancement

**File:** `frontend/src/components/charts/ImpactScoreRadar.tsx`, lines 243-256

```typescript
{metrics.damage_ratio !== undefined && (
  <Box p={3} bg="rgba(30, 41, 59, 0.5)" borderRadius="md">
    <HStack justify="space-between">
      <Text fontSize="sm" color="gray.400">
        {metrics.damage_taken > 0 ? 'Damage Efficiency' : 'Damage Ratio'}
      </Text>
      <Text fontSize="lg" fontWeight="bold" color={metrics.damage_ratio >= 1 ? 'green.400' : 'orange.400'}>
        {metrics.damage_taken > 0
          ? `${metrics.damage_ratio.toFixed(2)}x`
          : '∞ (Perfect Game)'}
      </Text>
    </HStack>
)}
```

---

## Part 2: Match History Page Updates

### 2.1 Tab System Architecture

**File:** `frontend/src/pages/MatchHistory.tsx`

```typescript
// Tab state management
const [activeTab, setActiveTab] = useState<string>('players');

// Tab components
import { PlayersTab } from './MatchHistory/PlayersTab';
import { CommentaryTab } from './MatchHistory/CommentaryTab';
import { AnalyticsTab } from './MatchHistory/AnalyticsTab';
import { SynergyTab } from './MatchHistory/SynergyTab';
```

### 2.2 Tabs to Create

1. **PlayersTab** (existing - verify avatars work correctly)
   - Ensure avatars use DiceBear mascots
   - Verify `getPlayerAvatarUrl()` is imported and used

2. **CommentaryTab** (NEW - enhanced SHAP display)
   - Story-based feature names instead of technical ones
   - Rename `mmr_diff` → "Skill Gap"
   - Rename `apm_diff` → "Blazing Fingers"
   - Rename `damage_dealt_diff` → "Sledgehammer"
   - Rename `economic_score_diff` → "Money Power"
   - Add narrative player performances
   - Match-specific achievement badges ("Moments of Glory")

3. **AnalyticsTab** (NEW - Match Story architecture)
   - Match headline generator (dramatic titles)
   - Narrative Arc sections (Opening Fire, Mid-Game Clash, Breaking Point)
   - Performance Identity cards with dramatic titles
   - Synergy Spotlight (Power Duo analysis)
   - "What If?" scenarios
   - Match DNA fingerprinting

4. **SynergyTab** (NEW)
   - Top player duos analysis
   - Team chemistry metrics
   - Duo titles ("The Butcher & The Baker", "Fire & Ice")

---

## Part 3: Database Upsert Logic

### 3.1 Current Behavior (Strict Reject)

**File:** `backend/app/api/replays.py`, lines 265-273

```python
existing_match = (
    db.query(Match).filter(Match.replay_hash == replay_data.replay_hash).first()
)

if existing_match:
    raise HTTPException(
        status_code=409,
        detail=f"Replay already uploaded. Match ID: {existing_match.id}",
    )
```

**Problems:**
- Same replay can't be re-uploaded (even if you want to add features)
- Existing match data can't be updated
- User gets 409 error instead of updated data

### 3.2 Proposed Upsert Logic

**File:** `backend/app/api/replays.py` - add new function at end of file

```python
def upsert_match(db: Session, replay_data: ReplayData) -> Tuple[Match, bool]:
    """
    Insert or update match based on replay_hash.
    Returns (match, created) tuple where created is True for new match.

    Args:
        db: Database session
        replay_data: Parsed replay data from sc2reader

    Returns:
        Tuple of (Match, bool) where Match is the match object and bool indicates
        if this was a new insertion or an update of existing match.
    """
    existing = db.query(Match).filter(
        Match.replay_hash == replay_data.replay_hash
    ).first()

    if existing:
        # UPDATE existing match
        match = existing

        # Update fields that may have changed on re-upload
        if replay_data.predicted_team1_win_prob is not None:
            match.predicted_team1_win_prob = replay_data.predicted_team1_win_prob
        if replay_data.predicted_team2_win_prob is not None:
            match.predicted_team2_win_prob = replay_data.predicted_team2_win_prob

        # Update replay file path (if changed)
        match.replay_file_path = replay_data.replay_file_path

        # Update replay hash (in case algorithm changes)
        match.replay_hash = replay_data.replay_hash

        # Keep original upload time
        # created_at stays the same

        db.commit()

        return match, False  # Updated existing match
    else:
        # CREATE new match (keep existing logic)
        match = Match(
            played_at=replay_data.played_at,
            game_mode=replay_data.game_mode,
            map_name=replay_data.map_name,
            duration_seconds=replay_data.duration_seconds,
            replay_file_path=replay_data.replay_file_path,
            replay_hash=replay_data.replay_hash,
            predicted_team1_win_prob=replay_data.predicted_team1_win_prob,
            predicted_team2_win_prob=replay_data.predicted_team2_win_prob,
            created_at=datetime.utcnow(),
        )

        db.add(match)
        db.commit()

        return match, True  # Created new match
```

### 3.3 Update Upload Functions

**Modify both functions to use upsert:**

```python
# In upload_replay(), replace lines 265-273 with:
match, created = upsert_match(db, replay_data)

# In upload_replay_advanced(), replace lines 1054-1063 with:
match, created = upsert_match(db, replay_data)
```

---

## Part 4: Implementation Priority

| Phase | Tasks | Effort | Priority | Dependencies |
|--------|--------|---------|-----------|--------------|
| **Phase 1** | Bug Fix + Display Enhancement | 2 files, ~1 hour | **CRITICAL** | None |
| **Phase 2** | Match History Tabs (Players, Commentary, Analytics, Synergy) | 6-8 new components, 6-8 hours | **HIGH** | Phase 1 complete |
| **Phase 3** | Database Upsert Logic | 1 file, ~30 min | **HIGH** | Phase 1 complete |

---

## Part 5: Database Schema Updates (Optional)

If implementing upsert, consider adding tracking column:

```sql
ALTER TABLE matches ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

This allows tracking when matches are re-uploaded with new features.

---

## Part 6: Testing Strategy

### Database Upsert Testing
1. Upload a sample replay
2. Note the Match ID returned
3. Upload same replay again
4. Verify: Same Match ID returned (not a 409 error)
5. Check database: Updated fields, not a new duplicate record

### Frontend Testing
1. Navigate to match history
2. Test tab switching between Players, Commentary, Analytics, Synergy
3. Verify avatars display correctly with DiceBear mascots
4. Verify new features (Performance Identities, Synergy, etc.) render without errors
5. Test damage ratio display shows "Perfect Game" for 0 damage_taken
6. Test with match that has enhanced data vs basic data

---

## Questions

### Q1: File Organization
Should I create a new directory `frontend/src/pages/MatchHistory/` containing all 4 tab components?

**Option A:** Separate directory (better organization, easier to maintain)
**Option B:** Single file `MatchHistory.tsx` (simpler imports, longer file)

### Q2: Implementation Order
Should I proceed with **Phase 1** (Bug Fix + Display Enhancement) first? This takes ~1 hour and immediately resolves infinite ratio issue affecting all match views.

**Next Phase Options:**
- **Option A:** Implement Phase 2 (Match History updates) next (~6-8 hours)
- **Option B:** Implement Phase 1 + Phase 2 together (~8 hours total)

### Q3: Database Schema
Should I add an `updated_at` column to the `matches` table to track when matches are re-uploaded?

---

## Summary

**Critical Path:**
1. Fix damage_taken bug (5 min)
2. Update Match History page with dramatic analytics (6-8 hours)
3. Implement database upsert logic (30 min)

**Total Estimated Time:** 8-9 hours

**Next Steps:**
1. Confirm Phase 1 implementation
2. Plan Phase 2 detailed component designs
3. Execute implementation in order
