#!/usr/bin/env python3
"""
Backfill ML Features Script

Re-processes existing matches to extract ML-ready features from replay files.
This populates the performance_features table without re-uploading replays.

Usage:
    python backend/scripts/backfill_ml_features.py

Note: Requires replay files to still be accessible at their original paths.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Match, MatchPlayer, PerformanceFeatures
from app.services.ml_features_service import MLFeaturesService
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from settings."""
    db_path = Path(backend_path) / "data" / "sc2mmr.db"
    return f"sqlite:///{db_path}"


def get_replay_storage_dirs() -> list[Path]:
    """Get possible replay storage directories."""
    return [
        backend_path / "failed_replays",
        backend_path / "replays",
        backend_path / "data" / "replays",
        Path.home() / "Documents" / "StarCraft II" / "Accounts",
    ]


def find_replay_file(match: Match) -> Path | None:
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
                    if match.replay_hash in replay_file.name:
                        return replay_file

    return None


def backfill_match(session, match: Match) -> bool:
    """
    Backfill ML features for a single match.

    Args:
        session: Database session
        match: Match to process

    Returns:
        True if successful, False otherwise
    """
    # Check if already has features
    existing = session.query(PerformanceFeatures).join(MatchPlayer).filter(
        MatchPlayer.match_id == match.id
    ).first()

    if existing and existing.build_order_json:
        logger.debug(f"Match {match.id} already has ML features, skipping")
        return True

    # Find replay file
    replay_path = find_replay_file(match)
    if not replay_path:
        logger.warning(f"Match {match.id}: Replay file not found")
        return False

    try:
        logger.info(f"Processing match {match.id} from {replay_path}")
        results = MLFeaturesService.extract_and_save_ml_features(
            session, str(replay_path), match.id
        )

        if results:
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"Match {match.id}: {success_count}/{len(results)} players processed")
            return success_count > 0
        return False

    except Exception as e:
        logger.error(f"Match {match.id}: Error processing - {e}")
        return False


def main():
    """Main backfill entry point."""
    logger.info("=" * 60)
    logger.info("ML Features Backfill Script")
    logger.info("=" * 60)

    # Setup database
    db_url = get_database_url()
    logger.info(f"Database: {db_url}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all matches
        matches = session.query(Match).order_by(Match.id).all()
        total = len(matches)
        logger.info(f"Found {total} matches to process")

        if total == 0:
            logger.info("No matches to process")
            return

        # Process each match
        success = 0
        skipped = 0
        failed = 0

        for i, match in enumerate(matches, 1):
            logger.info(f"[{i}/{total}] Processing match {match.id}...")

            result = backfill_match(session, match)
            if result:
                success += 1
            else:
                failed += 1

            # Progress update every 10 matches
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{total} ({success} success, {failed} failed)")

        # Final summary
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"  Total matches: {total}")
        logger.info(f"  Successful: {success}")
        logger.info(f"  Failed: {failed}")
        logger.info("=" * 60)

    finally:
        session.close()


if __name__ == "__main__":
    main()
