# SPEC-ML-001: ML-Enhanced Hybrid MMR System

---
id: SPEC-ML-001
version: 1.0.0
status: draft
created: 2025-12-06
updated: 2025-12-06
author: R2-D2
priority: high
depends_on: SPEC-REFACTOR-001
---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-06 | R2-D2 | Initial SPEC creation |

---

## 1. Overview

### 1.1 Purpose

Enhance the SC2 MMR Tracker with a **Hybrid MMR System** that combines:
1. **TrueSkill MMR** (70%): Traditional win/loss Bayesian skill rating
2. **Performance Impact Score** (30%): Game event-based performance metrics

This creates a **living, data-driven rating** that:
- Rewards strong performance even in losses
- Penalizes poor performance even in wins
- Improves prediction accuracy over time as ML learns optimal weights
- Provides fairer team balancing by capturing true skill beyond W/L

### 1.2 Scope

| Area | In Scope | Out of Scope |
|------|----------|--------------|
| MMR Integration | Add performance modifier to MMR gain/loss | Replacing TrueSkill entirely |
| Feature Store | Store normalized metrics per match | Real-time streaming analytics |
| Rule-Based Scoring | Implement weighted formula for performance | Deep learning/neural networks |
| ML Foundation | Design for future model training | Training ML models (Phase 2) |
| API Changes | Expose hybrid MMR and breakdown | New UI components |

### 1.3 Design Philosophy

**Start Rule-Based → Grow into ML**

| Phase | Implementation | Data Requirement |
|-------|---------------|------------------|
| Phase 1 | Rule-based weighted formula | 0 matches (works immediately) |
| Phase 2 | Collect feature vectors | 100+ matches |
| Phase 3 | Train regression model | 500+ matches |
| Phase 4 | Deploy ML model | 1000+ matches |
| Phase 5 | Continuous learning | Ongoing |

### 1.4 Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Prediction Accuracy | ~55% | 65%+ |
| Team Balance Quality | 0.58 avg | 0.70 avg |
| Player Satisfaction | N/A | Positive feedback on fairness |
| Data Coverage | 0% matches with ML features | 100% |

---

## 2. Functional Requirements (MUST)

### 2.1 Hybrid MMR Calculation

| ID | Requirement |
|----|-------------|
| FR-001 | The system MUST calculate a Performance Impact Modifier (PIM) for each player per match |
| FR-002 | The system MUST apply PIM to modify MMR gain/loss: `actual_change = base_change × (1 + PIM)` |
| FR-003 | The system MUST bound PIM to range [-0.5, +0.5] (±50% modifier max) |
| FR-004 | The system MUST store both `raw_mmr_change` (TrueSkill only) and `hybrid_mmr_change` (with PIM) |
| FR-005 | The system MUST display Hybrid MMR as the primary rating on player cards |

### 2.2 Performance Impact Modifier (PIM) Calculation

| ID | Requirement |
|----|-------------|
| FR-010 | PIM MUST be calculated from existing `PlayerMatchMetrics` fields |
| FR-011 | PIM MUST use weighted formula: `PIM = Σ(weight_i × normalized_metric_i)` |
| FR-012 | PIM MUST normalize metrics relative to match average (z-score normalization) |
| FR-013 | PIM MUST handle edge cases: solo games, incomplete metrics, very short games |

### 2.3 Feature Store

| ID | Requirement |
|----|-------------|
| FR-020 | The system MUST create `PerformanceFeatures` table storing normalized metrics |
| FR-021 | The system MUST store raw metric values for ML training data |
| FR-022 | The system MUST store PIM and its component breakdown per match player |
| FR-023 | The system MUST support versioned weight configurations |

### 2.4 Backward Compatibility

| ID | Requirement |
|----|-------------|
| FR-030 | The system MUST preserve existing TrueSkill mu/sigma fields |
| FR-031 | The system MUST maintain backward-compatible API responses |
| FR-032 | The system MUST allow toggling hybrid MMR on/off via config |

---

## 3. Non-Functional Requirements (SHOULD)

### 3.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-001 | PIM calculation SHOULD complete in <100ms per match |
| NFR-002 | Feature normalization SHOULD use cached match statistics |
| NFR-003 | Database queries for features SHOULD be indexed appropriately |

### 3.2 Extensibility

| ID | Requirement |
|----|-------------|
| NFR-010 | Weight configuration SHOULD be externalized in JSON/YAML |
| NFR-011 | New metrics SHOULD be addable without schema changes |
| NFR-012 | ML model integration SHOULD be pluggable (swap rule-based for trained model) |

### 3.3 Observability

| ID | Requirement |
|----|-------------|
| NFR-020 | PIM distribution SHOULD be logged for analysis |
| NFR-021 | Prediction accuracy SHOULD be tracked (predicted vs actual winner) |
| NFR-022 | Feature correlation with wins SHOULD be queryable |

---

## 4. Technical Design

### 4.1 Performance Impact Modifier Formula (Rule-Based v1)

```python
# Weights for Performance Impact Modifier (sum to 1.0)
WEIGHTS = {
    # Combat Performance (40%)
    "damage_ratio": 0.15,        # Damage dealt / damage taken
    "army_value_ratio": 0.15,   # Army value killed / army value lost
    "combat_score": 0.10,       # Existing 0-100 combat score

    # Economic Performance (25%)
    "spending_efficiency": 0.10, # Resources spent / collected
    "economic_score": 0.10,      # Existing 0-100 economic score
    "resource_advantage": 0.05,  # Total resources vs match average

    # Team Contribution (25%)
    "team_fight_participation": 0.10,  # % of team fights participated
    "team_fight_damage_ratio": 0.10,   # Damage ratio in team fights
    "overall_impact": 0.05,            # Existing overall impact score

    # Efficiency (10%)
    "efficiency_score": 0.10,    # Existing efficiency score
}

def calculate_pim(metrics: PlayerMatchMetrics, match_avg: MatchAverages) -> float:
    """
    Calculate Performance Impact Modifier.

    Returns float in range [-0.5, +0.5]
    - Positive: Better than average performance
    - Negative: Below average performance
    - 0: Average performance
    """
    z_scores = {}

    # Z-score normalization for each metric
    for metric_name, weight in WEIGHTS.items():
        value = getattr(metrics, metric_name, 0)
        avg = getattr(match_avg, metric_name, 0)
        std = getattr(match_avg, f"{metric_name}_std", 1)

        if std > 0:
            z_scores[metric_name] = (value - avg) / std
        else:
            z_scores[metric_name] = 0

    # Weighted sum
    raw_pim = sum(z_scores[m] * w for m, w in WEIGHTS.items())

    # Sigmoid-like bounding to [-0.5, +0.5]
    bounded_pim = 0.5 * tanh(raw_pim)

    return bounded_pim
```

### 4.2 Hybrid MMR Integration

```python
def update_hybrid_mmr(player: Player, base_change: float, pim: float) -> float:
    """
    Apply Performance Impact Modifier to MMR change.

    Examples:
    - Win with great performance (PIM=+0.3): +50 → +65 MMR
    - Win with poor performance (PIM=-0.3): +50 → +35 MMR
    - Loss with great performance (PIM=+0.3): -50 → -35 MMR
    - Loss with poor performance (PIM=-0.3): -50 → -65 MMR
    """
    modifier = 1.0 + pim  # Range: [0.5, 1.5]

    if base_change >= 0:
        # Won: good performance = more gain, bad = less gain
        actual_change = base_change * modifier
    else:
        # Lost: good performance = less loss, bad = more loss
        actual_change = base_change * (2.0 - modifier)  # Inverted for losses

    return actual_change
```

### 4.3 Database Schema

```sql
-- Performance Features Table (ML-ready feature store)
CREATE TABLE performance_features (
    id INTEGER PRIMARY KEY,
    match_player_id INTEGER REFERENCES match_player(id),

    -- Normalized features (z-scores relative to match)
    damage_ratio_z REAL,
    army_value_ratio_z REAL,
    combat_score_z REAL,
    spending_efficiency_z REAL,
    economic_score_z REAL,
    resource_advantage_z REAL,
    team_fight_participation_z REAL,
    team_fight_damage_ratio_z REAL,
    overall_impact_z REAL,
    efficiency_score_z REAL,

    -- Calculated PIM
    pim REAL,
    pim_version VARCHAR(20) DEFAULT 'rule_v1',

    -- MMR changes
    raw_mmr_change REAL,        -- TrueSkill only
    hybrid_mmr_change REAL,     -- With PIM applied

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weight configuration table (versioned)
CREATE TABLE pim_weight_config (
    id INTEGER PRIMARY KEY,
    version VARCHAR(20) UNIQUE,
    weights_json TEXT,
    active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_perf_features_match_player ON performance_features(match_player_id);
CREATE INDEX idx_perf_features_pim ON performance_features(pim);
```

### 4.4 API Changes

```python
# Extended Player response
class PlayerResponse(BaseModel):
    id: int
    name: str

    # Traditional MMR
    mu: float
    sigma: float
    mmr: float  # Display MMR: 1000 + 40*mu

    # Hybrid MMR (NEW)
    hybrid_mmr: float  # MMR with performance adjustments
    avg_pim: float     # Average PIM across all games
    pim_trend: str     # "improving", "stable", "declining"

    # Existing fields...

# Match detail includes PIM breakdown
class MatchPlayerResponse(BaseModel):
    player_id: int
    player_name: str
    team: int
    won: bool

    # MMR changes
    mmr_before: float
    mmr_after: float
    raw_mmr_change: float      # TrueSkill only
    hybrid_mmr_change: float   # With PIM
    pim: float                 # Performance modifier

    # PIM breakdown (NEW)
    pim_breakdown: Dict[str, float]  # {"combat": 0.12, "economic": -0.05, ...}
```

### 4.5 Configuration

```yaml
# config/pim_config.yaml
version: "rule_v1"
enabled: true
weights:
  combat:
    damage_ratio: 0.15
    army_value_ratio: 0.15
    combat_score: 0.10
  economic:
    spending_efficiency: 0.10
    economic_score: 0.10
    resource_advantage: 0.05
  team:
    team_fight_participation: 0.10
    team_fight_damage_ratio: 0.10
    overall_impact: 0.05
  efficiency:
    efficiency_score: 0.10

bounds:
  pim_min: -0.5
  pim_max: 0.5

# ML settings (Phase 2+)
ml:
  enabled: false
  model_path: null
  fallback_to_rules: true
```

---

## 5. Implementation Phases

### Phase 1: Rule-Based Foundation (This SPEC)
- Implement PIM calculation using weighted formula
- Create `performance_features` table
- Modify rating update flow to include PIM
- Add PIM breakdown to API responses
- Add configuration for weights and enablement

### Phase 2: Data Collection & Analysis
- Collect 500+ matches with feature vectors
- Analyze feature correlation with match outcomes
- A/B test rule-based weights
- Track prediction accuracy

### Phase 3: ML Model Training (Future SPEC)
- Train regression model to predict optimal PIM
- Compare ML predictions vs rule-based
- Implement model serving infrastructure
- Deploy with fallback to rules

### Phase 4: Continuous Learning (Future SPEC)
- Implement periodic retraining pipeline
- Add online learning capability
- Track model drift and accuracy

---

## 6. Acceptance Criteria

### 6.1 PIM Calculation

```gherkin
GIVEN a match with 4 players
WHEN metrics are extracted from replay
THEN each player SHALL have a PIM in range [-0.5, +0.5]

GIVEN a player with above-average damage ratio
WHEN PIM is calculated
THEN the combat component SHALL be positive

GIVEN a player with below-average spending efficiency
WHEN PIM is calculated
THEN the economic component SHALL be negative
```

### 6.2 Hybrid MMR

```gherkin
GIVEN a player who wins with exceptional performance (PIM=+0.4)
WHEN MMR is updated
THEN hybrid_mmr_change SHALL be ~140% of raw_mmr_change

GIVEN a player who loses but performed exceptionally (PIM=+0.3)
WHEN MMR is updated
THEN hybrid_mmr_change loss SHALL be ~30% less than raw_mmr_change

GIVEN hybrid MMR is disabled in config
WHEN MMR is updated
THEN hybrid_mmr_change SHALL equal raw_mmr_change
```

### 6.3 API

```gherkin
GIVEN a player profile API request
WHEN response is returned
THEN it SHALL include hybrid_mmr and avg_pim fields

GIVEN a match detail API request
WHEN response is returned
THEN each player SHALL have pim and pim_breakdown fields
```

---

## 7. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PIM rewards farming over winning | Medium | High | Cap PIM influence to ±50%, prioritize win-correlated metrics |
| Players game the system | Low | Medium | Use diverse metrics, monitor for anomalies |
| Initial weights are poor | Medium | Medium | Start conservative (±25%), tune based on data |
| Complexity confuses users | Low | Medium | Show simple "Performance: Good/Average/Poor" label |
| Historical data mismatch | Medium | Low | Only apply to new matches, don't retroactively adjust |

---

## 8. Dependencies

### 8.1 Internal Dependencies

| Component | Dependency |
|-----------|------------|
| PIM Calculator | `PlayerMatchMetrics` (already exists) |
| Feature Store | New database migration |
| API Changes | Existing player/match endpoints |

### 8.2 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| scipy | ^1.11.0 | Statistical functions (z-score, tanh) |
| pydantic | ^2.0.0 | Configuration validation |

---

## 9. Glossary

| Term | Definition |
|------|------------|
| PIM | Performance Impact Modifier - adjustment factor based on in-game metrics |
| Hybrid MMR | Combined rating: TrueSkill base + performance adjustments |
| Z-score | Normalized metric: (value - mean) / std_deviation |
| Feature Store | Database table storing ML-ready feature vectors |
| Rule-Based | Deterministic formula using predefined weights |

---

## 10. References

- [TrueSkill Documentation](https://trueskill.org/)
- [Z-score Normalization](https://en.wikipedia.org/wiki/Standard_score)
- [StarCraft 2 Replay Analysis](https://liquipedia.net/starcraft2/Replay)
- Existing: `backend/app/advanced_parser.py` - Current impact scoring
- Existing: `backend/app/models.py` - PlayerMatchMetrics schema

---

## 11. Appendix: Current Metrics Available

From `PlayerMatchMetrics` model (already tracked):

| Category | Metrics |
|----------|---------|
| Economic | `minerals_collected`, `vespene_collected`, `spending_efficiency`, `workers_created`, `bases_created` |
| Combat | `damage_dealt`, `damage_taken`, `damage_ratio`, `units_killed`, `units_lost`, `army_value_killed`, `army_value_lost` |
| Team | `team_fight_participation`, `team_fight_damage`, `team_fight_damage_ratio` |
| Impact | `economic_score`, `combat_score`, `efficiency_score`, `overall_impact` (0-100) |
| Timing | `first_damage_timing`, `early_game_damage`, `mid_game_damage`, `late_game_damage` |
| Profile | `player_archetype`, `aggression_score`, `apm` |
