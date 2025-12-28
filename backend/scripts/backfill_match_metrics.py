#!/usr/bin/env python3
"""
Backfill PlayerMatchMetrics Script

Re-processes existing matches to extract in-game metrics from replay files.
This populates/updates the player_match_metrics table for ML feature extraction.

Usage:
    python backend/scripts/backfill_match_metrics.py
    python backend/scripts/backfill_match_metrics.py --force  # Re-process all matches
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import logging
import json
from typing import Optional, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Match, MatchPlayer, PlayerMatchMetrics, Player
from app.advanced_parser import parse_replay_advanced, PlayerMetrics
from app.impact_service import ImpactService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from settings."""
    db_path = Path(backend_path) / "data" / "sc2mmr.db"
    return f"sqlite:///{db_path}"


def has_metrics(session: Session, match_id: int) -> bool:
    """Check if match already has PlayerMatchMetrics."""
    count = (
        session.query(PlayerMatchMetrics)
        .join(MatchPlayer, PlayerMatchMetrics.match_player_id == MatchPlayer.id)
        .filter(MatchPlayer.match_id == match_id)
        .count()
    )
    return count > 0


def update_metrics(existing: PlayerMatchMetrics, pm: PlayerMetrics) -> None:
    """Update existing PlayerMatchMetrics with new values from parsed metrics."""
    # Resource metrics
    existing.minerals_collected = pm.minerals_collected
    existing.vespene_collected = pm.vespene_collected
    existing.total_resources_collected = pm.total_resources_collected
    existing.resources_spent = pm.resources_spent
    existing.spending_efficiency = pm.spending_efficiency
    existing.workers_created = pm.workers_created
    existing.units_trained = pm.units_trained
    existing.units_lost = pm.units_lost
    existing.units_killed = pm.units_killed

    # Army metrics
    existing.army_value_built = pm.army_value_built
    existing.army_value_killed = pm.army_value_killed
    existing.army_value_lost = pm.army_value_lost
    existing.damage_dealt = pm.damage_dealt
    existing.damage_taken = pm.damage_taken
    existing.damage_ratio = pm.damage_ratio

    # Calculated scores
    existing.economic_score = pm.economic_score
    existing.combat_score = pm.combat_score
    existing.efficiency_score = pm.efficiency_score
    existing.overall_impact = pm.overall_impact

    # Team fight metrics
    existing.team_fight_participation = pm.team_fight_participation
    existing.team_fight_damage = pm.team_fight_damage
    existing.team_fight_damage_ratio = pm.team_fight_damage_ratio

    # Timing and composition
    existing.first_expansion_timing = pm.first_expansion_timing
    existing.bases_created = pm.bases_created
    existing.apm = pm.apm
    existing.unit_composition = (
        json.dumps(pm.unit_composition) if pm.unit_composition else None
    )

    # Damage timeline
    existing.first_damage_timing = pm.first_damage_timing
    existing.early_game_damage = pm.early_game_damage
    existing.mid_game_damage = pm.mid_game_damage
    existing.late_game_damage = pm.late_game_damage
    existing.aggression_score = pm.aggression_score

    if pm.damage_timeline:
        existing.damage_timeline = pm.damage_timeline.to_json()


def backfill_match(
    session: Session, match: Match, force: bool = False
) -> Dict[str, bool]:
    """
    Backfill PlayerMatchMetrics for a single match.

    Args:
        session: Database session
        match: Match to process
        force: If True, update even if metrics exist

    Returns:
        Dict of player_name -> success status
    """
    results = {}

    if not match.replay_file_path or not os.path.exists(match.replay_file_path):
        logger.warning(
            f"Match {match.id}: Replay file not found at {match.replay_file_path}"
        )
        return results

    try:
        # Extract metrics from replay
        replay_data = parse_replay_advanced(match.replay_file_path)
        player_metrics = replay_data.player_metrics if replay_data else []

        if not player_metrics:
            logger.warning(f"Match {match.id}: No metrics extracted from replay")
            return results

        # Get match players
        match_players = (
            session.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )

        for mp in match_players:
            player = session.query(Player).filter(Player.id == mp.player_id).first()
            if not player:
                continue

            # Find matching metrics by player name
            pm: Optional[PlayerMetrics] = None
            for metrics in player_metrics:
                if metrics.player_name == player.name:
                    pm = metrics
                    break

            if not pm:
                # Try matching by team and similar attributes
                for metrics in player_metrics:
                    if metrics.team == mp.team_number and metrics.race == mp.race:
                        pm = metrics
                        break

            if pm:
                # Check if already has metrics
                existing = (
                    session.query(PlayerMatchMetrics)
                    .filter(PlayerMatchMetrics.match_player_id == mp.id)
                    .first()
                )

                if existing:
                    if force:
                        # Update existing metrics
                        update_metrics(existing, pm)
                        results[player.name] = True
                        logger.debug(
                            f"Match {match.id}, Player {player.name}: Updated metrics"
                        )
                    else:
                        logger.debug(
                            f"Match {match.id}, Player {player.name}: Already has metrics"
                        )
                        results[player.name] = True
                else:
                    # Save new metrics
                    ImpactService.save_match_metrics(session, mp.id, pm)
                    results[player.name] = True
                    logger.debug(
                        f"Match {match.id}, Player {player.name}: Saved metrics"
                    )
            else:
                logger.warning(
                    f"Match {match.id}, Player {player.name}: No matching metrics found"
                )
                results[player.name] = False

        session.commit()

    except Exception as e:
        logger.error(f"Match {match.id}: Error processing - {e}")
        session.rollback()

    return results


def main():
    """Main backfill entry point."""
    # Check for --force flag
    force = "--force" in sys.argv

    logger.info("=" * 60)
    logger.info("PlayerMatchMetrics Backfill Script")
    if force:
        logger.info("MODE: FORCE UPDATE - Will re-process all matches")
    logger.info("=" * 60)

    # Setup database
    db_url = get_database_url()
    logger.info(f"Database: {db_url}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get matches to process
        all_matches = session.query(Match).order_by(Match.id).all()

        if force:
            matches_to_process = all_matches
        else:
            matches_to_process = []
            for match in all_matches:
                if not has_metrics(session, match.id):
                    matches_to_process.append(match)

        total = len(matches_to_process)
        logger.info(f"Found {len(all_matches)} total matches, {total} to process")

        if total == 0:
            logger.info("All matches already have metrics!")
            return

        # Process each match
        success = 0
        failed = 0
        players_processed = 0

        for i, match in enumerate(matches_to_process, 1):
            logger.info(
                f"[{i}/{total}] Processing match {match.id} ({match.played_at})..."
            )

            results = backfill_match(session, match, force=force)

            if results:
                success_count = sum(1 for v in results.values() if v)
                players_processed += success_count
                if success_count > 0:
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1

            # Progress update every 10 matches
            if i % 10 == 0:
                logger.info(
                    f"Progress: {i}/{total} ({success} success, {failed} failed, {players_processed} players)"
                )

        # Final summary
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"  Matches processed: {total}")
        logger.info(f"  Successful: {success}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Players with metrics: {players_processed}")
        logger.info("=" * 60)

        # Verify final count
        final_count = session.query(PlayerMatchMetrics).count()
        logger.info(f"Total PlayerMatchMetrics records: {final_count}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
