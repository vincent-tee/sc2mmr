"""
Basic tests for SC2 MMR Tracker.
Run with: pytest tests/test_basic.py
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Player, GameMode, Race
from app.rating_system import RatingSystem


def test_player_creation():
    """Test creating a player with default ratings."""
    player = Player(name="TestPlayer")

    assert player.name == "TestPlayer"
    assert player.mu == 25.0
    assert player.sigma == 8.333
    assert player.total_games == 0
    assert player.wins == 0
    assert player.losses == 0


def test_player_mmr_calculation():
    """Test MMR calculation (mu - 3*sigma)."""
    player = Player(name="TestPlayer", mu=25.0, sigma=8.333)

    expected_mmr = 25.0 - (3 * 8.333)
    assert abs(player.mmr - expected_mmr) < 0.01


def test_player_win_rate():
    """Test win rate calculation."""
    player = Player(name="TestPlayer", total_games=10, wins=7, losses=3)

    assert player.win_rate == 70.0


def test_favorite_race():
    """Test favorite race determination."""
    player = Player(
        name="TestPlayer",
        terran_games=5,
        protoss_games=10,
        zerg_games=3,
        random_games=0
    )

    assert player.favorite_race == "Protoss"


def test_trueskill_rating_creation():
    """Test TrueSkill Rating object creation."""
    rating = RatingSystem.create_rating(mu=25.0, sigma=8.333)

    assert rating.mu == 25.0
    assert rating.sigma == 8.333


def test_conservative_rating():
    """Test conservative rating calculation."""
    mmr = RatingSystem.get_conservative_rating(mu=25.0, sigma=8.333)

    expected = 25.0 - (3 * 8.333)
    assert abs(mmr - expected) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
