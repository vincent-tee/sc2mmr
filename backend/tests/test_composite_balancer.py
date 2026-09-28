"""
Tests for balancer win probability and balance prediction capture.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.balancer import (
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


class TestBalancePredictionCapture:
    def _make_match(self, db: Session, team1_ids, team2_ids, team1_won: bool):
        game_length = timedelta(minutes=10)
        started_just_after_suggestion = datetime.utcnow() + timedelta(minutes=1)
        match = Match(
            played_at=started_just_after_suggestion + game_length,
            game_mode=GameMode.TWO_V_TWO,
            map_name="TestMap",
            duration_seconds=int(game_length.total_seconds()),
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
