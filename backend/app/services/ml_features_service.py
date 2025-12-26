"""
ML Features Service - Integrate enhanced_parser with replay processing pipeline.

This service bridges the enhanced_parser output to the PerformanceFeatures table,
enabling ML-ready feature extraction during replay processing.

Integration Points:
1. Extracts build orders, upgrades, and abilities from replay
2. Converts enhanced parser features to JSON for storage
3. Saves to performance_features table during replay processing

SPEC-ML-001 Implementation.
"""

import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models import MatchPlayer, PerformanceFeatures
from .enhanced_parser import EnhancedReplayParser, EnhancedPlayerFeatures

logger = logging.getLogger(__name__)


class MLFeaturesService:
    """
    Service to extract and store ML-ready features from replays.

    Responsibilities:
    - Call enhanced_parser to extract features
    - Convert to database-ready format
    - Save to performance_features table
    - Handle errors gracefully
    """

    @staticmethod
    def extract_and_save_ml_features(
        db: Session,
        replay_path: str,
        match_id: int,
    ) -> Dict[str, bool]:
        """
        Extract ML features from replay and save to database.

        This is the main integration point - call this after match is created
        but before rating calculations (so features are available for ML models).

        Args:
            db: Database session
            replay_path: Path to .SC2Replay file
            match_id: ID of the match (for linking MatchPlayer records)

        Returns:
            Dictionary mapping player_id -> success boolean
            Example: {1: True, 2: True, 3: False} indicates player 3 failed
        """
        results = {}

        try:
            logger.info(f"Extracting ML features from replay: {replay_path}")

            # Step 1: Parse replay with enhanced parser
            enhanced_features = MLFeaturesService._parse_replay_enhanced(
                replay_path
            )

            if not enhanced_features:
                logger.warning("Enhanced parser returned no features")
                return results

            # Step 2: Find MatchPlayer records for this match
            match_players = db.query(MatchPlayer).filter(
                MatchPlayer.match_id == match_id
            ).all()

            if not match_players:
                logger.warning(f"No match_players found for match_id={match_id}")
                return results

            # Map player names to MatchPlayer records for quick lookup
            player_lookup = {mp.player.name: mp for mp in match_players}

            # Step 3: Save features for each player
            for pid, features in enhanced_features.items():
                try:
                    success = MLFeaturesService._save_player_features(
                        db=db,
                        features=features,
                        match_player=player_lookup.get(features.player_name),
                    )
                    results[pid] = success
                except Exception as e:
                    logger.error(
                        f"Failed to save features for player {features.player_name}: {e}",
                        exc_info=True,
                    )
                    results[pid] = False

            # Step 4: Commit all changes
            try:
                db.commit()
                logger.info(
                    f"ML features saved for {sum(results.values())}/{len(results)} players"
                )
            except Exception as e:
                logger.error(f"Failed to commit ML features: {e}")
                db.rollback()
                return {pid: False for pid in results}

            return results

        except Exception as e:
            logger.error(f"Failed to extract ML features: {e}", exc_info=True)
            return results

    @staticmethod
    def _parse_replay_enhanced(
        replay_path: str,
    ) -> Optional[Dict[int, EnhancedPlayerFeatures]]:
        """
        Parse replay file with enhanced parser.

        Args:
            replay_path: Path to .SC2Replay file

        Returns:
            Dictionary mapping player_id to EnhancedPlayerFeatures, or None on error
        """
        try:
            parser = EnhancedReplayParser(replay_path)
            features = parser.parse()
            logger.info(f"Parsed {len(features)} players from replay")
            return features
        except Exception as e:
            logger.error(f"Enhanced parser failed: {e}", exc_info=True)
            return None

    @staticmethod
    def _save_player_features(
        db: Session,
        features: EnhancedPlayerFeatures,
        match_player: Optional[MatchPlayer],
    ) -> bool:
        """
        Save enhanced features to performance_features table.

        Args:
            db: Database session
            features: Enhanced features for a player
            match_player: MatchPlayer record (for linking)

        Returns:
            True if saved successfully, False otherwise
        """
        if not match_player:
            logger.warning(
                f"No MatchPlayer found for player {features.player_name}"
            )
            return False

        try:
            # Create or update performance_features record
            perf_features = (
                db.query(PerformanceFeatures)
                .filter(
                    PerformanceFeatures.match_player_id == match_player.id
                )
                .first()
            )

            if not perf_features:
                perf_features = PerformanceFeatures(
                    match_player_id=match_player.id
                )
                db.add(perf_features)

            # Save build order features
            MLFeaturesService._save_build_order_features(
                perf_features, features
            )

            # Save upgrade features
            MLFeaturesService._save_upgrade_features(
                perf_features, features
            )

            # Save ability features
            MLFeaturesService._save_ability_features(perf_features, features)

            # Save macro features
            MLFeaturesService._save_macro_features(perf_features, features)

            logger.debug(
                f"Saved ML features for {features.player_name}: "
                f"build_order={len(features.build_order)} events, "
                f"upgrades={len(features.upgrades)} events"
            )

            return True

        except Exception as e:
            logger.error(
                f"Error saving features for {features.player_name}: {e}",
                exc_info=True,
            )
            return False

    @staticmethod
    def _save_build_order_features(
        perf_features: PerformanceFeatures,
        features: EnhancedPlayerFeatures,
    ) -> None:
        """Save build order features to database."""
        if not features.build_order:
            return

        # Convert build order to JSON format
        build_order_data = [
            {
                "second": event.second,
                "unit_type": event.unit_type,
                "supply": event.supply,
                "is_building": event.is_building,
                "is_worker": event.is_worker,
            }
            for event in features.build_order
        ]

        perf_features.build_order_json = build_order_data
        perf_features.build_order_hash = features.build_order_hash
        perf_features.detected_build_type = features.detected_build_type

    @staticmethod
    def _save_upgrade_features(
        perf_features: PerformanceFeatures,
        features: EnhancedPlayerFeatures,
    ) -> None:
        """Save upgrade features to database."""
        if not features.upgrades:
            return

        # Convert upgrades to JSON format
        upgrades_data = [
            {
                "second": event.second,
                "upgrade_name": event.upgrade_name,
                "category": event.upgrade_category,
            }
            for event in features.upgrades
        ]

        perf_features.upgrades_json = upgrades_data
        perf_features.first_attack_upgrade_second = (
            features.first_attack_upgrade_second
        )
        perf_features.first_armor_upgrade_second = (
            features.first_armor_upgrade_second
        )
        perf_features.upgrade_timing_score = features.upgrade_timing_score

    @staticmethod
    def _save_ability_features(
        perf_features: PerformanceFeatures,
        features: EnhancedPlayerFeatures,
    ) -> None:
        """Save ability usage features to database."""
        if features.ability_usage.total_abilities == 0:
            return

        perf_features.abilities_json = features.ability_usage.abilities
        perf_features.total_abilities = features.ability_usage.total_abilities
        perf_features.abilities_per_minute = (
            features.ability_usage.abilities_per_minute
        )

    @staticmethod
    def _save_macro_features(
        perf_features: PerformanceFeatures,
        features: EnhancedPlayerFeatures,
    ) -> None:
        """Save macro management features to database."""
        perf_features.supply_block_seconds = features.supply_block_seconds
        perf_features.early_worker_losses = features.early_worker_losses
        perf_features.harassment_response_score = (
            features.harassment_response_score
        )

    @staticmethod
    def get_features_for_match_player(
        db: Session, match_player_id: int
    ) -> Optional[PerformanceFeatures]:
        """
        Retrieve ML features for a specific match player.

        Args:
            db: Database session
            match_player_id: MatchPlayer ID

        Returns:
            PerformanceFeatures record or None
        """
        return (
            db.query(PerformanceFeatures)
            .filter(PerformanceFeatures.match_player_id == match_player_id)
            .first()
        )
