"""
Unit tests for PerformanceRatingAdjuster.calculate_performance_multiplier.

Bug under test: on a LOSS, an above-average individual performance is supposed
to cushion (reduce the magnitude of) the rating loss, and a below-average
performance should not be cushioned (or should be penalized further). The
multiplier must therefore be a non-increasing function of performance_score
on a loss (higher performance -> smaller-magnitude loss), mirroring the
non-decreasing behavior already correct on a win.

These tests operate directly on calculate_performance_multiplier with simple
stand-in objects exposing only the `overall_impact` attribute it reads -- no
DB session or real PlayerMatchMetrics rows are needed.
"""
from types import SimpleNamespace

import pytest

from app.performance_rating import PerformanceRatingAdjuster


def metrics(overall_impact):
    return SimpleNamespace(overall_impact=overall_impact)


def make_inputs(player_impact, team_avg=100.0, opponent_avg=100.0, n_team=3, n_opp=3):
    """Build (player_metrics, team_metrics, opponent_metrics) where the team/opponent
    lists average to team_avg/opponent_avg exactly, and the player's own impact is
    player_impact (player is included in team_metrics, matching production usage in
    adjust_ratings_for_match)."""
    player = metrics(player_impact)
    teammate_total_to_reach_team_avg = team_avg * n_team - player_impact
    teammate_padding_value = (
        teammate_total_to_reach_team_avg / (n_team - 1) if n_team > 1 else 0.0
    )
    team_list = [player] + [metrics(teammate_padding_value) for _ in range(n_team - 1)]

    opponent_list = [metrics(opponent_avg) for _ in range(n_opp)]
    return player, team_list, opponent_list


def multiplier_for(player_impact, won, team_avg=100.0, opponent_avg=100.0):
    player, team_list, opponent_list = make_inputs(player_impact, team_avg, opponent_avg)
    return PerformanceRatingAdjuster.calculate_performance_multiplier(
        player, team_list, opponent_list, won
    )


PERFORMANCE_SWEEP = [40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 200.0]


class TestLossCushioning:
    """Core bug: on a loss, better individual performance must shrink the loss,
    never grow it."""

    def test_above_average_loss_multiplier_is_at_most_one(self):
        """An above-average performer on a loss must get a multiplier <= 1.0
        (never > 1.0), since the mu delta is negative and multiplying a negative
        number by something > 1.0 makes the loss LARGER, not smaller."""
        mult = multiplier_for(player_impact=150.0, won=False)
        assert mult <= 1.0, (
            f"Above-average loss multiplier {mult} > 1.0 would make the loss "
            "bigger, not cushion it"
        )

    def test_below_average_loss_multiplier_is_at_least_one(self):
        """A below-average performer on a loss must get a multiplier >= 1.0
        (a bigger loss), never a cushion."""
        mult = multiplier_for(player_impact=50.0, won=False)
        assert mult >= 1.0, (
            f"Below-average loss multiplier {mult} < 1.0 would shrink the loss "
            "for the worse performer -- backwards"
        )

    def test_average_loss_multiplier_is_one(self):
        """At exactly the team average (performance_score == 1.0), the loss is
        neither cushioned nor amplified."""
        mult = multiplier_for(player_impact=100.0, won=False)
        assert mult == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "lo,hi",
        list(zip(PERFORMANCE_SWEEP, PERFORMANCE_SWEEP[1:])),
    )
    def test_loss_multiplier_non_increasing_as_performance_rises(self, lo, hi):
        """Sweeping performance from low to high on a loss, the multiplier must
        never increase -- higher performance can only cushion (shrink) or leave
        unchanged the magnitude of the loss, never amplify it further."""
        mult_lo = multiplier_for(player_impact=lo, won=False)
        mult_hi = multiplier_for(player_impact=hi, won=False)
        assert mult_hi <= mult_lo + 1e-9, (
            f"multiplier at higher performance ({hi} -> {mult_hi}) exceeds "
            f"multiplier at lower performance ({lo} -> {mult_lo}) on a loss"
        )

    def test_loss_magnitude_non_increasing_end_to_end(self):
        """Concrete numeric check: apply the multiplier to a fixed negative mu
        delta and confirm the resulting loss magnitude shrinks (or stays flat)
        as performance improves, never grows."""
        base_delta = -2.0  # a representative TrueSkill loss
        magnitudes = []
        for score in PERFORMANCE_SWEEP:
            mult = multiplier_for(player_impact=score, won=False)
            adjusted_delta = base_delta * mult
            assert adjusted_delta <= 0.0, "a loss must never flip into a net gain"
            magnitudes.append(abs(adjusted_delta))
        assert all(
            magnitudes[i + 1] <= magnitudes[i] + 1e-9
            for i in range(len(magnitudes) - 1)
        ), f"loss magnitudes were not non-increasing: {magnitudes}"


class TestWinAmplification:
    """The win case is not the reported bug; these tests confirm it already
    behaves correctly and guard against the loss-case fix breaking it."""

    def test_above_average_win_multiplier_is_at_least_one(self):
        mult = multiplier_for(player_impact=150.0, won=True)
        assert mult >= 1.0

    def test_below_average_win_multiplier_is_at_most_one(self):
        mult = multiplier_for(player_impact=50.0, won=True)
        assert mult <= 1.0

    def test_average_win_multiplier_is_one(self):
        mult = multiplier_for(player_impact=100.0, won=True)
        assert mult == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "lo,hi",
        list(zip(PERFORMANCE_SWEEP, PERFORMANCE_SWEEP[1:])),
    )
    def test_win_multiplier_non_decreasing_as_performance_rises(self, lo, hi):
        mult_lo = multiplier_for(player_impact=lo, won=True)
        mult_hi = multiplier_for(player_impact=hi, won=True)
        assert mult_hi >= mult_lo - 1e-9, (
            f"multiplier at higher performance ({hi} -> {mult_hi}) is below "
            f"multiplier at lower performance ({lo} -> {mult_lo}) on a win"
        )

    def test_win_gain_non_decreasing_end_to_end(self):
        base_delta = 2.0
        gains = []
        for score in PERFORMANCE_SWEEP:
            mult = multiplier_for(player_impact=score, won=True)
            adjusted_delta = base_delta * mult
            assert adjusted_delta >= 0.0, "a win must never flip into a net loss"
            gains.append(adjusted_delta)
        assert all(
            gains[i + 1] >= gains[i] - 1e-9 for i in range(len(gains) - 1)
        ), f"win gains were not non-decreasing: {gains}"


class TestMultiplierNeverFlipsSign:
    """The multiplier itself must always stay strictly positive so it can never
    turn a loss into a gain (or vice versa) on its own."""

    @pytest.mark.parametrize("score", [1.0, 10.0, 50.0, 100.0, 300.0, 1000.0])
    @pytest.mark.parametrize("won", [True, False])
    def test_multiplier_bounds_stay_positive(self, won, score):
        mult = multiplier_for(player_impact=score, won=won)
        assert PerformanceRatingAdjuster.MIN_PERFORMANCE_MULTIPLIER <= mult
        assert mult <= PerformanceRatingAdjuster.MAX_PERFORMANCE_MULTIPLIER
        assert mult > 0.0
