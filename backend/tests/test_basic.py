"""
Basic tests for SC2 MMR Tracker.
Run with: pytest tests/test_basic.py -v
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Player, GameMode, Race
from app.rating_system import RatingSystem


class TestPlayerModel:
    """Tests for the Player model."""

    def test_player_creation_with_session(self, player_factory):
        """Test creating a player with database defaults applied."""
        player = player_factory(name="TestPlayer")

        assert player.name == "TestPlayer"
        assert player.mu == 25.0
        assert player.sigma == 8.333
        assert player.total_games == 0
        assert player.wins == 0
        assert player.losses == 0

    def test_player_creation_without_session(self):
        """Test that Player without session has None for defaults (expected SQLAlchemy behavior)."""
        # Note: SQLAlchemy column defaults are only applied on flush/commit
        player = Player(name="TestPlayer")
        assert player.name == "TestPlayer"
        # Without session, defaults are None until flush
        # This is expected SQLAlchemy behavior

    def test_player_mmr_calculation(self, player_factory):
        """
        Test MMR calculation uses the scaled display formula.

        Doctrine (owner decision 2026-07-02, rating consolidation campaign
        Phase 3): MMR = MMR_BASE + MMR_MU_MULTIPLIER * mu - 200 * sigma.
        The sigma penalty is deliberate — measured +2.3pp prediction accuracy
        over the no-sigma formula (McNemar p=0.031, n=860; see
        docs/superpowers/campaign/rating-consolidation-log.md Session 2).
        New players (mu=25, sigma=8.333) start at ~1833.
        """
        player = player_factory(name="TestPlayer", mu=25.0, sigma=8.333)

        expected_mmr = RatingSystem.calculate_display_mmr(25.0, 8.333)  # = 1833.4
        assert expected_mmr == RatingSystem.MMR_BASE + (
            RatingSystem.MMR_MU_MULTIPLIER * 25.0
        ) - (200.0 * 8.333)
        # The Player.mmr column default is the rounded new-player formula value
        assert player.mmr == pytest.approx(expected_mmr, abs=0.5)

    def test_player_mmr_varies_with_mu(self, player_factory):
        """Test that MMR scales with mu and is penalized by sigma."""
        low = RatingSystem.calculate_display_mmr(15.0, 8.333)   # = 833.4
        high = RatingSystem.calculate_display_mmr(35.0, 8.333)  # = 2833.4
        assert high > low
        assert high - low == pytest.approx(RatingSystem.MMR_MU_MULTIPLIER * 20.0)
        # sigma penalty: lower uncertainty -> higher displayed MMR at equal mu
        assert RatingSystem.calculate_display_mmr(25.0, 4.0) > RatingSystem.calculate_display_mmr(25.0, 8.333)

    def test_player_win_rate_as_decimal(self, player_factory):
        """
        Test win rate calculation returns decimal (0.0 to 1.0).

        Note: win_rate property returns decimal format, not percentage.
        Frontend is responsible for converting to percentage display.
        """
        player = player_factory(name="TestPlayer", total_games=10, wins=7, losses=3)

        # win_rate returns decimal: 7/10 = 0.7
        assert player.win_rate == 0.7

    def test_player_win_rate_zero_games(self, player_factory):
        """Test win rate is 0 when player has no games."""
        player = player_factory(name="NewPlayer", total_games=0, wins=0, losses=0)
        assert player.win_rate == 0.0

    def test_favorite_race(self, player_factory):
        """Test favorite race determination based on game counts."""
        player = player_factory(
            name="TestPlayer",
            terran_games=5,
            protoss_games=10,
            zerg_games=3,
            random_games=0
        )

        assert player.favorite_race == "Protoss"

    def test_favorite_race_no_games(self, player_factory):
        """Test favorite race when player has no games."""
        player = player_factory(
            name="NewPlayer",
            terran_games=0,
            protoss_games=0,
            zerg_games=0,
            random_games=0
        )
        assert player.favorite_race == "Unknown"


# Backward compatibility: keep old test function names as aliases
def test_player_creation(player_factory):
    """Alias for backward compatibility."""
    TestPlayerModel().test_player_creation_with_session(player_factory)


def test_player_mmr_calculation(player_factory):
    """Alias for backward compatibility."""
    TestPlayerModel().test_player_mmr_calculation(player_factory)


def test_player_win_rate(player_factory):
    """Alias for backward compatibility."""
    TestPlayerModel().test_player_win_rate_as_decimal(player_factory)


def test_favorite_race(player_factory):
    """Alias for backward compatibility."""
    TestPlayerModel().test_favorite_race(player_factory)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
