# SPEC-ML-001: Acceptance Criteria

---
spec_id: SPEC-ML-001
version: 1.0.0
created: 2025-12-06
---

## Acceptance Test Scenarios

### AT-001: PIM Calculation Accuracy

```gherkin
Feature: Performance Impact Modifier Calculation

  Scenario: Above-average performance yields positive PIM
    Given a match with 4 players
    And player "TopPerformer" has damage_ratio=2.5, combat_score=85
    And the match average damage_ratio=1.2, combat_score=55
    When PIM is calculated for "TopPerformer"
    Then PIM SHALL be positive (> 0.1)

  Scenario: Below-average performance yields negative PIM
    Given a match with 4 players
    And player "Underperformer" has damage_ratio=0.3, combat_score=20
    And the match average damage_ratio=1.2, combat_score=55
    When PIM is calculated for "Underperformer"
    Then PIM SHALL be negative (< -0.1)

  Scenario: Average performance yields near-zero PIM
    Given a match with 4 players
    And player "Average" has metrics equal to match average
    When PIM is calculated for "Average"
    Then PIM SHALL be within [-0.05, +0.05]

  Scenario: PIM is bounded
    Given a player with extremely exceptional metrics
    When PIM is calculated
    Then PIM SHALL NOT exceed +0.5
    And PIM SHALL NOT be below -0.5
```

### AT-002: Hybrid MMR Application

```gherkin
Feature: Hybrid MMR Calculation

  Scenario: Win with good performance amplifies gain
    Given player has base MMR change of +50 (win)
    And player's PIM is +0.3
    When hybrid MMR is calculated
    Then hybrid_mmr_change SHALL be +65 (50 × 1.3)

  Scenario: Win with poor performance reduces gain
    Given player has base MMR change of +50 (win)
    And player's PIM is -0.3
    When hybrid MMR is calculated
    Then hybrid_mmr_change SHALL be +35 (50 × 0.7)

  Scenario: Loss with good performance reduces loss
    Given player has base MMR change of -50 (loss)
    And player's PIM is +0.3
    When hybrid MMR is calculated
    Then hybrid_mmr_change SHALL be -35 (-50 × 0.7)

  Scenario: Loss with poor performance amplifies loss
    Given player has base MMR change of -50 (loss)
    And player's PIM is -0.3
    When hybrid MMR is calculated
    Then hybrid_mmr_change SHALL be -65 (-50 × 1.3)
```

### AT-003: Feature Store Persistence

```gherkin
Feature: Performance Features Storage

  Scenario: Features stored after match processing
    Given a match is processed with 6 players
    When replay processing completes
    Then 6 PerformanceFeatures records SHALL be created
    And each record SHALL have a valid match_player_id
    And each record SHALL have a pim value

  Scenario: Z-scores are normalized correctly
    Given a match with varied player performance
    When PerformanceFeatures are stored
    Then z-score values SHALL center around 0 for the match
    And extremely high performers SHALL have z > 1
    And extremely low performers SHALL have z < -1
```

### AT-004: API Responses

```gherkin
Feature: API Response Schema

  Scenario: Player profile includes hybrid MMR
    Given player "TestPlayer" exists with hybrid_mmr=2150
    When GET /api/players/1 is called
    Then response SHALL include "hybrid_mmr": 2150
    And response SHALL include "avg_pim" field

  Scenario: Match detail includes PIM breakdown
    Given match 1 exists with processed performance features
    When GET /api/matches/1 is called
    Then each player in response SHALL have "pim" field
    And each player SHALL have "pim_breakdown" object
    And pim_breakdown SHALL contain "combat", "economic", "team", "efficiency"
```

### AT-005: Configuration

```gherkin
Feature: Hybrid MMR Configuration

  Scenario: Hybrid MMR can be disabled
    Given config has hybrid_mmr_enabled=false
    When a match is processed
    Then hybrid_mmr_change SHALL equal raw_mmr_change
    And Player.hybrid_mmr SHALL NOT be updated

  Scenario: Custom weights can be configured
    Given config has custom weight for damage_ratio=0.25
    When PIM is calculated
    Then damage_ratio SHALL be weighted at 25% (not default 15%)
```

### AT-006: Backward Compatibility

```gherkin
Feature: Backward Compatibility

  Scenario: Existing TrueSkill fields preserved
    Given player exists with mu=28.5, sigma=4.2
    When match is processed with hybrid MMR enabled
    Then mu and sigma SHALL be updated by TrueSkill
    And mmr property SHALL still return 1000 + 40*mu
    And hybrid_mmr SHALL be updated separately

  Scenario: API maintains backward compatibility
    Given existing client expects mmr field
    When GET /api/players is called
    Then response SHALL include "mmr" field (display MMR)
    And "hybrid_mmr" SHALL be an additional field
```

---

## Performance Criteria

### PC-001: Calculation Speed
- PIM calculation for a match SHALL complete in <100ms

### PC-002: Database Performance
- PerformanceFeatures insertion SHALL not increase match processing by >10%

### PC-003: API Response Time
- Player profile with hybrid MMR SHALL return in <200ms

---

## Quality Metrics

### QM-001: Test Coverage
- PICalculator class SHALL have ≥90% test coverage

### QM-002: PIM Distribution
- After 100+ matches, PIM distribution SHALL approximate normal curve
- Mean PIM SHALL be within [-0.05, +0.05]

### QM-003: Prediction Accuracy
- Team with higher average PIM SHALL win ≥55% of matches
- (Validates that PIM correlates with actual performance)

---

## Sign-off Checklist

- [ ] All AT scenarios pass
- [ ] Performance criteria met
- [ ] Quality metrics achieved
- [ ] API documentation updated
- [ ] Configuration documented
- [ ] Rollback procedure tested (disable hybrid MMR)
