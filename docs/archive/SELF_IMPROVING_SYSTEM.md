# Self-Improving MMR System

## 🧠 Overview

This system creates a **"living model"** that continuously improves itself - not just updating weights, but discovering what new features to extract from replays.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    SELF-IMPROVING LOOP                        │
└──────────────────────────────────────────────────────────────┘

1. MATCH HAPPENS
   ↓
2. FEATURE EXTRACTION (Plugin System)
   ├─ Current Features (combat, economy, team contribution)
   ├─ Experimental Features (early aggression, map control)
   └─ Suggested Features (AI-proposed)
   ↓
3. PREDICTION
   ├─ Model A (Active): Makes prediction
   ├─ Model B (Experimental): Makes prediction
   └─ Both predictions logged
   ↓
4. BLENDED MMR UPDATE
   ├─ TrueSkill (85%): Baseline rating change
   ├─ Adaptive Model (15%): Context adjustment
   └─ Final MMR = Blended result
   ↓
5. OUTCOME OBSERVATION
   ├─ Actual result known
   ├─ Prediction errors calculated
   └─ Triggers learning pipeline
   ↓
6. LEARNING PIPELINE
   ├─ Update model weights (gradient descent)
   ├─ Analyze feature importance
   ├─ Detect error patterns
   ├─ Suggest new features
   └─ A/B test new model
   ↓
7. FEATURE DISCOVERY (If patterns found)
   ├─ High upset rate → Suggest "early_aggression" feature
   ├─ Map-specific errors → Suggest "map_control" feature
   ├─ Team composition errors → Suggest "race_synergy" feature
   └─ Generate extraction pseudocode
   ↓
8. HUMAN REVIEW & IMPLEMENTATION
   ├─ Review suggested features
   ├─ Implement extraction logic in parser
   └─ Add to experimental feature set
   ↓
9. A/B TESTING
   ├─ 80% traffic → Model A (stable)
   ├─ 20% traffic → Model B (with new feature)
   └─ Monitor performance
   ↓
10. PROMOTION (If Model B wins)
    ├─ Model B becomes active
    ├─ Model A archived
    └─ Cycle continues...
```

## Components

### 1. Blended Rating System (`blended_rating.py`)

**Purpose:** Combine TrueSkill's stability with Adaptive Model's context-awareness.

**How it works:**
```python
# Example: Underdog victory
TrueSkill says: +25 MMR (standard win)
Adaptive Model sees: Only 30% predicted to win (underdog!)
Adjustment: 1.2x multiplier (impressive upset)
Final MMR: +30 MMR

# Example: Expected win
TrueSkill says: +25 MMR (standard win)
Adaptive Model sees: 75% predicted to win (heavily favored)
Adjustment: 0.9x multiplier (expected outcome)
Final MMR: +22 MMR
```

**Configuration:**
```python
BlendConfig(
    trueskill_weight=0.85,  # 85% TrueSkill
    adaptive_weight=0.15,   # 15% Adaptive
    enabled=False,          # Start disabled
    log_only_mode=True      # Monitor first, apply later
)
```

### 2. Online Learning Pipeline (`online_learning.py`)

**Purpose:** Continuously improve the model from new data.

**Features:**
- **Automatic retraining** every N matches
- **Weight optimization** using gradient descent
- **Feature discovery** from prediction errors
- **Model versioning** for safe experimentation

**Example Learning Cycle:**
```python
# Every 50 matches
engine = OnlineLearningEngine(db)

# 1. Match outcome recorded
engine.record_outcome(match_id=123, team1_won=True)

# 2. System checks: Should we retrain?
# - 50+ new matches since last training? ✓
# - Enough total data (100+)? ✓
# - Triggers: retrain_model()

# 3. Retraining
# - Get recent 500 matches
# - Optimize weights using Nelder-Mead
# - Create new model version (v20250114_143022)
# - Mark as "experimental"

# 4. Feature Discovery
# - Analyze high-error predictions
# - Find patterns (e.g., many upsets)
# - Suggest new features:
#   * "early_game_aggression"
#   * "map_control_percentage"
#   * "composition_synergy"
# - Generate extraction pseudocode

# 5. A/B Testing
# - 80% predictions use Model A (stable)
# - 20% predictions use Model B (experimental)
# - Track accuracy of both

# 6. Promotion (if Model B better)
# - Promote Model B to active
# - Archive Model A
```

### 3. Feature Discovery System

**Purpose:** AI suggests what new features to extract from replays.

**How it discovers features:**

#### Pattern 1: High Upset Rate
```
Observation: 40% of prediction errors are upsets
Hypothesis: Missing early-game dynamics
Suggestion: "early_game_aggression"
Extraction Logic:
  early_units = count_units(replay, time=0-300s)
  early_attacks = count_attacks(replay, time=0-300s)
  score = (early_units * 0.3 + early_attacks * 0.7)
```

#### Pattern 2: Map-Specific Errors
```
Observation: Errors concentrated on specific maps
Hypothesis: Map control important
Suggestion: "map_control_percentage"
Extraction Logic:
  control_timeline = extract_map_control(replay)
  avg_control = mean(control_timeline)
```

#### Pattern 3: Composition Errors
```
Observation: Certain race combos have unexpected outcomes
Hypothesis: Team synergies matter
Suggestion: "composition_synergy"
Extraction Logic:
  synergy_matrix = {('Terran', 'Protoss'): 1.2, ...}
  score = lookup(team_races, synergy_matrix)
```

### 4. Database Schema

New tables for self-improvement:

```sql
-- Track model versions
model_versions
  - id
  - version_name (e.g., "v20250114_143022")
  - created_at
  - weights_json
  - features_used (JSON array)
  - is_active (current production model)
  - is_experimental
  - total_predictions
  - correct_predictions
  - avg_prediction_error

-- Log predictions for later evaluation
prediction_logs
  - id
  - match_id
  - model_version
  - predicted_team1_win_prob
  - predicted_team2_win_prob
  - actual_team1_won (NULL until match completes)
  - features_json (features used)
  - prediction_error (calculated after match)
  - was_upset

-- Track which features matter
feature_importance
  - id
  - feature_name
  - model_version
  - correlation_with_outcome
  - information_gain
  - sample_size

-- AI-suggested new features
feature_suggestions
  - id
  - feature_name (e.g., "early_aggression")
  - feature_description
  - extraction_logic (pseudocode)
  - reasoning (why suggested)
  - correlation_hypothesis
  - status (pending/implemented/rejected/testing)
  - test_results
```

## Usage

### Phase 1: Deploy in Log-Only Mode

```python
# In your configuration
BLENDED_RATING_CONFIG = BlendConfig(
    enabled=True,
    log_only_mode=True,  # Don't change MMR yet
    trueskill_weight=0.85,
    adaptive_weight=0.15
)

# In rating update code
blended_system = BlendedRatingSystem(BLENDED_RATING_CONFIG)
results = blended_system.update_ratings_from_match_blended(...)

# Monitor logs
# "LOG-ONLY] MMR Adjustment: TrueSkill=+25.0 → Blended=+30.0 (Adaptive=1.20x, Pred=30.0%, Upset=True)"
```

### Phase 2: Enable Online Learning

```python
# After match processing
from app.online_learning import OnlineLearningEngine

engine = OnlineLearningEngine(db)

# Log the prediction
engine.log_prediction(
    match_id=match.id,
    model_version="v1.0",
    team1_win_prob=0.65,
    team2_win_prob=0.35,
    features={
        "combat_score": 75.2,
        "economic_score": 68.9,
        # ...
    }
)

# Record outcome (after match finishes)
engine.record_outcome(
    match_id=match.id,
    team1_won=True
)

# System automatically:
# - Calculates prediction error
# - Updates feature importance
# - Retrains every 50 matches
# - Suggests new features when patterns found
```

### Phase 3: Review Feature Suggestions

```python
# Check suggested features
suggestions = db.query(FeatureSuggestion).filter(
    FeatureSuggestion.status == "pending"
).all()

for suggestion in suggestions:
    print(f"Feature: {suggestion.feature_name}")
    print(f"Reason: {suggestion.reasoning}")
    print(f"Extraction:\n{suggestion.extraction_logic}")
    print(f"Expected correlation: {suggestion.correlation_hypothesis}")

    # If it makes sense, implement it!
    # Then mark as "implemented"
    suggestion.status = "implemented"
```

### Phase 4: Implement New Features

```python
# In your parser or feature extraction
from app.online_learning import FeatureExtractor

extractor = FeatureExtractor()

# Register existing features
extractor.register_extractor("combat_score", extract_combat_score)
extractor.register_extractor("economic_score", extract_economic_score)

# Register new AI-suggested feature!
def extract_early_aggression(replay_data, match_data):
    # Implement the suggested logic
    early_units = count_units_created(replay_data, time_range=(0, 300))
    early_attacks = count_attack_events(replay_data, time_range=(0, 300))
    return (early_units * 0.3 + early_attacks * 0.7) / match_data.duration

extractor.register_extractor("early_aggression", extract_early_aggression)

# Extract all features
features = extractor.extract_all(replay_data, match_data)
```

### Phase 5: A/B Test & Promote

```python
# Check experimental model performance
monitor = BlendedRatingMonitor(db)
analysis = monitor.analyze_impact(days=30)

print(f"Blended accuracy: {analysis['blended_accuracy']:.1%}")
print(f"TrueSkill accuracy: {analysis['trueskill_accuracy']:.1%}")
print(f"Improvement: {analysis['improvement']:.1%}")

# If blended is better
should_enable, reason = monitor.should_enable_blending()
if should_enable:
    print(f"✓ Enabling blending: {reason}")
    # Update config to apply changes
    BLENDED_RATING_CONFIG.log_only_mode = False
else:
    print(f"✗ Keeping TrueSkill only: {reason}")
```

## Benefits

### 1. Self-Improving
- Model gets better over time
- Learns what matters from actual match outcomes
- No manual tuning needed

### 2. Context-Aware MMR
- Accounts for upsets (underdog wins get more MMR)
- Adjusts for expected wins (favorite wins get less MMR)
- More accurate than pure TrueSkill

### 3. Feature Discovery
- System tells you what's missing
- Generates extraction pseudocode
- Prioritizes by expected impact

### 4. Safe Experimentation
- Log-only mode for monitoring
- A/B testing for validation
- Rollback if accuracy drops
- Model versioning

## Example Outcomes

### Before (Pure TrueSkill)
```
Match 1: Team A (1500 MMR) beats Team B (1200 MMR)
  - Team A: +18 MMR
  - Team B: -18 MMR
  - Issue: Team A was heavily favored (80% predicted), so +18 seems high

Match 2: Team C (1200 MMR) beats Team D (1500 MMR)
  - Team C: +32 MMR
  - Team D: -32 MMR
  - Issue: Team C pulled off huge upset, but only gets standard boost
```

### After (Blended System)
```
Match 1: Team A (1500 MMR) beats Team B (1200 MMR)
  - Adaptive Model: 80% predicted (heavy favorite)
  - Adjustment: 0.85x (reduce expected win)
  - Team A: +15 MMR (was +18)
  - Team B: -15 MMR (was -18)
  - ✓ More fair - expected outcome

Match 2: Team C (1200 MMR) beats Team D (1500 MMR)
  - Adaptive Model: 20% predicted (huge underdog)
  - Adjustment: 1.3x (reward impressive upset)
  - Team C: +42 MMR (was +32)
  - Team D: -42 MMR (was -32)
  - ✓ More fair - unexpected outcome rewarded
```

## Monitoring

Check logs regularly:

```bash
# See blended adjustments
grep "Blended" app.log | tail -20

# Check for upsets
grep "Upset=True" app.log | wc -l

# See feature suggestions
grep "feature suggestions" app.log
```

Query database:

```sql
-- Check model performance
SELECT
    model_version,
    COUNT(*) as predictions,
    AVG(prediction_error) as avg_error,
    SUM(CASE WHEN was_upset THEN 1 ELSE 0 END) as upsets
FROM prediction_logs
GROUP BY model_version
ORDER BY created_at DESC;

-- See feature importance
SELECT
    feature_name,
    correlation_with_outcome,
    sample_size
FROM feature_importance
ORDER BY ABS(correlation_with_outcome) DESC;

-- Pending feature suggestions
SELECT
    feature_name,
    reasoning,
    correlation_hypothesis
FROM feature_suggestions
WHERE status = 'pending'
ORDER BY correlation_hypothesis DESC;
```

## Next Steps

1. **Add database migrations** for new tables
2. **Integrate blended rating** into existing `rating_system.py`
3. **Deploy in log-only mode** for 100 matches
4. **Review logs** and adjust weights if needed
5. **Enable blending** if improvement shown
6. **Implement suggested features** from AI
7. **Repeat cycle** - continuous improvement!

## Safety Guardrails

✓ **Log-only mode** - Monitor without changing MMR
✓ **Max adjustment limits** - Can't change MMR by more than 30%
✓ **Minimum samples** - Won't retrain until 100+ matches
✓ **Validation split** - Tests on held-out data
✓ **Rollback capability** - Can revert to old model
✓ **Alert on anomalies** - Warns on large adjustments
✓ **Human review** - Feature suggestions reviewed before implementation

---

**The system is now alive! 🚀**

It will continuously:
- Learn from outcomes
- Improve predictions
- Suggest new features
- Get smarter over time

All while maintaining TrueSkill's proven stability as the foundation.
