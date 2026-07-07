#!/usr/bin/env python3
"""
Backfill CommandCenter Metrics Script

Re-processes existing matches using PyCommandCenter to extract high-fidelity
economic and damage statistics from replay files.

This script updates PlayerMatchMetrics with accurate:
- Damage dealt/taken (actual HP, not cost-based estimates)
- Resources collected and spent
- Income rates over time
- Army values

Usage:
    python backend/scripts/backfill_cc_metrics.py [--force] [--limit N] [--match-id ID]

Options:
    --force     Reprocess all matches, even those with existing CC metrics
    --limit N   Only process N matches
    --match-id  Process a specific match by ID
    --dry-run   Show what would be processed without making changes

Requirements:
    - StarCraft II installed (Linux headless build)
    - PyCommandCenter library compiled (library.so in backend/app/lib/)
    - Replay files accessible at their stored paths
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models import Match, MatchPlayer, PlayerMatchMetrics
from app.services.commandcenter_parser import (
    get_commandcenter_parser,
    is_commandcenter_available,
    CommandCenterParser,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from settings."""
    db_path = Path(backend_path) / "data" / "sc2mmr.db"
    return f"sqlite:///{db_path}"


def get_replay_storage_dirs() -> list[Path]:
    """Get possible replay storage directories.

    The old replay-observer watch directory (the local SC2 install's replay
    folder) can still be searched by setting SC2_REPLAY_WATCH_DIR; the
    observer feature itself was removed 2026-07-07.
    """
    dirs = [
        backend_path / "replays",
        backend_path / "data" / "replays",
        backend_path / "failed_replays",
    ]
    extra = os.environ.get("SC2_REPLAY_WATCH_DIR")
    if extra:
        dirs.insert(0, Path(extra))
    return dirs


def find_replay_file(match: Match) -> Optional[Path]:
    """
    Try to find the replay file for a match.

    Args:
        match: Match record with replay_file_path or replay_hash

    Returns:
        Path to replay file or None if not found
    """
    # First, try the stored path
    if match.replay_file_path and os.path.exists(match.replay_file_path):
        return Path(match.replay_file_path)

    # Try to find by hash in known directories
    if match.replay_hash:
        for dir_path in get_replay_storage_dirs():
            if dir_path.exists():
                for replay_file in dir_path.rglob("*.SC2Replay"):
                    # Check if hash is in filename or compute hash
                    if match.replay_hash[:10] in replay_file.name:
                        return replay_file

    return None


def match_needs_cc_metrics(session: Session, match: Match, force: bool = False) -> bool:
    """
    Check if a match needs CC metrics backfill.

    Args:
        session: Database session
        match: Match to check
        force: If True, always return True

    Returns:
        True if match needs processing
    """
    if force:
        return True

    # Check if match has metrics with realistic damage values
    metrics = (
        session.query(PlayerMatchMetrics)
        .join(MatchPlayer)
        .filter(MatchPlayer.match_id == match.id)
        .all()
    )

    if not metrics:
        return True

    # Check if damage values look like they came from CC parser (actual HP damage)
    # CC damage is usually much higher than cost-based estimates
    total_damage = sum(m.damage_dealt or 0 for m in metrics)
    total_minerals = sum(m.minerals_collected or 0 for m in metrics)

    # If total damage is 0 or very low relative to resources, likely needs CC
    if total_damage < 100:
        return True

    # If minerals are 0, definitely needs processing
    if total_minerals < 100:
        return True

    return False


def backfill_match_cc_metrics(
    session: Session,
    cc_parser: CommandCenterParser,
    match: Match,
    dry_run: bool = False,
) -> bool:
    """
    Backfill CC metrics for a single match.

    Args:
        session: Database session
        cc_parser: CommandCenter parser instance
        match: Match to process
        dry_run: If True, don't actually save changes

    Returns:
        True if successful, False otherwise
    """
    # Find replay file
    replay_path = find_replay_file(match)
    if not replay_path:
        logger.warning(f"Match {match.id}: Replay file not found")
        return False

    try:
        # Get number of players
        match_players = (
            session.query(MatchPlayer).filter(MatchPlayer.match_id == match.id).all()
        )
        num_players = len(match_players)

        if num_players < 2:
            logger.warning(
                f"Match {match.id}: Only {num_players} players found, skipping"
            )
            return False

        logger.info(
            f"Processing match {match.id} ({num_players} players) from {replay_path}"
        )

        if dry_run:
            logger.info(f"[DRY RUN] Would process match {match.id}")
            return True

        # Parse with CommandCenter
        cc_metrics = cc_parser.parse_replay(str(replay_path), num_players=num_players)

        if not cc_metrics:
            logger.warning(f"Match {match.id}: No metrics returned from CC parser")
            return False

        # Update metrics for each player
        updated = 0
        for idx, mp in enumerate(match_players):
            cc_pid = idx + 1  # CC uses 1-indexed player IDs

            if cc_pid not in cc_metrics:
                logger.warning(
                    f"Match {match.id}: No CC metrics for player {mp.player_id} (pid={cc_pid})"
                )
                continue

            stats = cc_metrics[cc_pid]

            # Get or create metrics record
            metrics = (
                session.query(PlayerMatchMetrics)
                .filter(PlayerMatchMetrics.match_player_id == mp.id)
                .first()
            )

            if not metrics:
                metrics = PlayerMatchMetrics(match_player_id=mp.id)
                session.add(metrics)

            # Update with CC data
            metrics.minerals_collected = int(stats.get("collected_minerals", 0))
            metrics.vespene_collected = int(stats.get("collected_vespene", 0))
            metrics.resources_spent = int(
                stats.get("spent_minerals", 0) + stats.get("spent_vespene", 0)
            )

            # Actual HP damage (not cost-based)
            metrics.damage_dealt = int(stats.get("total_damage_dealt", 0))
            metrics.damage_taken = int(stats.get("total_damage_taken", 0))

            # Army values
            metrics.army_value_killed = int(stats.get("total_killed_value", 0))
            metrics.army_value_built = int(
                stats.get("total_value_units", 0)
                + stats.get("total_value_structures", 0)
            )

            updated += 1
            logger.debug(
                f"  Player {mp.player_id}: minerals={metrics.minerals_collected}, "
                f"damage={metrics.damage_dealt}"
            )

        session.commit()
        logger.info(f"Match {match.id}: Updated {updated}/{num_players} players")
        return updated > 0

    except Exception as e:
        logger.error(f"Match {match.id}: Error processing - {e}", exc_info=True)
        session.rollback()
        return False


def main():
    """Main backfill entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill CommandCenter metrics for existing matches"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess all matches, even those with existing metrics",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Only process N matches"
    )
    parser.add_argument(
        "--match-id", type=int, default=None, help="Process a specific match by ID"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("CommandCenter Metrics Backfill Script")
    logger.info("=" * 60)

    # Check if CC parser is available
    if not is_commandcenter_available():
        logger.error("CommandCenter parser is not available!")
        logger.error("Please ensure:")
        logger.error("  1. StarCraft II is installed at ~/StarCraftII")
        logger.error("  2. library.so is in backend/app/lib/")
        sys.exit(1)

    # Initialize CC parser
    try:
        cc_parser = get_commandcenter_parser()
        if not cc_parser:
            logger.error("Failed to initialize CommandCenter parser")
            sys.exit(1)
        logger.info(f"CommandCenter parser initialized: {cc_parser.exe_path}")
    except Exception as e:
        logger.error(f"Failed to initialize CommandCenter parser: {e}")
        sys.exit(1)

    # Setup database
    db_url = get_database_url()
    logger.info(f"Database: {db_url}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Build query
        query = session.query(Match).order_by(Match.id)

        if args.match_id:
            query = query.filter(Match.id == args.match_id)

        matches = query.all()
        total = len(matches)
        logger.info(f"Found {total} matches in database")

        if total == 0:
            logger.info("No matches to process")
            return

        # Filter to matches needing processing
        if not args.force and not args.match_id:
            matches = [
                m for m in matches if match_needs_cc_metrics(session, m, args.force)
            ]
            logger.info(f"{len(matches)} matches need CC metrics backfill")

        if args.limit:
            matches = matches[: args.limit]
            logger.info(f"Processing limited to {args.limit} matches")

        if not matches:
            logger.info("No matches to process")
            return

        # Process each match
        success = 0
        failed = 0
        skipped = 0

        for i, match in enumerate(matches, 1):
            logger.info(f"[{i}/{len(matches)}] Match {match.id}...")

            result = backfill_match_cc_metrics(
                session, cc_parser, match, dry_run=args.dry_run
            )

            if result:
                success += 1
            else:
                failed += 1

            # Progress update every 10 matches
            if i % 10 == 0:
                logger.info(
                    f"Progress: {i}/{len(matches)} ({success} success, {failed} failed)"
                )

        # Final summary
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"  Total processed: {len(matches)}")
        logger.info(f"  Successful: {success}")
        logger.info(f"  Failed: {failed}")
        if args.dry_run:
            logger.info("  (DRY RUN - no changes made)")
        logger.info("=" * 60)

    finally:
        session.close()


if __name__ == "__main__":
    main()
