"""
Tests for the composite balance objective and balance prediction capture.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.balancer import (
    DEFAULT_COMPOSITE_WEIGHTS,
    PlayerInfo,
    TeamBalancer,
)
from app.models import BalancePrediction, GameMode, Match, MatchPlayer, Race
from app.services.balance_capture import BalancePredictionService


def make_player(pid: int, mmr: float = 2000.0, mu: float = 25.0, sigma: float = 4.0, **kw):
    return PlayerInfo(
        id=pid,
        name=f"P{pid}",
        mu=mu,
        sigma=sigma,
        mmr=mmr,
        overall_impact=kw.get("overall_impact", 60.0),
        total_games=kw.get("total_games", 30),
        aggression_score=kw.get("aggression_score", 50.0),
        avg_combat_score=kw.get("avg_combat_score", 25.0),
        economic_score=kw.get("economic_score", 60.0),
        efficiency_score=kw.get("efficiency_score", 55.0),
    )


class TestCompositeScore:
    def test_even_match_beats_lopsided(self):
        even = TeamBalancer.compute_composite_score(
            win_probability=0.5,
            match_quality=0.8,
            skill_spread_diff=0.0,
            component_imbalance=0.0,
            synergy_imbalance=0.0,
        )
        lopsided = TeamBalancer.compute_composite_score(
            win_probability=0.85,
            match_quality=0.8,
            skill_spread_diff=0.0,
            component_imbalance=0.0,
            synergy_imbalance=0.0,
        )
        assert even > lopsided

    def test_spread_penalty_reduces_score(self):
        flat = TeamBalancer.compute_composite_score(
            win_probability=0.5,
            match_quality=0.8,
            skill_spread_diff=0.0,
            component_imbalance=0.0,
            synergy_imbalance=0.0,
        )
        spread = TeamBalancer.compute_composite_score(
            win_probability=0.5,
            match_quality=0.8,
            skill_spread_diff=300.0,
            component_imbalance=0.0,
            synergy_imbalance=0.0,
        )
        assert spread < flat

    def test_ml_weight_folds_into_closeness_when_unavailable(self):
        # With no ML prob, a perfect 50/50 should still be able to reach the
        # same weight mass as with an ML prob of exactly 0.5
        without_ml = TeamBalancer.compute_composite_score(
            win_probability=0.5,
            match_quality=1.0,
            skill_spread_diff=0.0,
            component_imbalance=0.0,
            synergy_imbalance=0.0,
        )
        with_ml = TeamBalancer.compute_composite_score(
            win_probability=0.5,
            match_quality=1.0,
            skill_spread_diff=0.0,
            component_imbalance=0.0,
            synergy_imbalance=0.0,
            ml_win_probability=0.5,
        )
        assert without_ml == pytest.approx(with_ml)
        # Max achievable = sum of positive weights (closeness+quality+ml)
        positive_mass = (
            DEFAULT_COMPOSITE_WEIGHTS["closeness"]
            + DEFAULT_COMPOSITE_WEIGHTS["quality"]
            + DEFAULT_COMPOSITE_WEIGHTS["ml_closeness"]
        )
        assert without_ml == pytest.approx(positive_mass)

    def test_score_clamped_to_unit_interval(self):
        score = TeamBalancer.compute_composite_score(
            win_probability=0.99,
            match_quality=0.0,
            skill_spread_diff=1000.0,
            component_imbalance=1.0,
            synergy_imbalance=100.0,
        )
        assert 0.0 <= score <= 1.0


class TestSpreadAndComponents:
    def test_skill_spread_detects_smurf_beginner_stack(self):
        # Equal sums: (2600 + 1400) vs (2000 + 2000)
        team_a = [make_player(1, 2600), make_player(2, 1400)]
        team_b = [make_player(3, 2000), make_player(4, 2000)]
        assert TeamBalancer.calculate_skill_spread_diff(team_a, team_b) == 600.0

    def test_component_imbalance_zero_for_identical_profiles(self):
        t1 = [make_player(1), make_player(2)]
        t2 = [make_player(3), make_player(4)]
        assert TeamBalancer.calculate_component_imbalance(t1, t2) == 0.0

    def test_component_imbalance_detects_profile_split(self):
        t1 = [make_player(1, avg_combat_score=45.0), make_player(2, avg_combat_score=45.0)]
        t2 = [make_player(3, avg_combat_score=15.0), make_player(4, avg_combat_score=15.0)]
        assert TeamBalancer.calculate_component_imbalance(t1, t2) > 0.0


class TestWinProbability:
    def test_includes_beta_softening(self):
        # A modest mu gap with tiny sigma should NOT produce a near-certain
        # probability once per-player performance variance (beta) is included
        strong = [make_player(1, mu=27.0, sigma=1.0), make_player(2, mu=27.0, sigma=1.0)]
        weak = [make_player(3, mu=25.0, sigma=1.0), make_player(4, mu=25.0, sigma=1.0)]
        p = TeamBalancer.calculate_win_probability(strong, weak)
        assert 0.5 < p < 0.75

    def test_symmetric(self):
        t1 = [make_player(1, mu=26.0), make_player(2, mu=24.0)]
        t2 = [make_player(3, mu=25.0), make_player(4, mu=25.0)]
        p12 = TeamBalancer.calculate_win_probability(t1, t2)
        p21 = TeamBalancer.calculate_win_probability(t2, t1)
        assert p12 + p21 == pytest.approx(1.0)


class TestCompositeObjectiveRanking:
    def test_composite_sort_and_fields_populated(self):
        players = [
            make_player(1, 2600, mu=33.0),
            make_player(2, 1400, mu=21.0),
            make_player(3, 2100, mu=28.0),
            make_player(4, 1900, mu=26.0),
        ]
        suggestions = TeamBalancer.generate_team_suggestions(
            players, top_n=3, objective="composite"
        )
        assert len(suggestions) == 3
        scores = [s.composite_score for s in suggestions]
        assert scores == sorted(scores, reverse=True)
        assert all(0.0 <= s.composite_score <= 1.0 for s in suggestions)

    def test_composite_prefers_low_spread_among_equal_sums(self):
        # Both possible even splits have identical MMR sums, but one split
        # stacks smurf+beginner vs mid+mid. Composite should prefer the
        # split where spreads match.
        players = [
            make_player(1, 2600, mu=33.0),
            make_player(2, 1400, mu=21.0),
            make_player(3, 2000, mu=27.0),
            make_player(4, 2000, mu=27.0),
        ]
        suggestions = TeamBalancer.generate_team_suggestions(
            players, top_n=10, objective="composite"
        )
        best = suggestions[0]
        best_split = {frozenset(p.id for p in best.team_1), frozenset(p.id for p in best.team_2)}
        assert best_split == {frozenset({1, 2}), frozenset({3, 4})}


class TestBalancePredictionCapture:
    def _make_match(self, db: Session, team1_ids, team2_ids, team1_won: bool, played_at=None):
        match = Match(
            played_at=played_at or datetime.utcnow(),
            game_mode=GameMode.TWO_V_TWO,
            map_name="TestMap",
            duration_seconds=600,
        )
        db.add(match)
        db.flush()
        for pid in team1_ids:
            db.add(
                MatchPlayer(
                    match_id=match.id, player_id=pid, team_number=1,
                    race=Race.TERRAN, won=1 if team1_won else 0,
                    mu_before=25, sigma_before=8, mu_after=25, sigma_after=8,
                )
            )
        for pid in team2_ids:
            db.add(
                MatchPlayer(
                    match_id=match.id, player_id=pid, team_number=2,
                    race=Race.ZERG, won=0 if team1_won else 1,
                    mu_before=25, sigma_before=8, mu_after=25, sigma_after=8,
                )
            )
        db.commit()
        return match

    def test_record_and_resolve_same_orientation(self, db_session, player_factory):
        players = [player_factory(name=f"cap{i}") for i in range(4)]
        ids = [p.id for p in players]
        BalancePredictionService.record_suggestion(
            db_session, method="test_v1", rank=1,
            team1_ids=ids[:2], team2_ids=ids[2:],
            predicted_team1_win_prob=0.6,
        )
        db_session.commit()

        match = self._make_match(db_session, ids[:2], ids[2:], team1_won=True)
        resolved = BalancePredictionService.resolve_for_match(db_session, match)
        assert resolved == 1

        pred = db_session.query(BalancePrediction).one()
        assert pred.resolved == 1
        assert pred.team1_won == 1
        assert pred.brier_score == pytest.approx((0.6 - 1) ** 2)

    def test_resolve_flipped_orientation(self, db_session, player_factory):
        players = [player_factory(name=f"flip{i}") for i in range(4)]
        ids = [p.id for p in players]
        # Prediction's team1 plays as match team2
        BalancePredictionService.record_suggestion(
            db_session, method="test_v1", rank=1,
            team1_ids=ids[2:], team2_ids=ids[:2],
            predicted_team1_win_prob=0.7,
        )
        db_session.commit()

        match = self._make_match(db_session, ids[:2], ids[2:], team1_won=True)
        BalancePredictionService.resolve_for_match(db_session, match)

        pred = db_session.query(BalancePrediction).one()
        # Prediction's team1 (= match team2) lost
        assert pred.team1_won == 0
        assert pred.brier_score == pytest.approx(0.7**2)

    def test_different_split_not_resolved(self, db_session, player_factory):
        players = [player_factory(name=f"split{i}") for i in range(4)]
        ids = [p.id for p in players]
        # Suggested split differs from the split actually played
        BalancePredictionService.record_suggestion(
            db_session, method="test_v1", rank=1,
            team1_ids=[ids[0], ids[2]], team2_ids=[ids[1], ids[3]],
            predicted_team1_win_prob=0.5,
        )
        db_session.commit()

        match = self._make_match(db_session, ids[:2], ids[2:], team1_won=True)
        resolved = BalancePredictionService.resolve_for_match(db_session, match)
        assert resolved == 0
        assert db_session.query(BalancePrediction).one().resolved == 0

    def test_stale_prediction_outside_window_not_resolved(
        self, db_session, player_factory
    ):
        players = [player_factory(name=f"stale{i}") for i in range(4)]
        ids = [p.id for p in players]
        pred = BalancePredictionService.record_suggestion(
            db_session, method="test_v1", rank=1,
            team1_ids=ids[:2], team2_ids=ids[2:],
            predicted_team1_win_prob=0.5,
        )
        pred.created_at = datetime.utcnow() - timedelta(days=3)
        db_session.commit()

        match = self._make_match(db_session, ids[:2], ids[2:], team1_won=True)
        assert BalancePredictionService.resolve_for_match(db_session, match) == 0

    def test_calibration_metrics(self, db_session, player_factory):
        players = [player_factory(name=f"cal{i}") for i in range(4)]
        ids = [p.id for p in players]
        for won, prob in [(True, 0.6), (False, 0.55), (True, 0.5)]:
            BalancePredictionService.record_suggestion(
                db_session, method="test_v1", rank=1,
                team1_ids=ids[:2], team2_ids=ids[2:],
                predicted_team1_win_prob=prob,
            )
            db_session.commit()
            match = self._make_match(db_session, ids[:2], ids[2:], team1_won=won)
            BalancePredictionService.resolve_for_match(db_session, match)

        calibration = BalancePredictionService.get_calibration(db_session)
        assert "test_v1" in calibration
        stats = calibration["test_v1"]
        assert stats["count"] == 3
        assert 0.0 <= stats["brier_score"] <= 1.0
        assert stats["log_loss"] > 0.0
        assert stats["bins"]
