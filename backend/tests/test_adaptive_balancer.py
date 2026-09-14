"""
Tests for app.services.adaptive_balancer.MLMetricsBalancer.

Covers two bugs fixed together:
1. Truthiness-fallback bug: fields legitimately at 0.0 (or 0 games) were
   silently replaced by fallback defaults because the code used `x or default`
   instead of `x if x is not None else default`.
2. Inert weights: the `weights` dict accepted by calculate_ml_rating/
   balance_teams only actually honors the "teamwork" key; other keys
   (combat/economic/efficiency/session_mmr) must not be advertised as having
   an effect via `weights_used` in the returned MLTeamSuggestion.
"""
from types import SimpleNamespace

from app.services.adaptive_balancer import MLMetricsBalancer

# calculate_ml_rating's form_adjustment = (impact - NEUTRAL_IMPACT) * 4 * weight,
# so setting avg_overall_impact to this value isolates base_mmr in assertions.
NEUTRAL_IMPACT = 60.0


class TestTruthinessFallbackFix:
    """A legitimate 0.0 value must be used as-is, never replaced by a default."""

    def test_zero_unified_mmr_is_not_replaced(self, db_session, player_factory):
        player = player_factory(
            name="ZeroUnified",
            unified_mmr=0.0,
            mmr=1500.0,
            avg_overall_impact=NEUTRAL_IMPACT,
            total_games=20,
        )
        rating, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert rating == player.unified_mmr

    def test_zero_mmr_used_when_unified_mmr_is_none(self, db_session, player_factory):
        player = player_factory(
            name="ZeroMmrOnly",
            unified_mmr=None,
            mmr=0.0,
            avg_overall_impact=NEUTRAL_IMPACT,
            total_games=20,
        )
        rating, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert rating == player.mmr

    def test_zero_combat_score_is_not_replaced(self, db_session, player_factory):
        player = player_factory(
            name="ZeroCombat",
            unified_mmr=1000.0,
            avg_combat_score=0.0,
            total_games=20,
        )
        _, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert breakdown.combat == 0.0

    def test_zero_economic_score_is_not_replaced(self, db_session, player_factory):
        player = player_factory(
            name="ZeroEconomic",
            unified_mmr=1000.0,
            avg_economic_score=0.0,
            total_games=20,
        )
        _, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert breakdown.economic == 0.0

    def test_zero_efficiency_score_is_not_replaced(self, db_session, player_factory):
        player = player_factory(
            name="ZeroEfficiency",
            unified_mmr=1000.0,
            avg_efficiency_score=0.0,
            total_games=20,
        )
        _, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert breakdown.efficiency == 0.0

    def test_zero_overall_impact_is_not_replaced(self, db_session, player_factory):
        player = player_factory(
            name="ZeroImpact",
            unified_mmr=1000.0,
            avg_overall_impact=0.0,
            total_games=20,
        )
        rating, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert breakdown.teamwork == 0.0
        expected_form_adjustment = (player.avg_overall_impact - NEUTRAL_IMPACT) * 4.0
        assert rating == player.unified_mmr + expected_form_adjustment

    def test_zero_total_games_treated_as_new_player(self, db_session, player_factory):
        player = player_factory(
            name="ZeroGames",
            unified_mmr=1000.0,
            mmr=1750.0,
            total_games=0,
        )
        _, breakdown = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        assert breakdown.total_games == 0

    def test_none_fields_still_use_documented_defaults(self, db_session):
        """Sanity check: genuinely missing (None) data still falls back to the
        documented defaults -- only real 0.0 values must bypass the fallback.

        Note: the Player ORM columns for avg_combat_score/avg_economic_score/
        avg_efficiency_score/avg_overall_impact are NOT NULL with a DB-side
        default of 0.0, so they can never actually be None once persisted
        (verified: constructing a Player with these fields set to None and
        flushing yields 0.0, not None). A plain stand-in object is used here
        so we can exercise calculate_ml_rating's None-handling directly.
        """
        fake_player = SimpleNamespace(
            id=1,
            name="AllNone",
            unified_mmr=None,
            mmr=1800.0,
            recency_weighted_mmr=None,
            session_weighted_mmr=None,
            avg_combat_score=None,
            avg_economic_score=None,
            avg_efficiency_score=None,
            avg_overall_impact=None,
            total_games=20,
        )
        _, breakdown = MLMetricsBalancer.calculate_ml_rating(
            fake_player, {"teamwork": 1.0}, db_session
        )
        assert breakdown.combat == 24.0
        assert breakdown.economic == 60.0
        assert breakdown.efficiency == 55.0
        assert breakdown.teamwork == 60.0


class TestInertWeights:
    """Only 'teamwork' affects calculate_ml_rating's output; other advertised
    weight keys (combat/economic/efficiency/session_mmr) must not be reported
    back to callers as if they had an effect."""

    def test_teamwork_weight_changes_output(self, db_session, player_factory):
        player = player_factory(
            name="TeamworkSensitive",
            unified_mmr=1000.0,
            avg_overall_impact=80.0,
            total_games=20,
        )
        rating_low, _ = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 0.0}, db_session
        )
        rating_high, _ = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 2.0}, db_session
        )
        assert rating_low != rating_high

    def test_combat_economic_efficiency_weights_do_not_change_output(
        self, db_session, player_factory
    ):
        player = player_factory(
            name="InertWeightCheck",
            unified_mmr=1000.0,
            avg_combat_score=50.0,
            avg_economic_score=50.0,
            avg_efficiency_score=50.0,
            avg_overall_impact=70.0,
            total_games=20,
        )
        baseline, _ = MLMetricsBalancer.calculate_ml_rating(
            player, {"teamwork": 1.0}, db_session
        )
        perturbed, _ = MLMetricsBalancer.calculate_ml_rating(
            player,
            {
                "teamwork": 1.0,
                "combat": 5.0,
                "economic": 5.0,
                "efficiency": 5.0,
                "session_mmr": 5.0,
            },
            db_session,
        )
        assert baseline == perturbed

    def test_weights_used_only_advertises_active_keys(self, db_session, player_factory):
        players = [
            player_factory(name=f"WU{i}", unified_mmr=1000.0, total_games=20)
            for i in range(4)
        ]
        ids = [p.id for p in players]

        manual_weights = {
            "teamwork": 1.0,
            "combat": 0.5,
            "economic": 0.5,
            "efficiency": 0.5,
            "session_mmr": 0.5,
        }
        suggestions = MLMetricsBalancer.balance_teams(
            ids,
            db_session,
            use_adaptive_weights=False,
            manual_weights=manual_weights,
        )
        assert len(suggestions) > 0
        for suggestion in suggestions:
            assert set(suggestion.weights_used.keys()) == {"teamwork"}
            assert suggestion.weights_used["teamwork"] == 1.0

    def test_active_weight_keys_is_exactly_teamwork(self):
        assert MLMetricsBalancer.ACTIVE_WEIGHT_KEYS == frozenset({"teamwork"})
