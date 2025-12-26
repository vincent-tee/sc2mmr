# SPEC-ML-001: Machine Learning Roadmap
## SC2 MMR Tracker - Enhanced Skill Assessment & Friend Insights

**Created**: 2025-12-09
**Goal**: Better skill rating, player insights, team balancing for friend groups

---

## 1. Current State Analysis

### 1.1 Existing MMR System

**Display MMR Formula**:
```python
MMR = 1000 + 40 × mu
# mu = TrueSkill skill estimate (default 25.0)
# Result: New players start at ~2000 MMR
```

**Hybrid MMR (Phase 1 - Rule-Based)**:
```python
Hybrid_MMR_Change = Base_Change × (1 + PIM)
# PIM = Performance Impact Modifier ∈ [-0.5, +0.5]
# Result: Good performance amplifies gains, reduces losses
```

### 1.2 Current Data Extraction (from SC2 Replays)

| Category | Metrics Captured | Status |
|----------|------------------|--------|
| **Economic** | Minerals, gas, workers, bases, spending efficiency | ✅ Done |
| **Combat** | Damage dealt/taken, units killed/lost, army value | ✅ Done |
| **Timing** | First expansion, first army, first damage, APM | ✅ Done |
| **Team** | Team fight participation %, damage share | ✅ Done |
| **Timeline** | Second-by-second damage (sparse JSON) | ✅ Done |
| **Archetype** | Rusher/Macro/Harasser classification | ✅ Done |

### 1.3 Current PIM Calculation (Rule-Based)

```python
# Weight distribution (must sum to 1.0)
Combat:     40% (damage_ratio, army_value_ratio, combat_score)
Economic:   25% (spending_efficiency, economic_score, resource_advantage)
Team:       25% (team_fight_participation, team_fight_damage_ratio)
Efficiency: 10% (efficiency_score)

# Calculation
raw_pim = weighted_sum(z_scores)
bounded_pim = 0.5 × tanh(raw_pim)  # Bounds to [-0.5, +0.5]
```

**Limitation**: Linear weights can't capture non-linear skill relationships.

---

## 2. Data Extraction Enhancements

### 2.1 Missing High-Value Data from SC2Reader

| Data Type | SC2Reader Source | Value for ML |
|-----------|------------------|--------------|
| **Build Order** | `replay.tracker_events` (UnitBornEvent, UnitInitEvent) | Build classification |
| **Unit Timeline** | `replay.tracker_events` (UnitBornEvent with timestamp) | Timing attack detection |
| **Upgrades** | `replay.tracker_events` (UpgradeCompleteEvent) | Tech path analysis |
| **Resource Float** | `player.current_food_used`, mineral/gas at checkpoints | Macro efficiency |
| **Abilities Used** | `replay.game_events` (AbilityEvent) | Micro skill |
| **Worker Losses** | Track worker UnitDiedEvent in first 5 min | Harassment response |

### 2.2 Implementation: Enhanced Data Extraction

**File**: `backend/app/services/enhanced_parser.py` (new)

```python
from sc2reader.events import (
    UnitBornEvent, UnitDiedEvent, UnitInitEvent,
    UpgradeCompleteEvent, AbilityEvent
)

class EnhancedReplayParser:
    """Extract ML-ready features from SC2 replays."""

    def extract_build_order(self, replay, player) -> list[dict]:
        """
        Extract chronological build order.
        Returns: [{"second": 45, "unit": "Marine", "count": 1}, ...]
        """
        build_events = []
        for event in replay.tracker_events:
            if isinstance(event, (UnitBornEvent, UnitInitEvent)):
                if event.unit_controller == player:
                    build_events.append({
                        "second": event.second,
                        "unit": event.unit_type_name,
                        "supply": event.unit.supply if hasattr(event.unit, 'supply') else 0
                    })
        return sorted(build_events, key=lambda x: x["second"])

    def extract_upgrade_timeline(self, replay, player) -> list[dict]:
        """
        Extract upgrade completion times.
        Returns: [{"second": 180, "upgrade": "StimPack"}, ...]
        """
        upgrades = []
        for event in replay.tracker_events:
            if isinstance(event, UpgradeCompleteEvent):
                if event.player == player:
                    upgrades.append({
                        "second": event.second,
                        "upgrade": event.upgrade_type_name
                    })
        return upgrades

    def extract_ability_usage(self, replay, player) -> dict:
        """
        Count ability usage for micro skill assessment.
        Returns: {"Stim": 15, "Snipe": 8, "EMP": 3, ...}
        """
        ability_counts = {}
        for event in replay.game_events:
            if isinstance(event, AbilityEvent):
                if event.player == player:
                    ability = event.ability_name
                    ability_counts[ability] = ability_counts.get(ability, 0) + 1
        return ability_counts

    def extract_resource_checkpoints(self, replay, player,
                                      intervals=[60, 120, 180, 300, 600]) -> list[dict]:
        """
        Sample resource state at key game moments.
        Returns: [{"second": 60, "minerals": 450, "gas": 100, "workers": 18}, ...]
        """
        # Implementation using replay state snapshots
        pass

    def extract_early_worker_losses(self, replay, player,
                                     cutoff_seconds=300) -> int:
        """
        Count workers lost in first 5 minutes (harassment indicator).
        """
        worker_deaths = 0
        worker_types = {"SCV", "Probe", "Drone"}
        for event in replay.tracker_events:
            if isinstance(event, UnitDiedEvent):
                if event.second <= cutoff_seconds:
                    if event.unit_controller == player:
                        if event.unit_type_name in worker_types:
                            worker_deaths += 1
        return worker_deaths
```

### 2.3 Database Schema Changes

**File**: `backend/app/models.py` - Add to PerformanceFeatures

```python
class PerformanceFeatures(Base):
    # ... existing fields ...

    # NEW: Build Order Data
    build_order_json = Column(JSON)  # Full build order sequence
    build_order_hash = Column(String(64))  # For clustering similar builds
    detected_build_type = Column(String(50))  # "2-base all-in", "macro", etc.

    # NEW: Upgrade Data
    upgrades_json = Column(JSON)  # [{"second": 180, "upgrade": "Stim"}]
    upgrade_timing_score = Column(Float)  # Z-score vs average upgrade times

    # NEW: Micro Data
    abilities_used_json = Column(JSON)  # {"Stim": 15, "EMP": 3}
    ability_efficiency = Column(Float)  # Abilities per damage dealt

    # NEW: Macro Data
    resource_float_avg = Column(Float)  # Average unspent resources
    supply_block_seconds = Column(Integer)  # Time spent supply blocked
    worker_saturation_score = Column(Float)  # How efficiently workers assigned

    # NEW: Harassment Response
    early_worker_losses = Column(Integer)  # Workers lost in first 5 min
    harassment_response_score = Column(Float)  # How well defended

    # NEW: ML Model Outputs
    ml_macro_score = Column(Float)  # ML-predicted macro skill (0-100)
    ml_micro_score = Column(Float)  # ML-predicted micro skill (0-100)
    ml_build_classification = Column(String(50))  # Classified build type
    ml_predicted_pim = Column(Float)  # ML model PIM prediction
```

---

## 3. ML Model Designs

### 3.1 Build Order Classifier (Phase 2A)

**Goal**: Classify player's strategic approach from build order

**Architecture**: LSTM or 1D-CNN on event sequences

```
Input:  Sequence of (unit_type, supply, second) tuples
        Padded to max_length=100 events

Encoding:
        - Unit type: One-hot (50 unit types)
        - Supply: Normalized 0-200
        - Second: Normalized 0-1800 (30 min)

Model:  LSTM(128) → LSTM(64) → Dense(32) → Dense(num_classes)

Output Classes:
        - "aggressive_rush" (attack before 5 min)
        - "timing_attack" (2-base attack 7-10 min)
        - "macro_expand" (3+ base, late army)
        - "cheese" (proxy, cannon rush, etc.)
        - "standard" (balanced approach)
        - "defensive" (turtle style)
```

**Training Data**:
- Existing matches in PerformanceFeatures
- Label by current `aggression_score` + `archetype` fields
- Augment with timing metrics

**Friend-Group Feature**:
- "Dave loves his Battlecruiser Rush! (detected 12 times)"
- "Sarah is playing more defensive lately (build shift detected)"

### 3.2 Macro/Micro Skill Decomposition (Phase 2B)

**Goal**: Separate skill into learnable components

**Macro Skill Model** (Gradient Boosting):
```python
macro_features = [
    'spending_efficiency',      # Resources spent / collected
    'worker_count_at_5min',     # Economy development
    'expansion_timing',         # When expanded
    'supply_block_seconds',     # Time supply blocked
    'resource_float_avg',       # Unspent resources
    'production_efficiency',    # Units produced / time
]

# Train: XGBoost regressor
# Target: Rank among players (0-100 percentile)
# Output: macro_skill_score (0-100)
```

**Micro Skill Model** (Gradient Boosting):
```python
micro_features = [
    'damage_ratio',             # Damage dealt / taken
    'army_value_efficiency',    # Kill value / loss value
    'ability_usage_rate',       # Abilities per minute
    'ability_effectiveness',    # Damage per ability
    'unit_preservation',        # Army survival rate
    'harassment_response',      # Early game defense
]

# Train: XGBoost regressor
# Target: Rank among players (0-100 percentile)
# Output: micro_skill_score (0-100)
```

**Friend-Group Feature**:
```
┌────────────────────────────────────────┐
│  Dave's Skill Breakdown               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                        │
│  Macro: ████████░░ 78/100             │
│  Micro: ████████████░ 92/100          │
│                                        │
│  💡 "Dave has great unit control but  │
│     could improve his expansion timing"│
└────────────────────────────────────────┘
```

### 3.3 Team Synergy Predictor (Phase 2C)

**Goal**: Predict how well players work together

**Model**: Neural Collaborative Filtering

```python
# Input per player
player_embedding = Embedding(num_players, 32)
playstyle_vector = [archetype_onehot, macro_score, micro_score, aggression]

# Team representation
team_1_embedding = Mean(player_embeddings)
team_1_style = Concat(player_styles)

# Synergy prediction
synergy_input = Concat(team_1_embedding, team_1_style,
                       team_2_embedding, team_2_style)
hidden = Dense(64, relu) → Dense(32, relu)
output = Dense(1, sigmoid)  # Win probability

# Training: Historical match outcomes
# Loss: Binary cross-entropy
```

**Friend-Group Features**:
- "Dave + Sarah have 73% win rate together! Great synergy!"
- "Mike + Lisa struggle together (41% WR) - try different pairing"
- Team generator uses this for better balance

### 3.4 Enhanced MMR Model (Phase 3)

**Goal**: Replace rule-based PIM with learned model

**Model**: XGBoost Ensemble

```python
features = [
    # Current z-scores
    'pim_combat_z', 'pim_economic_z', 'pim_team_z', 'pim_efficiency_z',

    # New ML features
    'ml_macro_score', 'ml_micro_score',
    'build_classification_onehot',
    'upgrade_timing_score',
    'ability_efficiency',

    # Context features
    'opponent_mmr_diff',  # Skill gap
    'map_onehot',         # Map effects
    'race_matchup',       # Race advantages
    'team_synergy_score', # Team compatibility

    # Historical
    'recent_form',        # Last 10 games performance
    'improvement_trend',  # Slope of recent scores
]

# Target: Actual MMR change (from TrueSkill)
# Model: XGBoost with early stopping
# Output: Predicted skill adjustment

# A/B Testing
if random() < 0.5:
    use ml_pim
else:
    use rule_based_pim
# Track which performs better
```

---

## 4. Player Insights System

### 4.1 Strength/Weakness Analysis

**Radar Chart Data**:
```python
def calculate_player_radar(player_id):
    return {
        "Economy": player.avg_economic_score,  # 0-100
        "Combat": player.avg_combat_score,      # 0-100
        "Timing": player.avg_timing_score,      # 0-100
        "Teamwork": player.avg_team_score,      # 0-100
        "Consistency": player.consistency_score, # 0-100
        "Adaptability": player.style_variance,   # 0-100
    }
```

**Personalized Tips**:
```python
def generate_tips(player):
    tips = []

    if player.ml_macro_score < 50:
        tips.append("💡 Try focusing on worker production - aim for 70 workers by 10 min")

    if player.early_worker_losses > avg * 1.5:
        tips.append("🛡️ You're losing lots of workers to early harassment - scout more!")

    if player.upgrade_timing_score < -1:
        tips.append("⚔️ Your upgrades are late - prioritize attack/armor upgrades")

    if player.ability_efficiency < avg:
        tips.append("✨ Practice using abilities more - they can turn fights!")

    return tips
```

### 4.2 Historical Trends

```python
def calculate_trends(player_id, window=30):
    recent_matches = get_last_n_matches(player_id, window)

    return {
        "mmr_trend": linear_regression_slope(recent_matches, 'mmr'),
        "macro_trend": linear_regression_slope(recent_matches, 'economic_score'),
        "micro_trend": linear_regression_slope(recent_matches, 'combat_score'),
        "consistency": std_dev(recent_matches, 'overall_impact'),
        "peak_mmr": max(recent_matches, 'mmr'),
        "improvement_rate": (recent_avg - old_avg) / time_period,
    }
```

### 4.3 Friend-Group Comparisons

```python
def player_vs_group(player_id, group_ids):
    player_stats = get_player_stats(player_id)
    group_avg = get_group_average(group_ids)

    return {
        "mmr_rank": rank_in_group(player_id, 'mmr'),
        "economy_percentile": percentile_in_group(player_id, 'economic_score'),
        "combat_percentile": percentile_in_group(player_id, 'combat_score'),
        "most_improved": is_most_improved(player_id, group_ids),
        "best_vs": best_opponent_matchup(player_id, group_ids),
        "worst_vs": worst_opponent_matchup(player_id, group_ids),
    }
```

---

## 5. Implementation Phases

### Phase 2A: Data Extraction (Week 1-2)
- [ ] Create `enhanced_parser.py` with build order extraction
- [ ] Add upgrade timeline extraction
- [ ] Add ability usage counting
- [ ] Add resource checkpoint sampling
- [ ] Update database schema
- [ ] Backfill existing matches (if replays available)

### Phase 2B: Skill Decomposition (Week 3-4)
- [ ] Implement macro skill model (XGBoost)
- [ ] Implement micro skill model (XGBoost)
- [ ] Create training pipeline
- [ ] Add radar chart API endpoint
- [ ] Add personalized tips generator
- [ ] Frontend: Skill breakdown component

### Phase 2C: Build Classifier (Week 5-6)
- [ ] Prepare build order dataset
- [ ] Train LSTM classifier
- [ ] Integrate into replay processing
- [ ] Add build type to player profiles
- [ ] Frontend: Build history display

### Phase 2D: Team Synergy (Week 7-8)
- [ ] Prepare player pair dataset
- [ ] Train collaborative filtering model
- [ ] Integrate into team generator
- [ ] Add synergy indicators to UI
- [ ] Frontend: Synergy badges

### Phase 3: Enhanced MMR Model (Week 9-12)
- [ ] Prepare comprehensive feature set
- [ ] Train XGBoost ensemble
- [ ] Implement A/B testing framework
- [ ] Monitor and compare models
- [ ] Gradual rollout to all matches

---

## 6. API Endpoints

### New Endpoints Required

```python
# Player insights
GET /api/players/{id}/insights
Response: {
    "radar_data": {...},
    "trends": {...},
    "tips": [...],
    "group_comparison": {...}
}

# Build history
GET /api/players/{id}/builds
Response: {
    "recent_builds": [...],
    "favorite_build": "macro_expand",
    "build_variety": 0.7
}

# Skill breakdown
GET /api/players/{id}/skills
Response: {
    "macro_score": 78,
    "micro_score": 65,
    "breakdown": {...}
}

# Team synergy
GET /api/teams/synergy
Body: {"player_ids": [1, 2, 3, 4]}
Response: {
    "team_1_synergy": 0.72,
    "team_2_synergy": 0.68,
    "pair_synergies": {...}
}

# Enhanced team generation
POST /api/teams/generate-ml
Body: {"player_ids": [...], "use_synergy": true}
Response: {
    "suggestions": [...],
    "synergy_scores": {...}
}
```

---

## 7. Technical Requirements

### 7.1 Python Dependencies

```txt
# ML Core
scikit-learn>=1.3.0
xgboost>=2.0.0
lightgbm>=4.0.0

# Deep Learning (for build classifier)
torch>=2.0.0  # or tensorflow>=2.15.0
# Lightweight alternative: pytorch-lightning

# Data Processing
pandas>=2.0.0
numpy>=1.24.0

# Model Serialization
joblib>=1.3.0
onnx>=1.14.0  # For model export
```

### 7.2 Model Storage

```
backend/
├── ml_models/
│   ├── macro_skill_v1.joblib
│   ├── micro_skill_v1.joblib
│   ├── build_classifier_v1.pt
│   ├── synergy_model_v1.joblib
│   └── enhanced_pim_v1.joblib
├── app/
│   └── services/
│       ├── ml_service.py      # Model loading & inference
│       ├── training_service.py # Model training
│       └── feature_service.py  # Feature extraction
```

### 7.3 Model Versioning

```python
class MLModelRegistry:
    """Track model versions and A/B test results."""

    models = {
        "macro_skill": {"version": "v1", "accuracy": 0.82},
        "micro_skill": {"version": "v1", "accuracy": 0.79},
        "build_classifier": {"version": "v1", "accuracy": 0.74},
        "synergy": {"version": "v1", "mse": 0.15},
        "enhanced_pim": {"version": "v1", "ab_test_result": "pending"},
    }

    def get_model(self, name):
        path = f"ml_models/{name}_{self.models[name]['version']}.joblib"
        return joblib.load(path)
```

---

## 8. Friend-Group Specific Features

### 8.1 "Most Improved" Detection

```python
def find_most_improved(group_ids, period_days=30):
    improvements = []
    for player_id in group_ids:
        old_mmr = get_mmr_at(player_id, days_ago=period_days)
        current_mmr = get_current_mmr(player_id)
        improvement = current_mmr - old_mmr
        improvements.append((player_id, improvement))

    return max(improvements, key=lambda x: x[1])
```

### 8.2 Rivalry Analysis

```python
def analyze_rivalries(group_ids):
    rivalries = []
    for p1, p2 in combinations(group_ids, 2):
        head_to_head = get_head_to_head(p1, p2)
        if head_to_head['total_games'] >= 5:
            rivalries.append({
                "players": [p1, p2],
                "games": head_to_head['total_games'],
                "leader": p1 if head_to_head['p1_wins'] > head_to_head['p2_wins'] else p2,
                "intensity": calculate_rivalry_intensity(head_to_head),
            })

    return sorted(rivalries, key=lambda x: x['intensity'], reverse=True)
```

### 8.3 Play Style Compatibility

```python
def calculate_compatibility(player_1, player_2):
    """
    Some play styles complement each other:
    - Aggressive + Defensive = Good
    - Two Aggressive = Risky but fun
    - Two Defensive = Slow games
    """
    style_1 = get_play_style(player_1)  # "aggressive", "defensive", "balanced"
    style_2 = get_play_style(player_2)

    compatibility_matrix = {
        ("aggressive", "defensive"): 0.9,  # Great combo
        ("aggressive", "aggressive"): 0.6,  # High variance
        ("defensive", "defensive"): 0.5,   # Slow but stable
        ("balanced", "balanced"): 0.7,     # Flexible
        ("balanced", "aggressive"): 0.8,
        ("balanced", "defensive"): 0.75,
    }

    return compatibility_matrix.get((style_1, style_2), 0.7)
```

---

## 9. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| MMR Prediction Accuracy | N/A | >75% | Compare predicted vs actual |
| Build Classification | N/A | >70% | Manual labeling validation |
| Team Balance Accuracy | ~55% | >65% | Predicted winner vs actual |
| Player Satisfaction | N/A | 8/10 | User surveys |
| Insight Usefulness | N/A | 7/10 | "Did tip help?" feedback |

---

## 10. Summary

This ML roadmap transforms the SC2 tracker from a simple stats display into an **intelligent friend-group gaming companion**:

1. **Better Skill Assessment**: Separate macro/micro skills, not just win/loss
2. **Personalized Insights**: Tips tailored to each player's weaknesses
3. **Smarter Team Balancing**: Synergy-aware team generation
4. **Fun Friend Features**: Rivalries, improvement tracking, compatibility

**Data is already being collected** - we just need to extract more from SC2Reader and train models on it.

**Next Immediate Step**: Implement `enhanced_parser.py` to capture build orders and upgrades from existing replays.
