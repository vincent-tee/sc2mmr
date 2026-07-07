# SPEC: Unified MMR System (FINAL)

**Created:** 2025-12-29  
**Status:** Approved  
**Author:** AI Assistant + User

## Overview

Consolidate the SC2MMR rating system to use a single, data-driven MMR formula that incorporates:
1. **TrueSkill base rating** (mu - 3*sigma)
2. **Handicap correction** (rewards outperformance vs expected win rate)
3. **Combat contribution** (validated +2.5% prediction improvement)

---

## The Formula

```
Unified_MMR = Raw_TrueSkill + (outperformance * 3000) + (20 * avg_combat_score)
```

### Components

| Component | Formula | Purpose |
|-----------|---------|---------|
| **Raw TrueSkill** | `mu - 3 * sigma` | Conservative skill estimate from win/loss |
| **Handicap Correction** | `(actual_WR - expected_WR) * 3000` | Corrects for balancing bias |
| **Combat Bonus** | `20 * avg_combat_score` | Rewards in-game contribution |

### Expected Win Rate
```
expected_WR = 1 / (1 + 10^(-handicap/400))
handicap = (my_team_mmr - opponent_team_mmr) / my_team_size
```

---

## Validation Evidence

| Method | Improvement | Notes |
|--------|-------------|-------|
| Bootstrap (n=1000) | +2.2% | 68% samples positive |
| Grid Search | +2.6% | Optimal at 20 MMR/point |
| Leave-One-Player-Out | +2.5% | Consistent across 16 players |
| Flip Analysis | 4/4 correct | Combat never hurts |

**Correlation with HC-MMR:** 0.19 (low - captures independent signal)

---

## Database Changes

### New Column
```sql
ALTER TABLE players ADD COLUMN unified_mmr FLOAT;
```

### Columns to Keep
| Column | Purpose |
|--------|---------|
| `mu`, `sigma` | TrueSkill internals |
| `unified_mmr` | **THE** rating (new primary) |
| `handicap_corrected_mmr` | Intermediate calculation |
| `avg_combat_score` | Component of unified MMR |
| `avg_economic_score` | Leaderboard category only |
| `avg_efficiency_score` | Leaderboard category only |
| `avg_overall_impact` | Leaderboard category only |
| `outperformance_pct` | Display stat |
| `avg_team_handicap` | Display stat |

### Columns to Archive/Delete
| Column | Reason |
|--------|--------|
| `mmr` | Rename to `raw_trueskill_mmr` |
| `recency_weighted_mmr` | Unused, no predictive value |
| `hybrid_mmr` | Unused, superseded |
| `session_weighted_mmr` | Unused, superseded |
| `avg_first_damage_timing` | No predictive value |
| `avg_aggression_score` | No predictive value |

---

## Backend Changes

### Files to Modify

| File | Changes |
|------|---------|
| `app/services/handicap_mmr_service.py` | Add `calculate_unified_mmr()` method |
| `app/balancer.py` | Use `unified_mmr` for balancing |
| `app/api/leaderboard.py` | Consolidate endpoints |
| `app/api/teams.py` | Delete deprecated endpoints |
| `app/models.py` | Update Player model |

### Files to Delete
| File | Reason |
|------|--------|
| `app/rating_models.py` | No longer needed (was for model switching) |
| `app/services/adaptive_balancer.py` | Only used by deprecated endpoints |

### API Endpoints (Final)

#### Teams API (Keep 7)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/teams/balance` | POST | Primary balancing (uses unified_mmr) |
| `/teams/quick-balance` | POST | Single best result |
| `/teams/balance-with-ai` | POST | Include AI player |
| `/teams/balance-with-guests` | POST | Include guest players |
| `/teams/predict` | POST | Match prediction |
| `/teams/ai-difficulties` | GET | List AI levels |
| `/teams/balance-quality` | GET | Historical metrics |

#### Teams API (Delete 8)
- `/balance-with-impact` (deprecated)
- `/balance-with-model` (deprecated)
- `/balance-with-ml-metrics` (deprecated)
- `/balance-timing-adjusted` (no value added)
- `/balance-true-skill` (merged into `/balance`)
- `/compare-models` (deprecated)
- `/predict-ml` (merge into `/predict`)
- `/models` (no longer needed)

#### Leaderboard API (Keep 9)
| Category | Endpoint | Description |
|----------|----------|-------------|
| `mmr` | `/leaderboard/mmr` | Unified MMR (default) |
| `combat` | `/leaderboard/specialists?category=combat` | Combat score |
| `economic` | `/leaderboard/specialists?category=economic` | Economic score |
| `efficiency` | `/leaderboard/specialists?category=efficiency` | Efficiency score |
| `teamwork` | `/leaderboard/specialists?category=teamwork` | Team contribution |
| `winrate` | `/leaderboard/winrate` | Win percentage |
| `games` | `/leaderboard/games` | Games played |
| `duos` | `/leaderboard/duos` | Best partnerships |
| `winstreak` | `/leaderboard/winstreak` | Longest streak |

#### Leaderboard API (Delete 5)
- `/leaderboard/trueskill` (merged into mmr)
- `/leaderboard/raw_mmr` (internal only)
- `/leaderboard/tactical` (redundant)
- `/leaderboard/hybrid` (redundant)
- `/leaderboard/achievements` (no data)

---

## Frontend Changes

### Files to Modify

| File | Changes |
|------|---------|
| `src/types/leaderboard.ts` | Reduce to 9 categories |
| `src/pages/Leaderboard.tsx` | Update category list, MMR is default |
| `src/api/leaderboard.ts` | Remove deprecated calls |
| `src/api/teams.ts` | Remove deprecated calls, simplify |
| `src/components/PlayerCard.tsx` | Show single "MMR" value |
| `src/pages/PlayerDetail.tsx` | Show unified MMR + combat as secondary |

### Leaderboard Categories (Final)

```typescript
export const LEADERBOARD_CATEGORIES = [
  { key: 'mmr', name: 'MMR', icon: '🏆', description: 'Overall skill rating' },
  { key: 'combat', name: 'Combat', icon: '⚔️', description: 'Damage and kills' },
  { key: 'economic', name: 'Economic', icon: '💰', description: 'Resource management' },
  { key: 'efficiency', name: 'Efficiency', icon: '⚡', description: 'Damage per resource' },
  { key: 'teamwork', name: 'Teamwork', icon: '🤝', description: 'Team contribution' },
  { key: 'winrate', name: 'Win Rate', icon: '📈', description: 'Win percentage (min 20 games)' },
  { key: 'games', name: 'Games', icon: '🎮', description: 'Total matches played' },
  { key: 'duos', name: 'Duos', icon: '👥', description: 'Best partnerships' },
  { key: 'winstreak', name: 'Streaks', icon: '🔥', description: 'Longest win streak' },
];
```

---

## Implementation Order

### Phase 1: Database & Core Logic
1. Add `unified_mmr` column to players table
2. Update `handicap_mmr_service.py` with unified formula
3. Backfill `unified_mmr` for all players
4. Update `balancer.py` to use `unified_mmr`

### Phase 2: Backend Cleanup
1. Delete deprecated endpoints from `teams.py`
2. Consolidate leaderboard endpoints
3. Delete `rating_models.py`
4. Delete `adaptive_balancer.py`

### Phase 3: Frontend Cleanup
1. Update leaderboard types and categories
2. Update API client (remove deprecated calls)
3. Simplify player display components
4. Remove model selection UI

### Phase 4: Documentation & Archive
1. Create `REGRESSION_ANALYSIS.md`
2. Create `DEPRECATED_FEATURES.md`
3. Update `BALANCING_GUIDE.md`
4. Clean up inline comments

### Phase 5: Testing
1. Verify leaderboard displays correctly
2. Verify team balancing uses unified MMR
3. Verify predictions work
4. Run existing tests, fix any failures

---

## Migration Script

```python
# scripts/migrate_unified_mmr.py

def calculate_unified_mmr(player):
    """Calculate unified MMR from components."""
    hc_mmr = player.handicap_corrected_mmr or player.mmr
    combat = player.avg_combat_score or 25
    return hc_mmr + (20 * combat)

def migrate():
    for player in db.query(Player).all():
        player.unified_mmr = calculate_unified_mmr(player)
    db.commit()
```

---

## Expected Rankings After Migration

| Rank | Player | Old HC-MMR | Combat | New Unified |
|------|--------|------------|--------|-------------|
| 1 | Sirhc | 4109 | 28.8 | 4686 |
| 2 | Stephan | 3939 | 31.5 | 4568 |
| 3 | androidsine | 3427 | 31.1 | 4050 |
| 4 | shunmanFan | 3235 | 30.0 | 3834 |
| 5 | HahaLolo | 3069 | 33.2 | 3733 (+1) |
| 6 | ChrisO | 3140 | 28.2 | 3705 (-1) |
| 7 | Tingmore | 2566 | 38.3 | 3332 (+2) |

**Notable:** Tingmore (highest combat) gains 2 ranks. CapN (lowest combat) drops 3 ranks.

---

## Rollback Plan

If issues arise:
1. `unified_mmr` is a new column - old data untouched
2. Can revert to using `handicap_corrected_mmr` by changing one constant
3. Deprecated endpoints can be restored from git history

---

## Approval Checklist

- [x] Formula: `unified_mmr = hc_mmr + (20 * combat)`
- [x] Delete timing/economic/efficiency from MMR calculation
- [x] Keep combat/economic/efficiency as leaderboard categories
- [x] Reduce to 9 leaderboard categories
- [x] Reduce to 7 team endpoints
- [x] Archive regression findings
- [x] Hard delete deprecated code (not soft deprecate)
