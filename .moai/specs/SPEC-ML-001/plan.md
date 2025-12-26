# SPEC-ML-001: Implementation Plan

---
spec_id: SPEC-ML-001
version: 1.0.0
status: draft
created: 2025-12-06
---

## Executive Summary

This plan implements the ML-Enhanced Hybrid MMR System in parallel with SPEC-REFACTOR-001. The approach is **incremental**: start with a rule-based formula, collect data, then evolve to ML.

**Total Estimated Effort**: 3-4 development days
**Recommended Approach**: TDD (Red-Green-Refactor)

---

## Phase 1: Database & Feature Store (Priority: BLOCKING)

**Estimated Effort**: 0.5 days
**Dependencies**: None

### 1.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| ML-T01 | Create database migration for `performance_features` table | `alembic/versions/` | 30 min |
| ML-T02 | Create `PerformanceFeatures` SQLAlchemy model | `app/models.py` | 20 min |
| ML-T03 | Create `PIMWeightConfig` model for versioned weights | `app/models.py` | 15 min |
| ML-T04 | Add `hybrid_mmr` field to `Player` model | `app/models.py` | 10 min |
| ML-T05 | Create weight configuration YAML | `config/pim_config.yaml` | 15 min |

### 1.2 Implementation Details

#### ML-T01: Database Migration

```python
# alembic/versions/xxx_add_performance_features.py
def upgrade():
    op.create_table(
        'performance_features',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_player_id', sa.Integer(), sa.ForeignKey('match_player.id')),

        # Z-score normalized features
        sa.Column('damage_ratio_z', sa.Float(), default=0.0),
        sa.Column('army_value_ratio_z', sa.Float(), default=0.0),
        sa.Column('combat_score_z', sa.Float(), default=0.0),
        sa.Column('spending_efficiency_z', sa.Float(), default=0.0),
        sa.Column('economic_score_z', sa.Float(), default=0.0),
        sa.Column('resource_advantage_z', sa.Float(), default=0.0),
        sa.Column('team_fight_participation_z', sa.Float(), default=0.0),
        sa.Column('team_fight_damage_ratio_z', sa.Float(), default=0.0),
        sa.Column('overall_impact_z', sa.Float(), default=0.0),
        sa.Column('efficiency_score_z', sa.Float(), default=0.0),

        # Calculated PIM
        sa.Column('pim', sa.Float(), default=0.0),
        sa.Column('pim_version', sa.String(20), default='rule_v1'),

        # MMR tracking
        sa.Column('raw_mmr_change', sa.Float()),
        sa.Column('hybrid_mmr_change', sa.Float()),

        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    )

    op.create_index('idx_perf_features_match_player', 'performance_features', ['match_player_id'])

    # Add hybrid_mmr to Player
    op.add_column('player', sa.Column('hybrid_mmr', sa.Float(), default=2000.0))

def downgrade():
    op.drop_table('performance_features')
    op.drop_column('player', 'hybrid_mmr')
```

### 1.3 Validation

```bash
# Run migration
cd backend && alembic upgrade head

# Verify table exists
sqlite3 data/sc2mmr.db ".schema performance_features"

# Verify Player has hybrid_mmr
sqlite3 data/sc2mmr.db ".schema player" | grep hybrid_mmr
```

---

## Phase 2: PIM Calculator Service (Priority: HIGH)

**Estimated Effort**: 1 day
**Dependencies**: Phase 1 complete

### 2.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| ML-T10 | Create `PICalculator` class with weighted formula | `app/services/pi_calculator.py` | 2 hours |
| ML-T11 | Implement z-score normalization helper | `app/services/pi_calculator.py` | 30 min |
| ML-T12 | Implement match average calculation | `app/services/pi_calculator.py` | 30 min |
| ML-T13 | Add PIM bounds and edge case handling | `app/services/pi_calculator.py` | 30 min |
| ML-T14 | Write unit tests for PIM calculator | `tests/test_pi_calculator.py` | 1 hour |
| ML-T15 | Load weights from YAML configuration | `app/services/pi_calculator.py` | 30 min |

### 2.2 Implementation Details

#### ML-T10: PICalculator Class

```python
# app/services/pi_calculator.py
"""
Performance Impact Calculator for Hybrid MMR System.

Calculates Performance Impact Modifier (PIM) based on in-game metrics.
PIM adjusts MMR gain/loss: actual_change = base_change × (1 + PIM)

Design:
- Phase 1: Rule-based weighted formula (this implementation)
- Phase 2+: ML model can replace calculate_pim() method
"""
import math
from typing import Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import MatchPlayer, PlayerMatchMetrics, Match
from app.config import settings


@dataclass
class MatchAverages:
    """Average metrics across all players in a match."""
    damage_ratio: float = 1.0
    damage_ratio_std: float = 0.5
    army_value_ratio: float = 1.0
    army_value_ratio_std: float = 0.5
    combat_score: float = 50.0
    combat_score_std: float = 20.0
    spending_efficiency: float = 0.7
    spending_efficiency_std: float = 0.15
    economic_score: float = 50.0
    economic_score_std: float = 20.0
    resource_advantage: float = 0.0  # Normalized to match average
    resource_advantage_std: float = 10000.0
    team_fight_participation: float = 0.5
    team_fight_participation_std: float = 0.2
    team_fight_damage_ratio: float = 1.0
    team_fight_damage_ratio_std: float = 0.5
    overall_impact: float = 50.0
    overall_impact_std: float = 20.0
    efficiency_score: float = 50.0
    efficiency_score_std: float = 20.0


@dataclass
class PIMBreakdown:
    """Breakdown of PIM by category."""
    combat: float = 0.0
    economic: float = 0.0
    team: float = 0.0
    efficiency: float = 0.0
    total: float = 0.0


class PICalculator:
    """
    Performance Impact Calculator.

    Calculates PIM (Performance Impact Modifier) for each player in a match.
    """

    # Default weights (can be overridden by config)
    DEFAULT_WEIGHTS = {
        # Combat (40%)
        "damage_ratio": 0.15,
        "army_value_ratio": 0.15,
        "combat_score": 0.10,
        # Economic (25%)
        "spending_efficiency": 0.10,
        "economic_score": 0.10,
        "resource_advantage": 0.05,
        # Team (25%)
        "team_fight_participation": 0.10,
        "team_fight_damage_ratio": 0.10,
        "overall_impact": 0.05,
        # Efficiency (10%)
        "efficiency_score": 0.10,
    }

    # Bounds for PIM
    PIM_MIN = -0.5
    PIM_MAX = 0.5

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize with optional custom weights."""
        self.weights = weights or self.DEFAULT_WEIGHTS

    def calculate_match_averages(
        self, db: Session, match_id: int
    ) -> MatchAverages:
        """
        Calculate average metrics for all players in a match.

        Args:
            db: Database session
            match_id: Match ID

        Returns:
            MatchAverages with mean and std for each metric
        """
        # Get all match players with metrics
        match_players = db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_id
        ).all()

        if not match_players:
            return MatchAverages()

        # Collect metrics from all players
        metrics_list = []
        for mp in match_players:
            if mp.metrics:
                metrics_list.append(mp.metrics)

        if not metrics_list:
            return MatchAverages()

        # Calculate averages and std devs
        def avg_and_std(values):
            if not values:
                return 0.0, 1.0
            mean = sum(values) / len(values)
            if len(values) < 2:
                return mean, 1.0
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(variance) if variance > 0 else 1.0
            return mean, std

        averages = MatchAverages()

        # Calculate for each metric
        for metric_name in self.DEFAULT_WEIGHTS.keys():
            values = [
                getattr(m, metric_name, 0) or 0
                for m in metrics_list
            ]
            mean, std = avg_and_std(values)
            setattr(averages, metric_name, mean)
            setattr(averages, f"{metric_name}_std", max(std, 0.001))  # Prevent div by 0

        return averages

    def calculate_z_score(
        self, value: float, mean: float, std: float
    ) -> float:
        """
        Calculate z-score (standard score).

        Args:
            value: The metric value
            mean: Population mean
            std: Population standard deviation

        Returns:
            Z-score (how many std devs from mean)
        """
        if std <= 0:
            return 0.0
        return (value - mean) / std

    def calculate_pim(
        self,
        metrics: PlayerMatchMetrics,
        match_averages: MatchAverages
    ) -> tuple[float, PIMBreakdown]:
        """
        Calculate Performance Impact Modifier.

        Args:
            metrics: Player's match metrics
            match_averages: Average metrics for the match

        Returns:
            Tuple of (pim, breakdown)
            - pim: Float in range [-0.5, +0.5]
            - breakdown: PIMBreakdown with category scores
        """
        if not metrics:
            return 0.0, PIMBreakdown()

        z_scores = {}
        breakdown = PIMBreakdown()

        # Calculate z-scores for each metric
        for metric_name, weight in self.weights.items():
            value = getattr(metrics, metric_name, 0) or 0
            mean = getattr(match_averages, metric_name, 0)
            std = getattr(match_averages, f"{metric_name}_std", 1)

            z_scores[metric_name] = self.calculate_z_score(value, mean, std)

        # Calculate category breakdowns
        breakdown.combat = (
            z_scores.get("damage_ratio", 0) * self.weights.get("damage_ratio", 0) +
            z_scores.get("army_value_ratio", 0) * self.weights.get("army_value_ratio", 0) +
            z_scores.get("combat_score", 0) * self.weights.get("combat_score", 0)
        )
        breakdown.economic = (
            z_scores.get("spending_efficiency", 0) * self.weights.get("spending_efficiency", 0) +
            z_scores.get("economic_score", 0) * self.weights.get("economic_score", 0) +
            z_scores.get("resource_advantage", 0) * self.weights.get("resource_advantage", 0)
        )
        breakdown.team = (
            z_scores.get("team_fight_participation", 0) * self.weights.get("team_fight_participation", 0) +
            z_scores.get("team_fight_damage_ratio", 0) * self.weights.get("team_fight_damage_ratio", 0) +
            z_scores.get("overall_impact", 0) * self.weights.get("overall_impact", 0)
        )
        breakdown.efficiency = (
            z_scores.get("efficiency_score", 0) * self.weights.get("efficiency_score", 0)
        )

        # Raw PIM (sum of weighted z-scores)
        raw_pim = breakdown.combat + breakdown.economic + breakdown.team + breakdown.efficiency

        # Bound using tanh to [-0.5, +0.5]
        bounded_pim = self.PIM_MAX * math.tanh(raw_pim)

        breakdown.total = bounded_pim

        return bounded_pim, breakdown

    def apply_pim_to_mmr_change(
        self, base_change: float, pim: float
    ) -> float:
        """
        Apply PIM to modify MMR change.

        Args:
            base_change: Raw MMR change from TrueSkill
            pim: Performance Impact Modifier [-0.5, +0.5]

        Returns:
            Modified MMR change

        Examples:
            Win (+50) with great performance (PIM=+0.3): 50 * 1.3 = +65
            Win (+50) with poor performance (PIM=-0.3): 50 * 0.7 = +35
            Loss (-50) with great performance (PIM=+0.3): -50 * 0.7 = -35
            Loss (-50) with poor performance (PIM=-0.3): -50 * 1.3 = -65
        """
        modifier = 1.0 + pim  # Range: [0.5, 1.5]

        if base_change >= 0:
            # Won: good performance = more gain
            return base_change * modifier
        else:
            # Lost: good performance = less loss (invert modifier)
            return base_change * (2.0 - modifier)
```

#### ML-T14: Unit Tests

```python
# tests/test_pi_calculator.py
import pytest
from app.services.pi_calculator import PICalculator, MatchAverages, PIMBreakdown
from app.models import PlayerMatchMetrics


class TestPICalculator:
    """Tests for Performance Impact Calculator."""

    def setup_method(self):
        self.calculator = PICalculator()

    def test_z_score_average(self):
        """Average value should give z-score of 0."""
        z = self.calculator.calculate_z_score(50, 50, 10)
        assert z == 0.0

    def test_z_score_above_average(self):
        """Above average should give positive z-score."""
        z = self.calculator.calculate_z_score(70, 50, 10)
        assert z == 2.0

    def test_z_score_below_average(self):
        """Below average should give negative z-score."""
        z = self.calculator.calculate_z_score(30, 50, 10)
        assert z == -2.0

    def test_pim_bounds_upper(self):
        """PIM should not exceed +0.5."""
        # Create metrics with extremely high values
        metrics = MockMetrics(all_high=True)
        averages = MatchAverages()

        pim, _ = self.calculator.calculate_pim(metrics, averages)
        assert pim <= 0.5

    def test_pim_bounds_lower(self):
        """PIM should not be below -0.5."""
        metrics = MockMetrics(all_low=True)
        averages = MatchAverages()

        pim, _ = self.calculator.calculate_pim(metrics, averages)
        assert pim >= -0.5

    def test_pim_average_is_zero(self):
        """Average performance should give PIM near 0."""
        metrics = MockMetrics(all_average=True)
        averages = MatchAverages()

        pim, _ = self.calculator.calculate_pim(metrics, averages)
        assert abs(pim) < 0.1

    def test_apply_pim_win_good_performance(self):
        """Win + good performance = more MMR gained."""
        result = self.calculator.apply_pim_to_mmr_change(50, 0.3)
        assert result == 65  # 50 * 1.3

    def test_apply_pim_win_bad_performance(self):
        """Win + bad performance = less MMR gained."""
        result = self.calculator.apply_pim_to_mmr_change(50, -0.3)
        assert result == 35  # 50 * 0.7

    def test_apply_pim_loss_good_performance(self):
        """Loss + good performance = less MMR lost."""
        result = self.calculator.apply_pim_to_mmr_change(-50, 0.3)
        assert result == -35  # -50 * 0.7

    def test_apply_pim_loss_bad_performance(self):
        """Loss + bad performance = more MMR lost."""
        result = self.calculator.apply_pim_to_mmr_change(-50, -0.3)
        assert result == -65  # -50 * 1.3


class MockMetrics:
    """Mock PlayerMatchMetrics for testing."""

    def __init__(self, all_high=False, all_low=False, all_average=False):
        if all_high:
            self.damage_ratio = 3.0
            self.army_value_ratio = 3.0
            self.combat_score = 100
            self.spending_efficiency = 1.0
            self.economic_score = 100
            self.resource_advantage = 50000
            self.team_fight_participation = 1.0
            self.team_fight_damage_ratio = 3.0
            self.overall_impact = 100
            self.efficiency_score = 100
        elif all_low:
            self.damage_ratio = 0.1
            self.army_value_ratio = 0.1
            self.combat_score = 0
            self.spending_efficiency = 0.1
            self.economic_score = 0
            self.resource_advantage = -50000
            self.team_fight_participation = 0.0
            self.team_fight_damage_ratio = 0.1
            self.overall_impact = 0
            self.efficiency_score = 0
        else:  # average
            self.damage_ratio = 1.0
            self.army_value_ratio = 1.0
            self.combat_score = 50
            self.spending_efficiency = 0.7
            self.economic_score = 50
            self.resource_advantage = 0
            self.team_fight_participation = 0.5
            self.team_fight_damage_ratio = 1.0
            self.overall_impact = 50
            self.efficiency_score = 50
```

### 2.3 Validation

```bash
# Run PIM calculator tests
cd backend && pytest tests/test_pi_calculator.py -v

# Expected: All tests pass
```

---

## Phase 3: Rating System Integration (Priority: HIGH)

**Estimated Effort**: 1 day
**Dependencies**: Phase 2 complete

### 3.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| ML-T20 | Modify `update_ratings_from_match()` to calculate PIM | `app/rating_system.py` | 1 hour |
| ML-T21 | Store `PerformanceFeatures` after each match | `app/rating_system.py` | 30 min |
| ML-T22 | Update `Player.hybrid_mmr` after each match | `app/rating_system.py` | 30 min |
| ML-T23 | Add hybrid MMR toggle in config | `app/config.py` | 15 min |
| ML-T24 | Write integration tests | `tests/test_rating_system.py` | 1 hour |
| ML-T25 | Backfill `hybrid_mmr` for existing players | `scripts/backfill_hybrid_mmr.py` | 30 min |

### 3.2 Key Integration Points

```python
# In rating_system.py update_ratings_from_match()

# After TrueSkill calculation:
if settings.hybrid_mmr_enabled:
    calculator = PICalculator()
    match_averages = calculator.calculate_match_averages(db, match.id)

    for match_player in match_players:
        # Calculate PIM
        pim, breakdown = calculator.calculate_pim(
            match_player.metrics,
            match_averages
        )

        # Calculate raw and hybrid MMR changes
        raw_change = RatingSystem.calculate_display_mmr(new_mu) - \
                     RatingSystem.calculate_display_mmr(old_mu)
        hybrid_change = calculator.apply_pim_to_mmr_change(raw_change, pim)

        # Store features
        features = PerformanceFeatures(
            match_player_id=match_player.id,
            pim=pim,
            raw_mmr_change=raw_change,
            hybrid_mmr_change=hybrid_change,
            # ... z-scores
        )
        db.add(features)

        # Update player's hybrid MMR
        player.hybrid_mmr += hybrid_change
```

---

## Phase 4: API Updates (Priority: MEDIUM)

**Estimated Effort**: 0.5 days
**Dependencies**: Phase 3 complete

### 4.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| ML-T30 | Add `hybrid_mmr`, `avg_pim` to Player response | `app/api/players.py` | 30 min |
| ML-T31 | Add `pim`, `pim_breakdown` to MatchPlayer response | `app/api/replays.py` | 30 min |
| ML-T32 | Add PIM analytics endpoint | `app/api/analytics.py` | 1 hour |
| ML-T33 | Update OpenAPI schema documentation | `app/main.py` | 15 min |

### 4.2 New Endpoint

```python
# GET /api/analytics/pim-distribution
# Returns distribution of PIM values for analysis

# GET /api/analytics/feature-correlations
# Returns correlation of features with win rate (for weight tuning)

# GET /api/players/{id}/pim-history
# Returns PIM history over time for a player
```

---

## Phase 5: Validation & Tuning (Priority: HIGH)

**Estimated Effort**: 0.5 days
**Dependencies**: Phase 4 complete

### 5.1 Tasks

| Task ID | Description | File(s) | Effort |
|---------|-------------|---------|--------|
| ML-T40 | Analyze PIM distribution across matches | Analysis script | 1 hour |
| ML-T41 | Validate prediction accuracy improvement | Analysis script | 1 hour |
| ML-T42 | Tune weights based on win correlation | `config/pim_config.yaml` | 1 hour |
| ML-T43 | Document final weights and rationale | SPEC update | 30 min |

---

## Execution Checklist

### Phase 1: Database
- [ ] Create migration for `performance_features` table
- [ ] Add `PerformanceFeatures` model
- [ ] Add `hybrid_mmr` to Player model
- [ ] Create weight config YAML
- [ ] Run migration successfully

### Phase 2: PIM Calculator
- [ ] Implement `PICalculator` class
- [ ] Implement z-score normalization
- [ ] Implement match average calculation
- [ ] Add bounds and edge cases
- [ ] Write unit tests (all pass)

### Phase 3: Integration
- [ ] Modify `update_ratings_from_match()`
- [ ] Store `PerformanceFeatures`
- [ ] Update `Player.hybrid_mmr`
- [ ] Add config toggle
- [ ] Write integration tests (all pass)

### Phase 4: API
- [ ] Update Player response schema
- [ ] Update MatchPlayer response schema
- [ ] Add analytics endpoints
- [ ] Update OpenAPI docs

### Phase 5: Validation
- [ ] Analyze PIM distribution
- [ ] Measure prediction accuracy
- [ ] Tune weights
- [ ] Document findings

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Unit tests | 100% passing |
| Integration tests | 100% passing |
| PIM distribution | Normal, centered ~0 |
| Prediction accuracy | ≥60% (baseline: ~55%) |
| API response time | <200ms for player profile |

---

## Parallel Execution with SPEC-REFACTOR-001

These can run in parallel:

| Day | SPEC-REFACTOR-001 | SPEC-ML-001 |
|-----|-------------------|-------------|
| 1 | Phase 2: Service Layer | Phase 1: Database |
| 2 | Phase 2: Service Layer (cont.) | Phase 2: PIM Calculator |
| 3 | Phase 3: TypeScript | Phase 3: Integration |
| 4 | Phase 3: TypeScript (cont.) | Phase 4-5: API & Validation |

No blocking dependencies between the two SPECs until Phase 3 of ML, which needs the service layer patterns from REFACTOR.
