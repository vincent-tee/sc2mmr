# ML Model Findings & Optimization Results

## Current Model Configuration

**Model**: LogisticRegression (C=1.0)
**Accuracy**: 71.2% (5-fold cross-validated)
**Baseline**: 69.9% (higher MMR wins)
**Improvement**: +1.3%

## Why LogisticRegression over XGBoost

With only **153 matches**, simpler models outperform complex ones:

| Model | Accuracy | vs Baseline |
|-------|----------|-------------|
| **LogisticRegression (C=1.0)** | 71.2% | **+1.3%** |
| LogisticRegression (C=0.1) | 71.2% | +1.2% |
| GradientBoosting | 70.5% | +0.6% |
| RandomForest | 69.9% | -0.1% |
| XGBoost (d=3, n=50) | 69.2% | -0.8% |
| XGBoost (d=2, n=30) | 67.2% | -2.7% |

**Key insight**: XGBoost needs 1000+ samples to outperform linear models. With small datasets, its many parameters cause overfitting.

## Optimal Feature Set (6 features)

Features selected via F-score analysis and cross-validation:

| Feature | F-Score | Description |
|---------|---------|-------------|
| `experience_diff` | 32.87 | Total games played difference (STRONGEST) |
| `mmr_diff` | 22.93 | Core skill gap |
| `win_rate_diff` | 17.96 | Historical win rate difference |
| `combat_diff` | 7.59 | Historical combat performance (micro_composite) |
| `teamfight_diff` | 7.59 | Team fight participation rate |
| `aggression_diff` | 7.48 | Play style aggressiveness (inverted - less aggressive wins) |

## Features Tested But Not Included

These features showed high F-scores but didn't improve accuracy when added:

| Feature | F-Score | Why Not Included |
|---------|---------|------------------|
| `recency_mmr_diff` | 24.80 | Correlated with `mmr_diff`, adds variance |
| `form_diff` | 18.89 | Correlated with `win_rate_diff` |
| `recent_win_rate_diff` | 5.04 | Redundant with `win_rate_diff` |
| `early_game_diff` | 5.92 | Not enough signal with current data |

Adding more features increased variance without improving accuracy.

## Feature Combinations Tested

| Combination | Accuracy | Features |
|-------------|----------|----------|
| **Current 6** | **71.2%** | experience, mmr, win_rate, combat, teamfight, aggression |
| Add recency_mmr | 71.1% | 7 features |
| Top 5 F-score | 71.1% | experience, recency_mmr, mmr, form, win_rate |
| Simple 3 | 70.6% | experience, mmr, win_rate |

## In-Game Metrics Correlation Analysis

Team-level correlations with winning (from 153 matches, 1035 player records):

| Metric | Correlation | Strength |
|--------|-------------|----------|
| combat_diff | +0.535 | STRONG |
| teamfight_diff | +0.301 | STRONG |
| impact_diff | +0.197 | MEDIUM |
| efficiency_diff | +0.197 | MEDIUM |
| aggression_diff | -0.192 | MEDIUM (less aggressive = better) |

These correlations are from **actual match data**, but for prediction we use **historical averages** (since we predict before the match).

## Impact Score Calculation Fix (Dec 2024)

Fixed bug where `efficiency_score` and `overall_impact` could exceed 100:

**Problem**: `damage_ratio` could be infinite (dealt damage, received 0)

**Solution**: Cap `damage_ratio` at 10.0 before calculations:
- `efficiency_score`: Now properly 0-100
- `combat_score`: Now properly 0-100
- `overall_impact`: Now properly 0-100

## Recommendations for Future

1. **Collect more data**: At 500+ matches, revisit XGBoost and additional features
2. **Re-evaluate periodically**: Run feature selection every 100 new matches
3. **Monitor baseline**: If MMR baseline exceeds ML model, retrain is needed

## Technical Details

### Model Location
`backend/data/xgboost_model.pkl` (actually LogisticRegression despite filename)

### Feature Extraction
`backend/app/services/xgboost_predictor.py`:
- `FeatureExtractor.extract_team_features()` - aggregates player stats
- `FeatureExtractor.create_match_features()` - creates diff vector
- `FEATURE_NAMES` - canonical list of 6 features

### Training
```python
from app.services.xgboost_predictor import get_xgboost_predictor
predictor = get_xgboost_predictor()
result = predictor.train(db)
```

### Cross-Validation Test
```bash
cd backend && python3 -c "
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LogisticRegression
# ... (see full script in session history)
"
```

## Session History

- **Dec 27, 2024**: Comprehensive model comparison, feature selection, impact score fix
- Tested 8 model variants, 6 feature combinations
- Confirmed LogisticRegression optimal for current dataset size
