#!/usr/bin/env python3
"""
Train Build Order Classifier

Trains the K-means build order classifier on available data.

Usage:
    python backend/scripts/train_build_classifier.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.build_order_classifier import train_classifier, get_classifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Train the build order classifier."""
    logger.info("=" * 60)
    logger.info("Build Order Classifier Training")
    logger.info("=" * 60)

    # Setup database
    db_path = backend_path / "data" / "sc2mmr.db"
    db_url = f"sqlite:///{db_path}"
    logger.info(f"Database: {db_url}")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Train classifier
        result = train_classifier(session)

        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE")
        logger.info(f"  Status: {result.get('status')}")
        logger.info(f"  Samples: {result.get('samples', 0)}")

        if result.get('status') == 'clustering':
            logger.info(f"  Clusters: {result.get('clusters', 0)}")
            logger.info("  Using K-means clustering for classification")
        elif result.get('status') == 'rule_based':
            logger.info(f"  Reason: {result.get('reason', '')}")
            logger.info("  Using rule-based classification (fallback)")
        else:
            logger.warning("  No data available for training")

        logger.info("=" * 60)

        # Test on available data
        classifier = get_classifier()
        if result.get('samples', 0) > 0:
            logger.info("\nTesting classifier on first 5 builds...")
            from app.models import PerformanceFeatures
            pfs = session.query(PerformanceFeatures).filter(
                PerformanceFeatures.build_order_json.isnot(None)
            ).limit(5).all()

            for pf in pfs:
                archetype, confidence = classifier.classify_from_db(session, pf.match_player_id)
                logger.info(f"  MatchPlayer {pf.match_player_id}: {archetype} ({confidence:.0%})")

    finally:
        session.close()


if __name__ == "__main__":
    main()
