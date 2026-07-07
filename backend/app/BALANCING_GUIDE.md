# SC2MMR Balancing System Guide

## Overview

The balancing system creates fair team compositions for StarCraft 2 matches.
All methods were regression-tested on 157 matches (Dec 29, 2024).

## Recommended Methods

### 0. Composite Objective Balance (NEW — Jul 2026)
**Endpoint:** `POST /teams/balance-composite`

Ranks splits by a composite objective instead of pure MMR-sum difference:
- Predicted win probability closest to 50% (TrueSkill, β-corrected; XGBoost
  re-rank of top candidates when the model is trained)
- TrueSkill match quality (uncertainty-aware)
- Penalties: within-team skill-spread mismatch, team-profile imbalance
  (combat/economic/efficiency/impact/aggression), one-sided synergy

Weights configurable via MLConfig key `composite_balance_weights`
(defaults in `app/balancer.py::DEFAULT_COMPOSITE_WEIGHTS`).

Backtest (Jul 3 2026, 614 even-team matches, pre-match rating snapshots):
the composite objective's top-quartile "best balanced" picks had a favorite
win rate of **0.497** vs **0.471** for pure MMR-diff. Also fixed win-prob
calibration by including TrueSkill β in both `TeamBalancer` and
`RatingSystem` (Brier 0.272 → 0.239, log loss 0.99 → 0.69).

**Calibration tracking:** every `/balance` and `/balance-composite` request
logs its top suggestions (`balance_predictions` table); replay uploads
resolve them against actual outcomes. Monitor per-method Brier/log-loss at
`GET /teams/balance-calibration`.

### 1. Timing-Adjusted Balance (RECOMMENDED)
**Endpoint:** `POST /teams/balance-timing-adjusted`
**Accuracy:** 77.7% overall, **72.7% on close games** (+9% improvement)

Uses the validated formula:
```python
timing_adjusted_mmr = mmr + (300 - avg_first_damage_timing) / 60 * 100
# +100 MMR per minute faster than 5-min baseline
```

This accounts for playstyle - aggressive players (early damage) get a bonus
that balances against macro players (late damage).

### 2. Basic TrueSkill Balance
**Endpoint:** `POST /teams/balance`
**Accuracy:** 76.4%

Simple and reliable. Uses TrueSkill match quality to find optimal splits.

### 3. Quick Balance
**Endpoint:** `POST /teams/quick-balance`

Returns the single best team composition (uses basic TrueSkill).

## Monitoring Balance Quality

**Endpoint:** `GET /teams/balance-quality`

Returns metrics on historical balance quality:
- Average MMR difference between teams
- % of matches within 100/200/300 MMR
- Prediction accuracy
- Closest and most lopsided matches

Use this to track if the balancer is working well over time.

## Deprecated/Legacy Methods

These endpoints still work but are not recommended:

- `/teams/balance-with-ml-metrics` - Complex, no real accuracy benefit
- `/teams/balance-with-impact` - Replaced by timing-adjusted
- `/teams/balance-with-model` - Too many options, confusing UX
- `/teams/compare-models` - Developer debugging tool

## Player Ratings

The system tracks several rating types:

| Rating | Description | Use Case |
|--------|-------------|----------|
| `mmr` | Conservative TrueSkill (mu - 3*sigma) | Default ranking |
| `timing_adjusted_mmr` | MMR + playstyle bonus | Balancing |
| `recency_weighted_mmr` | Recent performance weighted | Trend analysis |
| `session_weighted_mmr` | Same-session performance | Session analysis |

## Extensibility Points

For future ML improvements:

1. **`app/balancer.py`** - Core balancing logic
   - `PlayerInfo.from_player()` - Add new player metrics here
   - `generate_team_suggestions()` - Modify scoring/ranking here

2. **`app/services/adaptive_balancer.py`** - ML metrics framework
   - `calculate_ml_rating()` - Add new rating formulas
   - `SynergyCalculator` - Team chemistry calculations

3. **`app/services/component_accuracy_tracker.py`** - Accuracy tracking
   - `record_prediction()` - Track new component accuracy
   - `get_optimal_weights()` - Auto-tune weights

## Validated Findings (Dec 29, 2024)

1. **First Damage Timing** correlates with outcomes (r=0.503)
2. **Teamfight Damage Ratio** also correlates (r=0.692)
3. **Close game prediction** improved 63.6% → 72.7% with timing adjustment
4. **shunmanFan** legitimately #1 (42-19 H2H vs Stephan, 89% clutch wins)
