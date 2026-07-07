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

## 2026-07-06: Retrain + leak-free re-validation after data-integrity fixes

**Hypothesis:** The live `MLPredictor.train()` trainer has a known lookahead leak
(`sc2mmr-research-methodology` leak taxonomy item 1) — it builds features for past
matches using players' *current* Player-row aggregates, which include the outcome
of the match being predicted and everything since. Separately, today's session found
and fixed two data-integrity bugs affecting match outcomes: ~172 matches where the
winner couldn't be determined were silently defaulted to "team 2 wins" (now corrected
via resource-comparison per the parser's own fallback rule), and 15 duplicate matches
(same game, uploaded/recorded twice, one pair with contradictory winners) were
removed. Net: n went from 871 to 856 matches. Rebuilding features leak-free (in-memory
chronological rolling aggregates, Recipe 9 style) AND on corrected labels should move
the measured accuracy from the previously-reported numbers — predicted to make the
honest number LOWER than 71.2%/64.3%-era figures, since those were computed on both
leaky features and partly-mislabeled outcomes.

**Setup:** n=856 matches (post-dedup, post-winner-fix), read-only queries against
`backend/data/sc2mmr.db`. Baseline re-measured fresh (team-sum `mmr_before` variant,
`sc2mmr-proof-and-analysis-toolkit` Recipe 1). Model re-evaluated via a from-scratch
leak-free harness (Recipe 9: in-memory per-player rolling aggregates updated only
*after* each match) feeding the existing 12-feature LogisticRegression(C=1.0), 5-fold
CV (Recipe 2), LOPO given ~19 core players appear in most matches (Recipe 3), bootstrap
95% CI if the margin is thin (Recipe 4), McNemar exact test vs baseline on the same
match set (Recipe 10).

**Predicted:** baseline 63-66% (team-sum); leak-free model 60-65%, i.e. possibly AT OR
BELOW the freshly-measured baseline once lookahead is removed.

**Kill criterion:** if 5-fold CV improvement over the freshly-measured baseline is
< +1.0pp, OR the bootstrap 95% CI on the improvement includes zero, OR McNemar
p ≥ 0.05 — this does not count as "beats baseline" and the model is NOT adopted as
an accuracy claim; report honestly and leave the production model/baseline
relationship as a documented-open finding rather than shipping an unproven "improvement."

**Observed** (n=833 usable matches — 856 total minus 20 winner-less/one-sided,
3 true MMR ties excluded from decided-baseline counts; script:
`backend/scripts/revalidate_ml_predictor_leakfree.py`, read-only):

| Method | Result |
|---|---|
| Baseline, team-sum `mmr_before` | 550/830 = **66.3%** |
| Baseline, team-average `mmr_before` | 508/830 = 61.2% |
| LogisticRegression(C=1.0), 5-fold CV, leak-free features | **65.8% ± 1.7%** |
| Model shootout, same leak-free features (LogReg C=0.1, shallow GradientBoosting, shallow RandomForest) | 65.6–66.3%, all statistically indistinguishable |
| LOPO (18 core players, ≥30 appearances, 17 with enough held-out data) | mean delta **−0.7%**, positive for only **6/17** players |
| Bootstrap CI (1000 resamples, in-sample fit) | mean +0.4%, **95% CI [−1.9%, +2.6%]** (includes zero) |
| McNemar exact, honest out-of-fold model vs team-sum baseline | baseline-only-right=50, model-only-right=46, **p=0.76** |
| Out-of-fold model accuracy vs baseline | 65.8% vs 66.3%, **delta −0.5%** |

**Verdict: Refuted.** All three pre-registered kill criteria triggered: CV
improvement is −0.5pp (not ≥ +1.0pp), the bootstrap CI spans zero, and McNemar
p=0.76 is nowhere near significant. LOPO shows the model helps a minority
(6/17) of held-out players — consistent with noise, not a real signal. Once the
lookahead leak is removed and match outcomes are corrected, this 12-feature
LogisticRegression provides **no measurable edge over "the team with the
higher summed pre-match MMR wins."** The previously-reported 71.2%
(n=153, 2024) and the model's own self-reported `training_accuracy` (last
computed 2026-07-03, before today's corrections) were optimistic — the
mechanism is exactly the leak this project's own methodology flags: those
numbers used players' current-as-of-training-time aggregates (including each
match's own future) to featurize historical matches.

**Next:** Documented-dead as an accuracy claim at current n and feature set —
do not cite 71.2% (or any number from the live `MLPredictor.train()`/
`extract_team_features()`) as validated going forward; both are leaky.
Re-entry condition: revisit if (a) n grows substantially past 833, or (b) a
genuinely new feature survives Recipe 7 screening (F-score + CV-with-vs-without)
on leak-free data.

**Adoption (same day, after this finding was reported):** the leak is fixed in
production. `build_chronological_dataset()` (`backend/app/services/ml_predictor.py`)
replaces the leaky per-match `extract_team_features()` calls in both
`MLPredictor.train()` and `/adaptive/accuracy-comparison`
(`backend/app/api/adaptive.py`) with the in-memory chronological walk validated
above. `train()` now reports honest 5-fold CV accuracy (`cv_accuracy`) next to
the same-data baseline (`baseline_accuracy`) instead of a single leaky
train/test split, and fits the final deployed model on all data (CV to
evaluate, full fit to ship — standard practice). Retrained model confirmed
matching the validation script exactly: 65.8% CV vs 66.3% baseline, n=833.
Frontend (`frontend/src/pages/MLIntelligence.tsx`) updated to stop presenting
a naive `+delta% vs baseline` claim when the gap is within noise (<2pp
threshold — this dataset's 5-fold CV std is ~1.7pp) and a hardcoded, unvalidated
"18% more likely" / "Experience is the top predictor" claim (both fabricated —
not derived from any query; the actual retrained model's top feature is
`win_rate_diff`) was replaced with the real top feature, computed live, and
honest framing about not having a proven edge. `predict()` (used for live
upcoming-match prediction, not training) was NOT changed — using current
player state there is legitimate, since a real future match has no leak to
have.

## 2026-07-06: Feature/model search on the leak-free dataset (session continued)

**Hypothesis:** given 4 model classes already tied with the baseline on the
current 12 leak-free features, no untried candidate feature or model class
will move 5-fold CV accuracy by more than ~1pp — the ceiling here is
signal-limited (not enough predictive information in the available data), not
model-limited.

**Setup:** same n=833 leak-free dataset. Tested 6 additional per-player
rolling candidate features not in the current 12 (`apm`, `kill_death_ratio`,
`damage_ratio`, `spending_efficiency`, `workers_created`,
`army_net_efficiency` = army value killed / (killed+lost)), each added
individually to the base 12 and evaluated via CV-with-vs-without (Recipe 7 -
correlation/F-score alone is inadmissible, only incremental CV counts). Then
a 6-model shootout (LogisticRegression, SVC-RBF, GaussianNB, shallow
GradientBoosting/RandomForest/ExtraTrees) on the best augmented feature set.
Script: `backend/scripts/search_better_ml_features.py`, read-only.

**Predicted:** no candidate feature delta ≥ +1.0pp; no model class beats
LogisticRegression by a meaningful margin.

**Observed:**

| Candidate feature (added to base 12) | CV accuracy | Delta vs base (65.8%) |
|---|---|---|
| `+apm` | 66.3% | +0.5% |
| `+workers_created` | 66.3% | +0.5% |
| `+army_net_efficiency` | 65.9% | +0.1% |
| `+spending_efficiency` | 65.9% | +0.1% |
| `+kill_death_ratio` | 65.8% | +0.0% |
| `+damage_ratio` | 65.4% | −0.4% |

Best candidate (`apm`) bootstrap check: improved in-sample fit in only
**104/200 (52%)** resamples — a coin flip. Combining the top 2 candidates
together: still +0.5%, no additive benefit (redundant signal). Model shootout
on base+`apm`: LogisticRegression 66.3% remained best; SVC 65.7%, shallow
GradientBoosting 65.2%, shallow RandomForest 65.2%, ExtraTrees 60.9% (worse),
GaussianNB 57.4% (much worse).

**Verdict: Refuted**, cleanly, on both axes tested. No feature cleared even
half the pre-registered threshold, and the top candidate's bootstrap
confirmed it's noise, not signal. No model class beat plain LogisticRegression;
several (GaussianNB, ExtraTrees) were meaningfully worse. Matches this
project's established small-n lesson (`ml-model-findings.md` "Why
LogisticRegression over XGBoost" above) — it's not that a better model is
waiting to be found here, it's that at n=833 with these features, "higher
summed MMR wins" is already close to the ceiling of what's predictable.

**Next:** No adoption — nothing beat the baseline. Documented-dead for this
feature/model search. Re-entry condition: (a) n grows substantially, (b) a
feature outside the currently-tracked metric set is added to the parser
(e.g. build-order/timing data, synergy terms), or (c) someone wants to
challenge this specific result — the script is saved and re-runnable
(`backend/scripts/search_better_ml_features.py`).
