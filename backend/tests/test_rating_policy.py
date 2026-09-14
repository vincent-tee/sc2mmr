from datetime import datetime, timedelta
import math

import pytest
import trueskill

from app.config import settings
from app.models import GameMode, Player, Race
from app.rating_policy import win_probability
from app.replay_parser import ReplayData, PlayerData
from app.services.ingestion import ingest_match
from scripts.walkforward_session_eval import run_simulation, holdout_comparison


def test_walkforward_matches_ingestion_across_inactivity(db_session, monkeypatch):
    monkeypatch.setattr(settings, "trueskill_beta", 6.5)
    usable, probabilities = [], []
    # Frequent games establish uncertainty and a typical gap, then a long break.
    for index, day in enumerate([0, 1, 2, 3, 4, 5, 6, 60, 61]):
        now = datetime(2026, 1, 1) + timedelta(days=day)
        team1_won = index % 3 != 0
        replay = ReplayData(
            played_at=now, game_mode=GameMode.TWO_V_TWO, map_name="Test",
            duration_seconds=600, replay_hash=f"policy-{index}", game_fingerprint=f"policy-{index}",
            players=[PlayerData(name=f"P{i}", race=Race.TERRAN,
                                team=1 if i < 2 else 2,
                                won=team1_won if i < 2 else not team1_won) for i in range(4)],
        )
        match, _ = ingest_match(db_session, replay, require_experience=False)
        players = db_session.query(Player).order_by(Player.name).all()
        ids = [p.id for p in players]
        usable.append((match.id, now.isoformat(), 1, ids[:2], 2, ids[2:], 1 if team1_won else 2))
        probabilities.append(match.predicted_team1_win_prob)
        simulated = run_simulation(usable)
        assert simulated['ts_probs'] == pytest.approx(probabilities)
        for player in players:
            expected = simulated['ratings'][player.id]
            assert (player.mu, player.sigma) == pytest.approx((expected.mu, expected.sigma))


def test_probability_uses_configured_beta_not_library_constant(monkeypatch):
    monkeypatch.setattr(settings, "trueskill_beta", 9.0)
    first, second = [trueskill.Rating(30, 2)], [trueskill.Rating(20, 2)]
    expected = .5 * (1 + math.erf(10 / math.sqrt(2 * (2 * 81 + 8))))
    assert win_probability(first, second) == pytest.approx(expected)


def test_holdout_outcomes_cannot_change_fitted_temperature():
    sessions = list(range(12))
    data = dict(ts_probs=[.9] * 12, ts_outcomes=[1, 0, 1] * 4)
    first = holdout_comparison(data, sessions)
    data['ts_outcomes'][-3:] = [0, 0, 0]
    second = holdout_comparison(data, sessions)
    assert first['temperature'] == second['temperature']
    assert first['train_count'] == 9 and first['test_count'] == 3
    assert first['calibrated'] == second['calibrated']
