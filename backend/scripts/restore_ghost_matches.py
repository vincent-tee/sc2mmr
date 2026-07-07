import sys
import os
from pathlib import Path
import logging

backend_path = Path("/home/vtee/projects/sc2mmr/backend")
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.database import SessionLocal, init_db
from app.models import Match, MatchPlayer
from app.services.match_orchestrator import MatchOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def restore_ghost_matches():
    db = SessionLocal()
    orchestrator = MatchOrchestrator(db)

    try:
        db.execute(
            text(
                "DELETE FROM player_match_metrics WHERE match_player_id NOT IN (SELECT id FROM match_players)"
            )
        )
        db.execute(
            text(
                "DELETE FROM performance_features WHERE match_player_id NOT IN (SELECT id FROM match_players)"
            )
        )
        db.commit()

        ghost_matches = (
            db.query(Match).outerjoin(MatchPlayer).filter(MatchPlayer.id == None).all()
        )
        logger.info(f"Found {len(ghost_matches)} ghost matches to restore.")

        restored_count = 0
        failed_count = 0

        for match in ghost_matches:
            match_id = match.id
            file_path = match.replay_file_path

            if not file_path or not os.path.exists(file_path):
                logger.warning(
                    f"Replay file not found for match {match_id}: {file_path}"
                )
                failed_count += 1
                continue

            logger.info(f"Restoring match {match_id} from {file_path}")

            try:
                db.execute(
                    text(
                        "DELETE FROM performance_features WHERE match_player_id IN (SELECT id FROM match_players WHERE match_id = :mid)"
                    ),
                    {"mid": match_id},
                )
                db.execute(
                    text(
                        "DELETE FROM player_match_metrics WHERE match_player_id IN (SELECT id FROM match_players WHERE match_id = :mid)"
                    ),
                    {"mid": match_id},
                )
                db.execute(
                    text("DELETE FROM match_players WHERE match_id = :mid"),
                    {"mid": match_id},
                )

                db.delete(match)
                db.commit()

                filename = os.path.basename(file_path)
                orchestrator.orchestrate_match(
                    file_path=file_path, filename=filename, use_advanced_parser=True
                )
                restored_count += 1
                logger.info(f"Successfully restored match {match_id}")
            except Exception as e:
                logger.error(f"Failed to restore match {match_id}: {e}")
                failed_count += 1
                db.rollback()

        logger.info(
            f"Restore complete. Restored: {restored_count}, Failed: {failed_count}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    restore_ghost_matches()
