# SPEC-ML-001 Handover Document

**Date**: 2025-12-06
**Status**: Phase 1-3 Complete, Ready for Testing

---

## What Was Built

### ML-Enhanced Hybrid MMR System

A performance-based rating system that adjusts MMR gains/losses based on in-game metrics, not just win/loss.

**Formula:**
```
hybrid_mmr_change = trueskill_change × (1 + PIM)
```

Where PIM (Performance Impact Modifier) ranges from -0.5 to +0.5 based on:
- **Combat (40%)**: damage_ratio, army_value_ratio, combat_score
- **Economic (25%)**: spending_efficiency, economic_score, resource_advantage
- **Team (25%)**: team_fight_participation, team_fight_damage_ratio, overall_impact
- **Efficiency (10%)**: efficiency_score

---

## Files Created/Modified

### New Files
| File | Purpose |
|------|---------|
| `backend/app/services/__init__.py` | Services package |
| `backend/app/services/pi_calculator.py` | Core PIM calculation engine |
| `backend/tests/test_pi_calculator.py` | 26 unit tests |
| `backend/migrations/003_add_performance_features.sql` | SQL schema |
| `backend/migrations/run_003_migration.py` | Migration runner |
| `.moai/specs/SPEC-ML-001/spec.md` | Full specification |
| `.moai/specs/SPEC-ML-001/plan.md` | Implementation plan |
| `.moai/specs/SPEC-ML-001/acceptance.md` | Acceptance criteria |

### Modified Files
| File | Changes |
|------|---------|
| `backend/app/models.py` | Added `PerformanceFeatures` model, `hybrid_mmr`/`avg_pim` to Player |
| `backend/app/config.py` | Added PIM weights, bounds, enable toggle |
| `backend/app/rating_system.py` | Integrated PICalculator after match processing |
| `backend/app/api/players.py` | Added `hybrid_mmr`/`avg_pim` to API responses |

---

## Test Results

```
============================== 44 passed ==============================
- 18 existing backend tests: ✅ All passing
- 26 new PICalculator tests: ✅ All passing
```

---

## Database Migration

**Already Ran Successfully:**
```
✓ Added hybrid_mmr column to players
✓ Added avg_pim column to players
✓ Created performance_features table
✓ Initialized hybrid_mmr for 19 existing players
```

---

## Configuration

In `.env` or `backend/app/config.py`:
```python
HYBRID_MMR_ENABLED=true  # Toggle system on/off
PIM_MIN=-0.5             # Minimum modifier (50% less gain)
PIM_MAX=0.5              # Maximum modifier (50% more gain)
```

Weight configuration (all in config.py, sum to 1.0):
```python
pim_weight_damage_ratio: 0.15
pim_weight_army_value_ratio: 0.15
pim_weight_combat_score: 0.10
# ... etc
```

---

## What Works Now

1. **New matches** automatically calculate PIM and update `hybrid_mmr`
2. **API responses** include `hybrid_mmr` and `avg_pim` for all players
3. **PerformanceFeatures** table stores all normalized metrics for future ML training

---

## Remaining Work

### Phase 4: Frontend (COMPLETE)
- ✅ `PlayerCard.jsx`: Shows hybrid_mmr with tooltip showing both values
- ✅ `Players.jsx`: Leaderboard uses hybrid_mmr with performance indicator (▲/▼)
- Tooltip shows: "TrueSkill: X | Hybrid: Y | Avg PIM: +Z%"

### Phase 5: ML Model Training (Future)
- After 500+ matches with features, analyze correlations
- Train regression model to optimize weights
- A/B test ML vs rule-based

---

## Quick Verification Commands

```bash
# Run all tests
cd backend && pytest tests/ -v

# Check a player's hybrid_mmr
sqlite3 data/sc2mmr.db "SELECT name, mmr, hybrid_mmr, avg_pim FROM players LIMIT 5"

# Check performance features (will be empty until new matches processed)
sqlite3 data/sc2mmr.db "SELECT COUNT(*) FROM performance_features"
```

---

## Architecture Summary

```
Replay Upload
    ↓
TrueSkill calculates base MMR change
    ↓
PICalculator.calculate_match_averages()
    ↓
PICalculator.calculate_pim() for each player
    ↓
PICalculator.apply_pim_to_mmr_change()
    ↓
Store PerformanceFeatures + Update Player.hybrid_mmr
```

---

**All systems operational. Upload a new replay to see hybrid MMR in action!**
