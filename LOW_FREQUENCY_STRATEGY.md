# Low-Frequency Gameplay Strategy (10 Games per 2 Weeks)

## Your Reality

- **Current**: 162 replays (32+ weeks of gameplay!)
- **New data rate**: 5 games/week (10 per 2 weeks)
- **To reach 300 replays**: 28 more weeks (~7 months)
- **Every match counts** - can't wait for thousands of replays

---

## Aggressive Learning Strategy

### Phase 1: Immediate (Week 1 - Your 162 Replays)

**Extract MAXIMUM value from existing data:**

```python
# Aggressive blending - your data is gold!
BLENDED_RATING_CONFIG = BlendConfig(
    enabled=True,
    log_only_mode=True,      # Start safe
    trueskill_weight=0.60,   # 60% TrueSkill
    adaptive_weight=0.40,    # 40% Adaptive (AGGRESSIVE!)

    # Be bold in logs - no risk
    max_adjustment_percent=0.6
)
```

**Why aggressive with 162 replays:**
- ✅ 8 months of real gameplay patterns
- ✅ You know your player meta intimately
- ✅ Small, consistent player pool
- ✅ Log-only = zero risk

**Action Items:**
1. Upload all 162 replays with blending in log-only mode
2. Review every adjustment in logs
3. **Manually annotate patterns you see:**
   - "Player X always rushes on this map"
   - "Protoss+Terran combos win more"
   - "Race Y dominates map Z"

---

### Phase 2: Go Live Fast (Week 2-3)

With only 5 games/week, **don't wait**:

```python
# After reviewing logs for just 10 new matches
if logs_look_reasonable:
    BLENDED_RATING_CONFIG.log_only_mode = False  # GO LIVE!
    BLENDED_RATING_CONFIG.adaptive_weight = 0.25  # Conservative live

# You'll see real MMR changes:
# Upsets: +30 MMR instead of +25
# Expected: +21 MMR instead of +25
```

---

### Phase 3: Manual Feature Discovery (Ongoing)

**Don't wait for 300+ replays.** You know your meta better than any AI!

#### Add Features YOU Know Matter

```python
# You probably know these affect outcomes:
features_to_add = [
    "player_race_preference",    # Some players excel with one race
    "map_familiarity",          # Players who spam one map
    "player_synergy_history",   # Players who always team together
    "time_of_day",              # Late night games different?
    "player_recent_form"        # Winning/losing streak
]
```

**How to implement:**

```python
# Add to your parser (backend/app/advanced_parser.py)
def calculate_player_synergy_boost(player1, player2, db):
    """Check if these players have history together."""
    past_games_together = db.query(MatchPlayer).filter(
        # ... query for past matches with both players
    ).count()

    if past_games_together > 5:
        # These players team often - check their win rate together
        wins_together = count_wins_together(player1, player2, db)
        return wins_together / past_games_together
    return 0.5  # Neutral

# Include in your prediction features
features['player_synergy'] = calculate_player_synergy_boost(...)
```

---

### Phase 4: Human-in-the-Loop Learning

With low game frequency, **you are the feature detector**:

#### After Each Game Session (10 games)

```sql
-- Which maps had upsets?
SELECT map_name, COUNT(*) as upset_count
FROM matches m
JOIN prediction_logs pl ON m.id = pl.match_id
WHERE pl.was_upset = TRUE
AND m.played_at > datetime('now', '-14 days')
GROUP BY map_name;

-- Which race matchups surprised the model?
SELECT team1_races, team2_races, actual_winner
FROM matches
WHERE prediction_error > 0.3
ORDER BY played_at DESC
LIMIT 10;
```

**Ask yourself:**
- "Why did the model get this wrong?"
- "Do I see a pattern the model missed?"
- **Implement that pattern as a feature!**

---

## Optimized Learning Triggers

Instead of "retrain every 50 matches" (that's 10 weeks!), use:

```python
# backend/app/online_learning.py
class LowFrequencyLearningConfig:
    # Retrain frequently with limited data
    retrain_every_n_matches = 10  # Every 2 weeks!
    min_matches_for_training = 50  # You already have 162!

    # Lower feature discovery threshold
    min_correlation_threshold = 0.10  # Was 0.15
    min_matches_for_feature_discovery = 100  # Was 300

    # More aggressive weight updates
    max_weight_change_per_update = 0.15  # Was 0.10
```

**Result:** Model improves every 2 weeks instead of waiting months!

---

## Frontend: Show Model Evolution Clearly

Since updates are infrequent, **make changes very visible**:

### Model Evolution Timeline

```jsx
// Show model versions with dates
Model v1.0 (Jan 1)  →  v1.1 (Jan 15)  →  v1.2 (Feb 1)
  162 replays           172 replays         182 replays
  65% accuracy          68% accuracy        71% accuracy

  Changes:
  - Increased combat weight 40% → 45%
  - Added map_synergy feature
  - Upset detection improved
```

### Per-Match Learning Display

After each upload session:

```
🎮 10 New Matches Processed!

📊 Model Performance This Session:
  ✓ 7/10 predictions correct (70%)
  📈 3 upsets detected (model learning!)
  🎯 Avg prediction error: 0.18 (↓ from 0.22)

🧠 What Changed:
  - Combat weight: 45% → 47% (+2%)
  - Map control correlation: +0.08
  - Terran+Protoss synergy detected: 1.15x

💡 Insights:
  - Model struggled on "Lost Temple" (0/2)
  - Consider adding map-specific features?
  - Protoss showing 62% win rate (up from 54%)
```

---

## Database Optimization for Low Frequency

With limited matches, **keep ALL historical data**:

```sql
-- Don't limit to recent 500 matches
-- Use ALL matches for training
SELECT * FROM matches
WHERE played_at > datetime('now', '-365 days')  -- Keep full year
ORDER BY played_at DESC;

-- Weight recent matches more, but don't discard old data
-- Old matches = 50% weight
-- Recent matches = 100% weight
weight = 0.5 + 0.5 * (days_since / 365)
```

---

## Realistic Timeline (10 Games per 2 Weeks)

| Week | Total Replays | What Happens |
|------|---------------|--------------|
| **1** | 162 (current) | ✅ Log-only blending at 40%<br>✅ Review all adjustments<br>✅ Get weight suggestions |
| **2** | 167 | ✅ 5 new games<br>⏳ Model retrains with new data |
| **3** | 172 | ✅ Go LIVE with 25% blending<br>✅ Model retrains again |
| **4** | 177 | 📊 Monitor accuracy |
| **5-6** | 182-187 | 📊 Collect 2 more sessions |
| **7** | 192 | 🎯 Model v1.1: New weights based on 30 new games |
| **12** | 217 | 🚀 Enough data for feature discovery |
| **20** | 262 | 💡 AI suggests new features |
| **30** | 312 | 🎉 Rich model with multiple features |

---

## Your Advantages with Low Frequency

**Don't think of it as "limited data" - you have advantages:**

1. **Stable Player Pool**
   - Same ~20 players
   - Consistent skill levels
   - Model learns THEM specifically

2. **Known Meta**
   - You understand player tendencies
   - You know map preferences
   - **Your insights > Generic AI**

3. **Quality Over Quantity**
   - Every game is serious (not ladder spam)
   - Consistent game format
   - Meaningful outcomes

4. **Human Feature Engineering**
   - You can add features the AI would need 1000+ replays to discover
   - "Player X always goes mech on maps with open areas"
   - "Player Y tilts after losing first game"

---

## Immediate Action Plan

### This Week:

1. **Remove Animations** (done!)
2. **Enable Aggressive Log-Only Blending**
   ```python
   adaptive_weight = 0.40  # Be bold!
   ```
3. **Upload All 162 Replays**
4. **Review Logs for Patterns**

### Next Session (2 weeks):

1. **Play Your 10 Games**
2. **Upload Immediately**
3. **Check Model Retraining Output**
4. **Go Live if Logs Look Good**

### Month 2:

1. **Add 1-2 Manual Features You Know Matter**
   - Player synergies?
   - Map preferences?
   - Race expertise?
2. **A/B Test New Features**
3. **Promote if Better**

---

## Key Insight

**With 10 games per 2 weeks, you don't wait for the AI to discover patterns.**

**YOU are the pattern detector. The AI is the pattern validator.**

Think of it as:
- **You**: "I think Protoss+Terran works well together"
- **AI**: "Let me check... yes! 1.15x win rate confirmed"
- **System**: "Feature added, confidence high"

You're not waiting for 300 replays to discover early_aggression.
You're TELLING the system "early aggression matters" and letting it quantify how much.

---

**Next: Rethink the frontend to make model evolution VERY visible even with sparse updates.**
