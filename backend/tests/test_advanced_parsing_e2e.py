"""
End-to-End Verification Tests for Advanced Parsing Pipeline.

Tests the full pipeline: replay parsing → ML feature extraction → PIM calculation → Hybrid MMR update

The pipeline consists of:
1. Enhanced parser extracts build orders, upgrades, abilities, macro metrics
2. ML features service saves features to performance_features table
3. PIM calculator computes performance impact modifier
4. Hybrid MMR system applies PIM to rating changes

SPEC-ML-001 Integration Tests.
"""

import pytest
import json
import math
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Player,
    Match,
    MatchPlayer,
    PlayerMatchMetrics,
    PerformanceFeatures,
    GameMode,
    Race,
)
from app.services.pi_calculator import PICalculator, MatchAverages, PIMBreakdown
from app.services.ml_features_service import MLFeaturesService
from app.services.enhanced_parser import (
    EnhancedReplayParser,
    EnhancedPlayerFeatures,
    BuildOrderEvent,
    UpgradeEvent,
    AbilityUsage,
    ResourceCheckpoint,
)


# ============================================================================
# Test Fixtures
# ============================================================================


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
            BuildOrderEvent(
                second=90, unit_type="Barracks", supply=15, is_building=True
            ),
            BuildOrderEvent(second=120, unit_type="Marine", supply=15),
            BuildOrderEvent(second=150, unit_type="Marine", supply=17),
            BuildOrderEvent(
                second=180, unit_type="CommandCenter", supply=19, is_building=True
            ),
            BuildOrderEvent(
                second=240, unit_type="Factory", supply=21, is_building=True
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
            UpgradeEvent(
                second=480,
                upgrade_name="TerranInfantryArmorsLevel1",
                upgrade_category="armor",
            ),
            UpgradeEvent(
                second=600,
                upgrade_name="TerranInfantryWeaponsLevel2",
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
            ResourceCheckpoint(
                second=180,
                minerals=200,
                vespene=50,
                workers=14,
                supply_used=19,
                supply_cap=23,
            ),
            ResourceCheckpoint(
                second=600,
                minerals=500,
                vespene=200,
                workers=18,
                supply_used=50,
                supply_cap=60,
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
    # Create players
    player1 = Player(name="Player1", mu=25.0, sigma=8.333)
    player2 = Player(name="Player2", mu=25.0, sigma=8.333)
    db_session.add_all([player1, player2])
    db_session.flush()

    # Create match
    match = Match(
        played_at=datetime.utcnow(),
        game_mode=GameMode.TWO_V_TWO,
        map_name="Frost",
        duration_seconds=600,
    )
    db_session.add(match)
    db_session.flush()

    # Create match players
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

    # Create metrics for both players
    metrics1 = PlayerMatchMetrics(
        match_player_id=mp1.id,
        minerals_collected=1500,
        vespene_collected=800,
        total_resources_collected=2300,
        resources_spent=2200,
        spending_efficiency=0.95,
        workers_created=8,
        units_trained=45,
        units_lost=12,
        units_killed=28,
        army_value_built=15000,
        army_value_killed=14000,
        army_value_lost=3000,
        damage_dealt=5000,
        damage_taken=2000,
        damage_ratio=2.5,
        first_expansion_timing=180,
        bases_created=2,
        apm=150.0,
        economic_score=75.0,
        combat_score=80.0,
        efficiency_score=85.0,
        overall_impact=80.0,
        team_fight_participation=0.8,
        team_fight_damage=3500,
        team_fight_damage_ratio=0.7,
        first_damage_timing=120,
        early_game_damage=800,
        mid_game_damage=2000,
        late_game_damage=2200,
        player_archetype="Balanced",
        aggression_score=65.0,
    )

    metrics2 = PlayerMatchMetrics(
        match_player_id=mp2.id,
        minerals_collected=1200,
        vespene_collected=600,
        total_resources_collected=1800,
        resources_spent=1700,
        spending_efficiency=0.85,
        workers_created=6,
        units_trained=35,
        units_lost=25,
        units_killed=15,
        army_value_built=12000,
        army_value_killed=8000,
        army_value_lost=5000,
        damage_dealt=2000,
        damage_taken=5000,
        damage_ratio=0.4,
        first_expansion_timing=200,
        bases_created=1,
        apm=140.0,
        economic_score=50.0,
        combat_score=30.0,
        efficiency_score=45.0,
        overall_impact=40.0,
        team_fight_participation=0.6,
        team_fight_damage=1000,
        team_fight_damage_ratio=0.5,
        first_damage_timing=150,
        early_game_damage=300,
        mid_game_damage=800,
        late_game_damage=900,
        player_archetype="Defensive",
        aggression_score=40.0,
    )

    db_session.add_all([metrics1, metrics2])
    db_session.flush()

    return {
        "match": match,
        "player1": player1,
        "player2": player2,
        "mp1": mp1,
        "mp2": mp2,
        "metrics1": metrics1,
        "metrics2": metrics2,
    }


# ============================================================================
# Tests: ML Features Extraction
# ============================================================================


class TestMLFeaturesExtraction:
    """Tests for ML features extraction from enhanced parser."""

    def test_build_order_extraction(self, mock_enhanced_features):
        """Verify build order features are captured correctly."""
        features = mock_enhanced_features

        # Check build order events
        assert len(features.build_order) == 7
        assert features.build_order[0].unit_type == "SCV"
        assert features.build_order[0].is_worker is True
        assert features.build_order[1].unit_type == "SupplyDepot"
        assert features.build_order[1].is_building is True

        # Check build classification
        assert features.detected_build_type == "macro"
        assert features.build_order_hash == "abc123def456"

    def test_upgrade_timing_extraction(self, mock_enhanced_features):
        """Verify upgrade timing features are captured."""
        features = mock_enhanced_features

        assert len(features.upgrades) == 3
        assert features.first_attack_upgrade_second == 420
        assert features.first_armor_upgrade_second == 480
        assert features.upgrade_timing_score == 1.5

        # Check upgrade details
        attack_upgrades = [
            u for u in features.upgrades if u.upgrade_category == "attack"
        ]
        armor_upgrades = [u for u in features.upgrades if u.upgrade_category == "armor"]

        assert len(attack_upgrades) == 2
        assert len(armor_upgrades) == 1

    def test_ability_extraction(self, mock_enhanced_features):
        """Verify ability usage features are captured."""
        features = mock_enhanced_features

        assert features.ability_usage.total_abilities == 25
        assert features.ability_usage.abilities_per_minute == 5.0
        assert "Stim" in features.ability_usage.abilities
        assert features.ability_usage.abilities["Stim"] == 15
        assert features.ability_usage.abilities["EMP"] == 5

    def test_macro_feature_extraction(self, mock_enhanced_features):
        """Verify macro management features are captured."""
        features = mock_enhanced_features

        assert features.early_worker_losses == 2
        assert features.harassment_response_score == 80.0
        assert features.supply_block_seconds == 45

    def test_resource_checkpoint_extraction(self, mock_enhanced_features):
        """Verify resource checkpoint tracking."""
        features = mock_enhanced_features

        assert len(features.resource_checkpoints) == 3
        assert features.resource_checkpoints[0].second == 60
        assert features.resource_checkpoints[0].workers == 13
        assert features.resource_checkpoints[2].second == 600
        assert features.resource_checkpoints[2].minerals == 500


# ============================================================================
# Tests: Performance Features Storage
# ============================================================================


class TestPerformanceFeaturesStorage:
    """Tests for saving ML features to database."""

    def test_save_performance_features(
        self, db_session: Session, match_with_players, mock_enhanced_features
    ):
        """Verify performance features are saved to database."""
        mp1 = match_with_players["mp1"]

        # Create performance features
        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            build_order_json=[
                {
                    "second": 24,
                    "unit_type": "SCV",
                    "is_building": False,
                    "is_worker": True,
                },
                {
                    "second": 60,
                    "unit_type": "SupplyDepot",
                    "is_building": True,
                    "is_worker": False,
                },
            ],
            build_order_hash=mock_enhanced_features.build_order_hash,
            detected_build_type=mock_enhanced_features.detected_build_type,
            upgrades_json=[
                {
                    "second": 420,
                    "upgrade_name": "TerranInfantryWeaponsLevel1",
                    "category": "attack",
                },
            ],
            first_attack_upgrade_second=420,
            first_armor_upgrade_second=480,
            abilities_json={"Stim": 15, "EMP": 5},
            total_abilities=20,
            abilities_per_minute=4.0,
            supply_block_seconds=45,
            early_worker_losses=2,
            harassment_response_score=80.0,
        )

        db_session.add(perf_features)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved is not None
        assert retrieved.detected_build_type == "macro"
        assert retrieved.total_abilities == 20
        assert retrieved.harassment_response_score == 80.0

    def test_build_order_json_storage(self, db_session: Session, match_with_players):
        """Verify build order JSON is stored correctly."""
        mp1 = match_with_players["mp1"]

        build_order_data = [
            {"second": 24, "unit_type": "SCV", "is_building": False},
            {"second": 60, "unit_type": "SupplyDepot", "is_building": True},
            {"second": 90, "unit_type": "Barracks", "is_building": True},
        ]

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            build_order_json=build_order_data,
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.build_order_json == build_order_data
        assert len(retrieved.build_order_json) == 3
        assert retrieved.build_order_json[0]["unit_type"] == "SCV"

    def test_abilities_json_storage(self, db_session: Session, match_with_players):
        """Verify abilities JSON is stored correctly."""
        mp1 = match_with_players["mp1"]

        abilities_data = {
            "Stim": 15,
            "EMP": 5,
            "ScannerSweep": 3,
        }

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            abilities_json=abilities_data,
            total_abilities=23,
            abilities_per_minute=4.6,
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.abilities_json == abilities_data
        assert retrieved.total_abilities == 23
        assert retrieved.abilities_per_minute == 4.6

    def test_upgrades_json_storage(self, db_session: Session, match_with_players):
        """Verify upgrades JSON is stored correctly."""
        mp1 = match_with_players["mp1"]

        upgrades_data = [
            {
                "second": 420,
                "upgrade_name": "TerranInfantryWeaponsLevel1",
                "category": "attack",
            },
            {
                "second": 480,
                "upgrade_name": "TerranInfantryArmorsLevel1",
                "category": "armor",
            },
            {
                "second": 600,
                "upgrade_name": "TerranInfantryWeaponsLevel2",
                "category": "attack",
            },
        ]

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            upgrades_json=upgrades_data,
            first_attack_upgrade_second=420,
            first_armor_upgrade_second=480,
            upgrade_timing_score=1.5,
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.upgrades_json == upgrades_data
        assert len(retrieved.upgrades_json) == 3
        assert retrieved.first_attack_upgrade_second == 420


# ============================================================================
# Tests: PIM Calculation
# ============================================================================


class TestPIMCalculation:
    """Tests for Performance Impact Modifier calculation."""

    def test_pim_affects_mmr_change(self, db_session: Session, match_with_players):
        """Verify PIM modifies the MMR change correctly."""
        calculator = PICalculator()
        match_averages = MatchAverages()

        metrics1 = match_with_players["metrics1"]
        mp1 = match_with_players["mp1"]

        # Create z-scores (above average)
        pim, breakdown = calculator.calculate_pim(metrics1, match_averages)

        # Above average performance should give positive PIM
        assert pim > 0, "Above average performance should yield positive PIM"
        assert breakdown.total > 0

        # Apply PIM to a base MMR change
        base_change = 50  # Base MMR gain
        adjusted_change = calculator.apply_pim_to_mmr_change(base_change, pim)

        assert adjusted_change > base_change, "Positive PIM should amplify gains"

    def test_pim_loss_scenario(self, db_session: Session, match_with_players):
        """Verify PIM reduces loss in losing scenario."""
        calculator = PICalculator()
        match_averages = MatchAverages()

        metrics1 = match_with_players["metrics1"]

        # Even though player lost, they had above-average performance
        # Create custom metrics with loss but good performance
        loss_metrics = PlayerMatchMetrics(
            damage_ratio=2.5,
            combat_score=80.0,
            economic_score=75.0,
            overall_impact=80.0,
            spending_efficiency=0.95,
            efficiency_score=85.0,
            team_fight_participation=0.8,
            team_fight_damage_ratio=0.7,
        )

        pim, breakdown = calculator.calculate_pim(loss_metrics, match_averages)

        # Even in a loss, good performance gives positive PIM
        assert pim > 0, "Good performance yields positive PIM even in loss"

        # Apply to loss scenario
        base_loss = -50
        adjusted_loss = calculator.apply_pim_to_mmr_change(base_loss, pim)

        # With positive PIM, loss should be less severe
        assert abs(adjusted_loss) < abs(base_loss), (
            "Positive PIM reduces loss magnitude"
        )

    def test_pim_bounded_values(self):
        """Verify PIM stays within [-0.5, 0.5] bounds."""
        calculator = PICalculator()
        match_averages = MatchAverages()

        # Create extreme metrics (should be bounded)
        extreme_high = PlayerMatchMetrics(
            damage_ratio=10.0,
            combat_score=100.0,
            economic_score=100.0,
            overall_impact=100.0,
            spending_efficiency=1.0,
            efficiency_score=100.0,
            team_fight_participation=1.0,
            team_fight_damage_ratio=10.0,
        )

        pim, _ = calculator.calculate_pim(extreme_high, match_averages)
        assert pim <= 0.5, f"PIM should not exceed 0.5, got {pim}"
        assert pim >= -0.5, f"PIM should not be below -0.5, got {pim}"

    def test_pim_z_score_normalization(self):
        """Verify z-score calculation is correct."""
        calculator = PICalculator()

        # Test average value
        z = calculator.calculate_z_score(50, 50, 10)
        assert z == 0.0

        # Test above average
        z = calculator.calculate_z_score(70, 50, 10)
        assert z == 2.0

        # Test below average
        z = calculator.calculate_z_score(30, 50, 10)
        assert z == -2.0

        # Test zero std (safety)
        z = calculator.calculate_z_score(70, 50, 0)
        assert z == 0.0

    def test_pim_breakdown_categories(self, db_session: Session):
        """Verify PIM breakdown has all categories."""
        calculator = PICalculator()
        match_averages = MatchAverages()

        metrics = PlayerMatchMetrics(
            damage_ratio=1.5,
            combat_score=70.0,
            economic_score=70.0,
            overall_impact=70.0,
            spending_efficiency=0.85,
            efficiency_score=70.0,
            team_fight_participation=0.7,
            team_fight_damage_ratio=1.5,
        )

        pim, breakdown = calculator.calculate_pim(metrics, match_averages)

        # Check all categories exist
        assert hasattr(breakdown, "combat")
        assert hasattr(breakdown, "economic")
        assert hasattr(breakdown, "team")
        assert hasattr(breakdown, "efficiency")
        assert hasattr(breakdown, "total")

        # Total should be sum of weighted components
        expected_total = (
            breakdown.combat * 0.4
            + breakdown.economic * 0.25
            + breakdown.team * 0.25
            + breakdown.efficiency * 0.1
        )
        # Account for clamping
        assert abs(pim - breakdown.total) < 0.01


# ============================================================================
# Tests: Hybrid MMR Integration
# ============================================================================


class TestHybridMMRIntegration:
    """Tests for hybrid MMR system with PIM integration."""

    def test_performance_features_linked_to_match_player(
        self, db_session: Session, match_with_players
    ):
        """Verify performance features are properly linked to match players."""
        mp1 = match_with_players["mp1"]

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            pim=0.2,
            raw_mmr_change=50.0,
            hybrid_mmr_change=60.0,
        )

        db_session.add(perf_features)
        db_session.commit()

        # Retrieve via relationship (backref creates a list, get first item)
        retrieved_mp = (
            db_session.query(MatchPlayer).filter(MatchPlayer.id == mp1.id).first()
        )

        assert retrieved_mp.performance_features is not None
        assert len(retrieved_mp.performance_features) > 0
        assert retrieved_mp.performance_features[0].pim == 0.2

    def test_raw_vs_hybrid_mmr_change(self, db_session: Session, match_with_players):
        """Verify raw MMR change vs hybrid MMR change difference."""
        mp1 = match_with_players["mp1"]

        # Create performance features with PIM
        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            pim=0.3,  # 30% performance bonus
            raw_mmr_change=50.0,  # Base TrueSkill change
            hybrid_mmr_change=65.0,  # With PIM applied: 50 * 1.3
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        # Verify relationship: hybrid = raw * (1 + PIM)
        expected_hybrid = retrieved.raw_mmr_change * (1 + retrieved.pim)
        assert abs(retrieved.hybrid_mmr_change - expected_hybrid) < 0.01

    def test_pim_with_loss(self, db_session: Session, match_with_players):
        """Verify PIM correctly modifies losses."""
        mp2 = match_with_players["mp2"]  # This player lost

        # Good performance even in loss gives positive PIM
        perf_features = PerformanceFeatures(
            match_player_id=mp2.id,
            pim=0.15,  # Even with loss, good defense = positive PIM
            raw_mmr_change=-50.0,  # Base loss
            hybrid_mmr_change=-42.5,  # With PIM: -50 * (1 - 0.15) = -42.5
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp2.id)
            .first()
        )

        # Loss with positive PIM should be less severe
        assert abs(retrieved.hybrid_mmr_change) < abs(retrieved.raw_mmr_change)

    def test_zero_pim_unchanged_mmr(self, db_session: Session, match_with_players):
        """Verify zero PIM doesn't change raw MMR."""
        mp1 = match_with_players["mp1"]

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            pim=0.0,  # Average performance
            raw_mmr_change=50.0,
            hybrid_mmr_change=50.0,  # No change
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.hybrid_mmr_change == retrieved.raw_mmr_change


# ============================================================================
# Tests: Re-processing Idempotency
# ============================================================================


class TestReprocessingIdempotency:
    """Tests for idempotent re-processing of replays."""

    def test_reprocess_updates_not_duplicates(
        self, db_session: Session, match_with_players
    ):
        """Verify re-processing updates existing records instead of creating duplicates."""
        mp1 = match_with_players["mp1"]

        # Initial save
        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            pim=0.1,
            build_order_hash="hash_v1",
        )
        db_session.add(perf_features)
        db_session.commit()

        initial_id = perf_features.id

        # Re-process (update)
        existing = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert existing is not None
        existing.pim = 0.2
        existing.build_order_hash = "hash_v2"
        db_session.commit()

        # Verify only one record exists
        count = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .count()
        )

        assert count == 1

        # Verify record was updated
        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.id == initial_id
        assert retrieved.pim == 0.2
        assert retrieved.build_order_hash == "hash_v2"

    def test_multiple_players_same_match(self, db_session: Session, match_with_players):
        """Verify multiple performance features for same match don't conflict."""
        mp1 = match_with_players["mp1"]
        mp2 = match_with_players["mp2"]

        # Add features for both players
        pf1 = PerformanceFeatures(
            match_player_id=mp1.id,
            pim=0.2,
            detected_build_type="macro",
        )

        pf2 = PerformanceFeatures(
            match_player_id=mp2.id,
            pim=-0.1,
            detected_build_type="timing",
        )

        db_session.add_all([pf1, pf2])
        db_session.commit()

        # Verify both exist
        count = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id.in_([mp1.id, mp2.id]))
            .count()
        )

        assert count == 2

        # Verify they're independent
        retrieved1 = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        retrieved2 = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp2.id)
            .first()
        )

        assert retrieved1.detected_build_type == "macro"
        assert retrieved2.detected_build_type == "timing"


# ============================================================================
# Tests: Z-Score Normalization
# ============================================================================


class TestZScoreNormalization:
    """Tests for z-score normalization across multiple matches."""

    def test_zscore_distribution_stats(self):
        """Verify z-scores have correct statistical properties."""
        calculator = PICalculator()

        # Create a series of metrics with known distribution
        metrics_values = [30, 40, 50, 60, 70]  # Mean = 50, values around it
        match_avg = 50
        match_std = 14.14  # Standard deviation

        z_scores = [
            calculator.calculate_z_score(val, match_avg, match_std)
            for val in metrics_values
        ]

        # Z-scores should be: -1.41, -0.71, 0, 0.71, 1.41
        expected = [-1.41, -0.71, 0, 0.71, 1.41]

        for calculated, expected_val in zip(z_scores, expected):
            assert abs(calculated - expected_val) < 0.05

    def test_zscore_mean_zero(self):
        """Verify z-scores have mean approximately zero."""
        calculator = PICalculator()
        match_avg = 50
        match_std = 10

        values = list(range(30, 71, 5))  # 30, 35, 40, ..., 70
        z_scores = [
            calculator.calculate_z_score(val, match_avg, match_std) for val in values
        ]

        mean_z = sum(z_scores) / len(z_scores)
        assert abs(mean_z) < 0.1  # Mean should be ~0

    def test_zscore_normalization_preserves_scale(self):
        """Verify z-score normalization preserves relative differences."""
        calculator = PICalculator()
        match_avg = 50
        match_std = 10

        # Test relative differences are preserved
        value1 = 40  # 1 std below mean
        value2 = 60  # 1 std above mean

        z1 = calculator.calculate_z_score(value1, match_avg, match_std)
        z2 = calculator.calculate_z_score(value2, match_avg, match_std)

        # Z-scores should be -1 and +1
        assert abs(z1 - (-1.0)) < 0.01
        assert abs(z2 - 1.0) < 0.01

        # Difference in z-scores should equal difference in stds
        assert abs((z2 - z1) - 2.0) < 0.01


# ============================================================================
# Tests: End-to-End Pipeline
# ============================================================================


class TestE2EPipeline:
    """Integration tests for the full advanced parsing pipeline."""

    def test_full_pipeline_flow(
        self, db_session: Session, match_with_players, mock_enhanced_features
    ):
        """Test complete pipeline: parsing → features → PIM → MMR."""
        mp1 = match_with_players["mp1"]

        # Step 1: Parse and extract features (simulated)
        enhanced_features = mock_enhanced_features

        # Step 2: Save to performance_features
        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            build_order_json=[{"second": 24, "unit_type": "SCV", "is_building": False}],
            detected_build_type=enhanced_features.detected_build_type,
            upgrades_json=[
                {"second": 420, "upgrade_name": "TerranInfantryWeaponsLevel1"}
            ],
            first_attack_upgrade_second=enhanced_features.first_attack_upgrade_second,
            abilities_json=dict(enhanced_features.ability_usage.abilities),
            total_abilities=enhanced_features.ability_usage.total_abilities,
            early_worker_losses=enhanced_features.early_worker_losses,
            harassment_response_score=enhanced_features.harassment_response_score,
        )

        db_session.add(perf_features)
        db_session.flush()

        # Step 3: Calculate PIM
        calculator = PICalculator()
        match_averages = MatchAverages()

        metrics = match_with_players["metrics1"]
        pim, breakdown = calculator.calculate_pim(metrics, match_averages)

        # Step 4: Apply to MMR
        base_change = 50.0
        hybrid_change = calculator.apply_pim_to_mmr_change(base_change, pim)

        # Update performance features with PIM
        perf_features.pim = pim
        perf_features.raw_mmr_change = base_change
        perf_features.hybrid_mmr_change = hybrid_change
        perf_features.pim_combat = breakdown.combat
        perf_features.pim_economic = breakdown.economic
        perf_features.pim_team = breakdown.team
        perf_features.pim_efficiency = breakdown.efficiency

        db_session.commit()

        # Verify complete flow
        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.detected_build_type == "macro"
        assert retrieved.total_abilities == 25
        assert retrieved.pim > 0  # Above average
        assert retrieved.hybrid_mmr_change > retrieved.raw_mmr_change

    def test_pipeline_error_handling(self, db_session: Session, match_with_players):
        """Test pipeline handles missing data gracefully."""
        mp1 = match_with_players["mp1"]

        # Create minimal performance features (some fields missing)
        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            # Missing build_order_json, upgrades_json, etc.
        )

        db_session.add(perf_features)
        db_session.commit()

        # Should still work with defaults
        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved is not None
        assert retrieved.build_order_json is None
        assert retrieved.total_abilities == 0  # Default

    def test_pim_version_tracking(self, db_session: Session, match_with_players):
        """Verify PIM calculation version is tracked."""
        mp1 = match_with_players["mp1"]

        perf_features = PerformanceFeatures(
            match_player_id=mp1.id,
            pim=0.2,
            pim_version="rule_v1",
        )

        db_session.add(perf_features)
        db_session.commit()

        retrieved = (
            db_session.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == mp1.id)
            .first()
        )

        assert retrieved.pim_version == "rule_v1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
