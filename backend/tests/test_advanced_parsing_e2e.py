"""
End-to-End Verification Tests for Advanced Parsing Pipeline.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import (
    Player,
    Match,
    MatchPlayer,
    PlayerMatchMetrics,
    PerformanceFeatures,
    GameMode,
    Race,
)
from app.services.pi_calculator import PICalculator, MatchAverages
from app.services.enhanced_parser import (
    EnhancedPlayerFeatures,
    BuildOrderEvent,
    UpgradeEvent,
    AbilityUsage,
    ResourceCheckpoint,
)


@pytest.fixture
def mock_enhanced_features():
    """Create mock enhanced features for testing."""
    ability_usage = AbilityUsage(
        total_abilities=25,
        abilities={"Stim": 15, "EMP": 5, "ScannerSweep": 5},
        abilities_per_minute=5.0,
    )

    features = EnhancedPlayerFeatures(
        player_id=1,
        player_name="TestPlayer",
        race="Terran",
        team=1,
        won=True,
        build_order=[
            BuildOrderEvent(second=24, unit_type="SCV", supply=13, is_worker=True),
            BuildOrderEvent(
                second=60, unit_type="SupplyDepot", supply=13, is_building=True
            ),
        ],
        build_order_hash="abc123def456",
        detected_build_type="macro",
        upgrades=[
            UpgradeEvent(
                second=420,
                upgrade_name="TerranInfantryWeaponsLevel1",
                upgrade_category="attack",
            ),
        ],
        upgrade_timing_score=1.5,
        first_attack_upgrade_second=420,
        first_armor_upgrade_second=480,
        ability_usage=ability_usage,
        resource_checkpoints=[
            ResourceCheckpoint(
                second=60,
                minerals=100,
                vespene=0,
                workers=13,
                supply_used=13,
                supply_cap=15,
            ),
        ],
        early_worker_losses=2,
        harassment_response_score=80.0,
        supply_block_seconds=45,
    )

    return features


@pytest.fixture
def match_with_players(db_session: Session):
    """Create a match with 2 players and metrics."""
    player1 = Player(name="Player1", mu=25.0, sigma=8.333)
    player2 = Player(name="Player2", mu=25.0, sigma=8.333)
    db_session.add_all([player1, player2])
    db_session.flush()

    match = Match(
        played_at=datetime.utcnow(),
        game_mode=GameMode.TWO_V_TWO,
        map_name="Frost",
        duration_seconds=600,
    )
    db_session.add(match)
    db_session.flush()

    mp1 = MatchPlayer(
        match_id=match.id,
        player_id=player1.id,
        team_number=1,
        race=Race.TERRAN,
        won=1,
        mu_before=25.0,
        sigma_before=8.333,
        mu_after=26.5,
        sigma_after=7.5,
    )

    mp2 = MatchPlayer(
        match_id=match.id,
        player_id=player2.id,
        team_number=2,
        race=Race.PROTOSS,
        won=0,
        mu_before=25.0,
        sigma_before=8.333,
        mu_after=23.5,
        sigma_after=7.5,
    )

    db_session.add_all([mp1, mp2])
    db_session.flush()

    metrics1 = PlayerMatchMetrics(
        match_player_id=mp1.id,
        damage_ratio=2.5,
        economic_score=75.0,
        combat_score=80.0,
        efficiency_score=85.0,
        overall_impact=80.0,
    )

    db_session.add(metrics1)
    db_session.flush()

    return {
        "match": match,
        "mp1": mp1,
        "mp2": mp2,
        "metrics1": metrics1,
    }


class TestPerformanceFeaturesStorage:
    """Tests for saving ML features to database."""

    def test_save_performance_features(
        self, db_session: Session, match_with_players, mock_enhanced_features
    ):
        """Verify performance features are saved to database."""
        mp1 = match_with_players["mp1"]

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            build_order_json=[{"second": 24, "unit_type": "SCV"}],
            detected_build_type="macro",
            total_abilities=20,
            harassment_response_score=80.0,
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved_mp = (
            db_session.query(MatchPlayer).filter(MatchPlayer.id == mp1.id).first()
        )

        assert retrieved_mp is not None
        assert retrieved_mp.performance_features is not None
        assert retrieved_mp.performance_features.detected_build_type == "macro"

    def test_pim_calculation(self, match_with_players):
        """Verify PIM calculation."""
        calculator = PICalculator()
        match_averages = MatchAverages()
        metrics1 = match_with_players["metrics1"]

        pim, breakdown = calculator.calculate_pim(metrics1, match_averages)
        # PIM should be in valid range (-0.5 to +0.5)
        assert -0.5 <= pim <= 0.5
        # Breakdown total should match PIM
        assert abs(breakdown.total - pim) < 0.001
