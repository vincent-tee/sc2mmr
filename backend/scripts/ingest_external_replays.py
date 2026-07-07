import sys
import os
from pathlib import Path
import logging
import shutil

backend_path = Path("/home/vtee/projects/sc2mmr/backend")
sys.path.insert(0, str(backend_path))

from app.database import SessionLocal
from app.services.match_orchestrator import MatchOrchestrator
from app.exceptions import DuplicateReplayError, DuplicateGameError, ReplayParseError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_folders(folders: list[str]):
    db = SessionLocal()
    orchestrator = MatchOrchestrator(db)
    dest_replay_dir = backend_path / "replays"
    dest_replay_dir.mkdir(exist_ok=True)

    total_found = 0
    total_ingested = 0
    total_duplicates = 0
    total_errors = 0

    for folder in folders:
        logger.info(f"Scanning folder: {folder}")
        p = Path(folder)
        if not p.exists():
            logger.warning(f"Folder does not exist: {folder}")
            continue

        for file_path in p.rglob("*.SC2Replay"):
            total_found += 1
            try:
                filename = file_path.name

                logger.info(f"Processing: {filename}")
                result = orchestrator.orchestrate_match(
                    file_path=str(file_path),
                    filename=filename,
                    use_advanced_parser=True,
                )

                total_ingested += 1
                logger.info(f"Successfully ingested {filename}")

            except (DuplicateReplayError, DuplicateGameError):
                total_duplicates += 1
                logger.info(f"Skipping duplicate: {file_path.name}")
            except Exception as e:
                total_errors += 1
                logger.error(f"Error processing {file_path.name}: {e}")
                db.rollback()

    logger.info(f"Ingestion complete.")
    logger.info(f"Found: {total_found}")
    logger.info(f"Ingested: {total_ingested}")
    logger.info(f"Duplicates: {total_duplicates}")
    logger.info(f"Errors: {total_errors}")
    db.close()


if __name__ == "__main__":
    external_folders = [
        "/mnt/c/Users/tru_n/Downloads/Theology SC2-20260104T140325Z-3-001/Theology SC2",
        "/mnt/c/Users/tru_n/Documents/StarCraft II/Accounts/396750040/1-S2-1-11883598/Replays/Multiplayer",
    ]
    ingest_folders(external_folders)
