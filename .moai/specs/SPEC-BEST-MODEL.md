# SC2 MMR - Best Model Specification

## Summary

Based on analysis of 149 matches, **Recency-Weighted MMR** is the most accurate predictor at **74.5%**.

---

## Current Metrics Available (Already Extracted)

### From `advanced_parser.py` → `PlayerMetrics`:
| Category | Metrics |
|----------|---------|
| **Economic** | `minerals_collected`, `vespene_collected`, `workers_created`, `resources_spent` |
| **Army** | `units_trained`, `units_killed`, `army_value_built`, `army_value_lost` |
| **Combat** | `damage_dealt`, `damage_taken`, `damage_ratio` |
| **Timing** | `first_expansion_timing`, `first_damage_timing`, `early/mid/late_game_damage` |
| **Team Fight** | `team_fight_participation`, `team_fight_damage`, `team_fight_damage_ratio` |
| **Derived** | `economic_score`, `combat_score`, `efficiency_score`, `overall_impact` |

### From `models.py` → `Player` (Aggregated):
- `avg_economic_score`, `avg_combat_score`, `avg_efficiency_score`, `avg_overall_impact`
- `recency_weighted_mmr` ✅ (already implemented)
- `hybrid_mmr` (TrueSkill + performance)

---

## Problem Identified

**Impact metrics are NOT recency-weighted**. When combined with Recency MMR, accuracy drops because old performance data dilutes recent form.

---

## Recommended Action

### Option 1: Stick with Recency MMR Only (Simplest)
- **Use**: `recency_weighted_mmr` for balancing and leaderboards
- **Accuracy**: 74.5%
- **Effort**: Minimal (just update leaderboard to use recency)

### Option 2: Add Recency-Weighted Impact (Future)
Add to `Player` model:
```python
recency_weighted_combat_score: float
recency_weighted_economic_score: float
recency_weighted_overall_impact: float
```

Apply same 60-day half-life decay used for recency MMR.

---

## Files to Update for Option 1

| File | Change |
|------|--------|
| `app/api/leaderboard.py` | Use `recency_weighted_mmr` instead of `hybrid_mmr` |
| `app/api/teams.py` | Consider recency MMR in balancing (optional) |
| `config/settings` | Add flag: `use_recency_for_balancing = True` |

---

## Metrics Comparison

| Model | Accuracy | Notes |
|-------|----------|-------|
| **Recency MMR** | **74.5%** | Best - accounts for current form |
| Standard MMR | 71.1% | Slow to adapt |
| Hybrid MMR | 71.1% | Impact not recency-weighted |
| Recency + Current Impact | 57.7% | Old impact hurts accuracy |
