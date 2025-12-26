"""
Unit tests for Performance Impact Calculator (PICalculator).

Tests the rule-based PIM calculation for SPEC-ML-001.
"""
import pytest
import math
from unittest.mock import Mock, MagicMock
from app.services.pi_calculator import PICalculator, MatchAverages, PIMBreakdown


class TestZScoreCalculation:
    """Tests for z-score normalization."""

    def setup_method(self):
        self.calculator = PICalculator()

    def test_z_score_average_is_zero(self):
        """Average value should give z-score of 0."""
        z = self.calculator.calculate_z_score(50, 50, 10)
        assert z == 0.0

    def test_z_score_above_average_is_positive(self):
        """Above average should give positive z-score."""
        z = self.calculator.calculate_z_score(70, 50, 10)
        assert z == 2.0

    def test_z_score_below_average_is_negative(self):
        """Below average should give negative z-score."""
        z = self.calculator.calculate_z_score(30, 50, 10)
        assert z == -2.0

    def test_z_score_handles_zero_std(self):
        """Zero standard deviation should return 0."""
        z = self.calculator.calculate_z_score(70, 50, 0)
        assert z == 0.0

    def test_z_score_handles_negative_std(self):
        """Negative standard deviation should return 0."""
        z = self.calculator.calculate_z_score(70, 50, -5)
        assert z == 0.0


class TestPIMCalculation:
    """Tests for PIM calculation."""

    def setup_method(self):
        self.calculator = PICalculator()
        self.match_averages = MatchAverages()

    def test_pim_null_metrics_returns_zero(self):
        """None metrics should give PIM of 0."""
        pim, breakdown = self.calculator.calculate_pim(None, self.match_averages)
        assert pim == 0.0
        assert breakdown.total == 0.0

    def test_pim_average_performance_near_zero(self):
        """Average performance should give PIM near 0."""
        metrics = MockMetrics(average=True)
        pim, breakdown = self.calculator.calculate_pim(metrics, self.match_averages)
        assert abs(pim) < 0.1

    def test_pim_above_average_is_positive(self):
        """Above average performance should give positive PIM."""
        metrics = MockMetrics(above_average=True)
        pim, breakdown = self.calculator.calculate_pim(metrics, self.match_averages)
        assert pim > 0.1

    def test_pim_below_average_is_negative(self):
        """Below average performance should give negative PIM."""
        metrics = MockMetrics(below_average=True)
        pim, breakdown = self.calculator.calculate_pim(metrics, self.match_averages)
        assert pim < -0.1

    def test_pim_bounded_upper(self):
        """PIM should not exceed +0.5."""
        metrics = MockMetrics(extreme_high=True)
        pim, breakdown = self.calculator.calculate_pim(metrics, self.match_averages)
        assert pim <= 0.5

    def test_pim_bounded_lower(self):
        """PIM should not be below -0.5."""
        metrics = MockMetrics(extreme_low=True)
        pim, breakdown = self.calculator.calculate_pim(metrics, self.match_averages)
        assert pim >= -0.5

    def test_pim_breakdown_categories(self):
        """PIM breakdown should have all categories."""
        metrics = MockMetrics(above_average=True)
        pim, breakdown = self.calculator.calculate_pim(metrics, self.match_averages)

        assert hasattr(breakdown, 'combat')
        assert hasattr(breakdown, 'economic')
        assert hasattr(breakdown, 'team')
        assert hasattr(breakdown, 'efficiency')
        assert hasattr(breakdown, 'total')

    def test_pim_breakdown_to_dict(self):
        """Breakdown to_dict should return proper format."""
        breakdown = PIMBreakdown(
            combat=0.15,
            economic=-0.05,
            team=0.10,
            efficiency=0.02,
            total=0.22
        )
        d = breakdown.to_dict()

        assert "combat" in d
        assert "economic" in d
        assert "team" in d
        assert "efficiency" in d
        assert "total" in d


class TestPIMApplication:
    """Tests for applying PIM to MMR changes."""

    def setup_method(self):
        self.calculator = PICalculator()

    def test_win_good_performance_amplifies_gain(self):
        """Win + good performance = more MMR gained."""
        result = self.calculator.apply_pim_to_mmr_change(50, 0.3)
        assert result == pytest.approx(65)  # 50 * 1.3

    def test_win_poor_performance_reduces_gain(self):
        """Win + poor performance = less MMR gained."""
        result = self.calculator.apply_pim_to_mmr_change(50, -0.3)
        assert result == pytest.approx(35)  # 50 * 0.7

    def test_loss_good_performance_reduces_loss(self):
        """Loss + good performance = less MMR lost."""
        result = self.calculator.apply_pim_to_mmr_change(-50, 0.3)
        assert result == pytest.approx(-35)  # -50 * 0.7

    def test_loss_poor_performance_amplifies_loss(self):
        """Loss + poor performance = more MMR lost."""
        result = self.calculator.apply_pim_to_mmr_change(-50, -0.3)
        assert result == pytest.approx(-65)  # -50 * 1.3

    def test_zero_pim_no_change(self):
        """Zero PIM should not modify MMR change."""
        result_win = self.calculator.apply_pim_to_mmr_change(50, 0.0)
        result_loss = self.calculator.apply_pim_to_mmr_change(-50, 0.0)

        assert result_win == 50
        assert result_loss == -50

    def test_max_pim_modifier(self):
        """Max PIM (+0.5) should give 50% bonus for wins."""
        result = self.calculator.apply_pim_to_mmr_change(100, 0.5)
        assert result == pytest.approx(150)  # 100 * 1.5

    def test_min_pim_modifier(self):
        """Min PIM (-0.5) should give 50% reduction for wins."""
        result = self.calculator.apply_pim_to_mmr_change(100, -0.5)
        assert result == pytest.approx(50)  # 100 * 0.5

    def test_zero_mmr_change(self):
        """Zero MMR change should stay zero regardless of PIM."""
        result = self.calculator.apply_pim_to_mmr_change(0, 0.3)
        assert result == 0


class TestWeightConfiguration:
    """Tests for weight configuration."""

    def test_default_weights_sum_to_one(self):
        """Default weights should sum to 1.0."""
        calculator = PICalculator()
        assert calculator.validate_weights()

    def test_custom_weights_accepted(self):
        """Custom weights should be used when provided."""
        custom_weights = {
            "damage_ratio": 0.5,
            "army_value_ratio": 0.5,
            "combat_score": 0.0,
            "spending_efficiency": 0.0,
            "economic_score": 0.0,
            "resource_advantage": 0.0,
            "team_fight_participation": 0.0,
            "team_fight_damage_ratio": 0.0,
            "overall_impact": 0.0,
            "efficiency_score": 0.0,
        }
        calculator = PICalculator(weights=custom_weights)

        assert calculator.weights["damage_ratio"] == 0.5
        assert calculator.weights["spending_efficiency"] == 0.0

    def test_get_weights_returns_copy(self):
        """get_weights() should return a copy."""
        calculator = PICalculator()
        weights = calculator.get_weights()
        weights["damage_ratio"] = 999

        assert calculator.weights["damage_ratio"] != 999


class TestMatchAverages:
    """Tests for MatchAverages dataclass."""

    def test_default_values(self):
        """MatchAverages should have sensible defaults."""
        avg = MatchAverages()

        assert avg.damage_ratio == 1.0
        assert avg.combat_score == 50.0
        assert avg.spending_efficiency == 0.7
        assert avg.economic_score == 50.0

    def test_std_defaults(self):
        """Standard deviation defaults should be positive."""
        avg = MatchAverages()

        assert avg.damage_ratio_std > 0
        assert avg.combat_score_std > 0


class MockMetrics:
    """
    Mock PlayerMatchMetrics for testing.

    Provides consistent test data for different scenarios.
    """

    def __init__(
        self,
        average: bool = False,
        above_average: bool = False,
        below_average: bool = False,
        extreme_high: bool = False,
        extreme_low: bool = False
    ):
        if extreme_high:
            # Extremely high values (should hit PIM upper bound)
            self.damage_ratio = 5.0
            self.army_value_ratio = 5.0
            self.combat_score = 100
            self.spending_efficiency = 1.0
            self.economic_score = 100
            self.resource_advantage = 100000
            self.team_fight_participation = 1.0
            self.team_fight_damage_ratio = 5.0
            self.overall_impact = 100
            self.efficiency_score = 100
        elif extreme_low:
            # Extremely low values (should hit PIM lower bound)
            self.damage_ratio = 0.0
            self.army_value_ratio = 0.0
            self.combat_score = 0
            self.spending_efficiency = 0.0
            self.economic_score = 0
            self.resource_advantage = -100000
            self.team_fight_participation = 0.0
            self.team_fight_damage_ratio = 0.0
            self.overall_impact = 0
            self.efficiency_score = 0
        elif above_average:
            # Moderately above average
            self.damage_ratio = 1.5
            self.army_value_ratio = 1.5
            self.combat_score = 70
            self.spending_efficiency = 0.85
            self.economic_score = 70
            self.resource_advantage = 5000
            self.team_fight_participation = 0.7
            self.team_fight_damage_ratio = 1.5
            self.overall_impact = 70
            self.efficiency_score = 70
        elif below_average:
            # Moderately below average
            self.damage_ratio = 0.5
            self.army_value_ratio = 0.5
            self.combat_score = 30
            self.spending_efficiency = 0.5
            self.economic_score = 30
            self.resource_advantage = -5000
            self.team_fight_participation = 0.3
            self.team_fight_damage_ratio = 0.5
            self.overall_impact = 30
            self.efficiency_score = 30
        else:  # average
            # Exactly average values
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


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
