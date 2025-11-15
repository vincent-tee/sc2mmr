# Setup Guide - Self-Improving MMR System

## Quick Start (162 Replays - Perfect to Begin!)

You have **162 replays** - that's enough to start the self-improving system in **monitoring mode**!

---

## Phase 1: Enable Log-Only Blending (Week 1)

### What This Does
- System monitors what MMR adjustments **would** be made
- No actual MMR changes yet
- Safe to observe and validate
- **Needs: 100+ replays** ✅ (You have 162!)

### Steps

#### 1. Add Database Tables

Run this migration to add the new tables:

```bash
cd backend
python3 - <<'EOF'
from app.database import engine
from app.online_learning import ModelVersion, PredictionLog, FeatureImportance, FeatureSuggestion

# Create tables
from app.models import Base
ModelVersion.__table__.create(bind=engine, checkfirst=True)
PredictionLog.__table__.create(bind=engine, checkfirst=True)
FeatureImportance.__table__.create(bind=engine, checkfirst=True)
FeatureSuggestion.__table__.create(bind=engine, checkfirst=True)

print("✓ Tables created successfully!")
EOF
```

#### 2. Initialize First Model Version

```bash
python3 - <<'EOF'
from app.database import SessionLocal
from app.online_learning import ModelVersion
from datetime import datetime
import json

db = SessionLocal()

# Create initial model version
initial_model = ModelVersion(
    version_name="v1.0_baseline",
    created_at=datetime.utcnow(),
    weights_json=json.dumps({
        'combat_weight': 0.40,
        'economic_weight': 0.20,
        'team_contribution_weight': 0.30,
        'efficiency_weight': 0.10
    }),
    features_used=['combat_score', 'economic_score', 'team_contribution', 'efficiency_score'],
    is_active=True,
    is_experimental=False,
    notes="Baseline model with default weights"
)

db.add(initial_model)
db.commit()
print(f"✓ Created baseline model: {initial_model.version_name}")
db.close()
EOF
```

#### 3. Enable Blending in Log-Only Mode

Add to `backend/app/config.py` (or create it):

```python
# backend/app/config.py
from app.blended_rating import BlendConfig

# Blended Rating Configuration
BLENDED_RATING_CONFIG = BlendConfig(
    enabled=True,           # Enable the blended system
    log_only_mode=True,     # DON'T apply changes yet, just log
    trueskill_weight=0.85,  # 85% TrueSkill
    adaptive_weight=0.15,   # 15% Adaptive adjustment
    max_adjustment_percent=0.3,  # Max 30% adjustment
    alert_on_large_adjustment=0.25  # Alert if >25% change
)
```

#### 4. Integrate into Rating Updates

Modify `backend/app/rating_system.py` around line 300 (after TrueSkill calculation):

```python
# In update_ratings_from_match, after calculating new ratings...

# Import at top
from .blended_rating import BlendedRatingSystem
from .config import BLENDED_RATING_CONFIG

# After line ~308 (after new_ratings calculated)
blended_system = BlendedRatingSystem(BLENDED_RATING_CONFIG)

# Apply blending (in log-only mode, this just logs)
team1_blended, team2_blended = blended_system.update_ratings_from_match_blended(
    db=db,
    match=match,
    team_1_players=team_1_db,
    team_2_players=team_2_db,
    team_1_ratings=team_1_ratings,
    team_2_ratings=team_2_ratings,
    new_team_1_ratings=new_team_1_ratings,
    new_team_2_ratings=new_team_2_ratings,
    team_1_won=team_1_won
)

# If NOT in log-only mode, use blended ratings
if not BLENDED_RATING_CONFIG.log_only_mode:
    # Update with blended values
    for i, (mu, sigma) in enumerate(team1_blended):
        new_team_1_ratings[i] = trueskill.Rating(mu=mu, sigma=sigma)
    for i, (mu, sigma) in enumerate(team2_blended):
        new_team_2_ratings[i] = trueskill.Rating(mu=mu, sigma=sigma)
```

#### 5. Upload Some Replays & Check Logs

```bash
# Upload a few replays
curl -F "files=@replay1.SC2Replay" http://localhost:8000/api/replays/upload

# Check logs for blending activity
tail -f backend/logs/app.log | grep "Blended"
```

You should see:
```
[LOG-ONLY] MMR Adjustment: TrueSkill=+25.0 → Blended=+30.0 (Adaptive=1.20x, Pred=30.0%, Upset=True)
[LOG-ONLY] MMR Adjustment: TrueSkill=+25.0 → Blended=+22.0 (Adaptive=0.88x, Pred=75.0%, Upset=False)
```

---

## Phase 2: Weight Optimization (Week 1-2)

### What This Does
- System analyzes your 162 replays
- Finds optimal weights for combat/economy/team/efficiency
- Suggests improvements
- **Needs: 100+ replays** ✅

### Steps

#### 1. Check Current Model Performance

```bash
curl http://localhost:8000/api/adaptive/model-performance | jq
```

Output:
```json
{
  "win_prediction_accuracy": 0.67,
  "sample_size": 162,
  "confidence_score": 0.72,
  "current_weights": {
    "combat": 0.40,
    "economic": 0.20,
    "team_contribution": 0.30,
    "efficiency": 0.10
  }
}
```

#### 2. Get Weight Suggestions

```bash
curl http://localhost:8000/api/adaptive/suggest-weights | jq
```

Output:
```json
{
  "suggestion": "update_recommended",
  "reason": "Found weights that improve prediction by 5.2%",
  "confidence": 0.78,
  "sample_size": 162,
  "current_weights": {...},
  "suggested_weights": {
    "combat": 0.45,      // +5% (combat matters more!)
    "economic": 0.18,    // -2%
    "team_contribution": 0.28,  // -2%
    "efficiency": 0.09   // -1%
  },
  "performance_improvement": 0.052
}
```

#### 3. Apply Suggested Weights (Optional)

If you want to use the suggested weights:

```python
# Update backend/app/advanced_parser.py
PERFORMANCE_WEIGHTS = {
    'combat': 0.45,        # Changed from 0.40
    'economic': 0.18,      # Changed from 0.20
    'team_contribution': 0.28,  # Changed from 0.30
    'efficiency': 0.09     # Changed from 0.10
}

# Restart backend
```

---

## Phase 3: Online Learning (Week 2-3)

### What This Does
- Automatically logs predictions
- Tracks accuracy over time
- Retrains every 50 matches
- **Needs: 150+ replays** ✅

### Steps

#### 1. Enable Online Learning in Upload

Modify `backend/app/api/replays.py` in the upload endpoint (after processing match):

```python
# Add imports at top
from app.online_learning import OnlineLearningEngine

# After match is processed and ratings updated (around line 150)
# Log prediction for online learning
try:
    learning_engine = OnlineLearningEngine(db)

    # Get current model version
    from app.online_learning import ModelVersion
    active_model = db.query(ModelVersion).filter(
        ModelVersion.is_active == True
    ).first()

    if active_model and match.predicted_team1_win_prob:
        # Log the prediction
        learning_engine.log_prediction(
            match_id=match.id,
            model_version=active_model.version_name,
            team1_win_prob=match.predicted_team1_win_prob,
            team2_win_prob=match.predicted_team2_win_prob,
            features={
                # Add feature values if available
                "trueskill_prediction": match.predicted_team1_win_prob
            }
        )

        # Record outcome (we know it immediately after processing)
        learning_engine.record_outcome(
            match_id=match.id,
            team1_won=team_1_players[0].won if team_1_players else False
        )
except Exception as e:
    logger.warning(f"Online learning failed: {e}")
    # Don't fail upload if learning fails
```

#### 2. Monitor Learning Progress

```bash
# Check model versions
curl http://localhost:8000/api/adaptive/model-versions | jq

# Check prediction logs
curl http://localhost:8000/api/adaptive/prediction-logs | jq

# Check feature suggestions
curl http://localhost:8000/api/adaptive/feature-suggestions | jq
```

---

## Phase 4: Enable Blending (Week 3-4)

### What This Does
- Actually applies MMR adjustments
- Uses blended TrueSkill + Adaptive
- **Needs: 200+ replays** (You'll need ~40 more)

### When to Enable
Check if blending improves accuracy:

```python
from app.blended_rating import BlendedRatingMonitor

monitor = BlendedRatingMonitor(db)
analysis = monitor.analyze_impact(days=30)

print(f"Current accuracy: {analysis['trueskill_accuracy']:.1%}")
print(f"Blended accuracy: {analysis['blended_accuracy']:.1%}")
print(f"Improvement: {analysis['improvement']:.1%}")

if analysis['improvement'] > 0.03:  # 3% better
    print("✓ Safe to enable blending!")
else:
    print("✗ Keep in log-only mode")
```

### Steps to Enable

If improvement is good (>3%):

```python
# backend/app/config.py
BLENDED_RATING_CONFIG = BlendConfig(
    enabled=True,
    log_only_mode=False,  # ← Changed from True!
    trueskill_weight=0.85,
    adaptive_weight=0.15,
    max_adjustment_percent=0.3
)

# Restart backend
```

Now blending is LIVE! Upsets get more MMR, expected wins get less.

---

## Phase 5: Feature Discovery (Later - 300+ Replays)

### What This Does
- AI suggests new features to extract
- Analyzes prediction errors for patterns
- **Needs: 300+ replays** (You'll need 138 more)

### How It Works

After 300+ replays, the system will:

1. **Analyze Errors**
   ```
   Found 45 high-error predictions
   Pattern: 60% are upsets (underdog wins)
   Hypothesis: Missing early game dynamics
   ```

2. **Suggest Feature**
   ```
   Feature: "early_game_aggression"
   Reasoning: "Underdogs may win through early pressure"
   Extraction Logic:
     early_units = count_units(replay, time=0-300s)
     score = (early_units * 0.3 + early_attacks * 0.7)
   Expected Correlation: 0.25
   ```

3. **You Implement**
   ```python
   # Add to your parser
   def extract_early_aggression(replay_data):
       # Your sc2reader code
       return aggression_score

   # Register it
   extractor.register_extractor("early_aggression", extract_early_aggression)
   ```

4. **System Tests**
   - Feature included in Model B (experimental)
   - 20% of predictions use Model B
   - 80% use Model A (stable)
   - Compare accuracy

5. **Auto-Promote if Better**
   ```python
   # If Model B accuracy > Model A accuracy + 0.05
   engine.promote_experimental_model("v20250114_143022")
   # Model B becomes standard!
   ```

---

## Monitoring Dashboard

### View in Frontend

Visit `http://localhost:3000/adaptive-model` to see:

- ✅ Current model performance
- ✅ Weight optimization suggestions
- ✅ Blending statistics (coming soon)
- ✅ Feature importance charts (coming soon)
- ✅ AI-suggested features (coming soon)
- ✅ Model version history (coming soon)

### Query Database Directly

```sql
-- Check model performance
SELECT
    model_version,
    COUNT(*) as predictions,
    AVG(prediction_error) as avg_error,
    SUM(CASE WHEN was_upset THEN 1 ELSE 0 END) as upsets
FROM prediction_logs
GROUP BY model_version;

-- Feature importance
SELECT feature_name, correlation_with_outcome
FROM feature_importance
ORDER BY ABS(correlation_with_outcome) DESC;

-- Pending AI suggestions
SELECT feature_name, reasoning, correlation_hypothesis
FROM feature_suggestions
WHERE status = 'pending';
```

---

## Timeline with 162 Replays

| Week | Replays | What To Do |
|------|---------|------------|
| **1** | 162 (current) | ✅ Enable log-only blending<br>✅ Get weight suggestions<br>✅ Monitor logs |
| **2** | 162-200 | ✅ Upload more replays<br>✅ Enable online learning<br>✅ Track predictions |
| **3** | 200-250 | ⏳ Enable blending (if improvement shown)<br>⏳ Monitor MMR changes |
| **4** | 250-300 | ⏳ Collect more data<br>⏳ Wait for feature suggestions |
| **5+** | 300+ | 🚀 Implement AI-suggested features<br>🚀 A/B test new models<br>🚀 Continuous improvement! |

---

## Safety Checklist

Before enabling blending:

- [  ] Log-only mode ran for 50+ matches
- [  ] Reviewed logs - adjustments seem reasonable
- [  ] Blended accuracy > TrueSkill accuracy (by 3%+)
- [  ] Have 200+ replays for confidence
- [  ] Monitoring dashboard shows stable performance

---

## Troubleshooting

### "Insufficient data" error
**Fix:** Need 100+ replays. You have 162 ✓

### "No improvement" in blending
**Fix:** Need 200+ replays for confidence. Upload 40 more.

### Feature suggestions empty
**Fix:** Need 300+ replays. System hasn't found patterns yet.

### Blending not logging
**Fix:** Check `config.py` has `enabled=True` and `log_only_mode=True`

---

## Next Steps

1. **Right now**: Set up database tables (5 min)
2. **This week**: Enable log-only blending, upload more replays
3. **Next week**: Check if blending helps, enable if yes
4. **Long term**: Implement AI-suggested features as system discovers them

**You're ready to start! 🚀**

Your 162 replays are perfect for Phases 1-2. Let the system learn!
