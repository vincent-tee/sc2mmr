"""
ReplayObserver - Background service to watch for new SC2 replays and process them.
"""

import logging
import os
import time
from pathlib import Path
from typing import Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from app.database import get_db_context
from app.config import settings
from app.services.replay_service import ReplayService
from app.replay_parser import calculate_replay_hash

logger = logging.getLogger(__name__)


class ReplayHandler(FileSystemEventHandler):
    """Handles file system events for SC2 replays."""

    def __init__(self, debounce_seconds: float = 2.0):
        self.debounce_seconds = debounce_seconds
        self.processing_hashes: Set[str] = set()

    def on_created(self, event):
        if not event.is_directory:
            src_path = (
                event.src_path.decode()
                if isinstance(event.src_path, bytes)
                else event.src_path
            )
            if src_path.endswith(".SC2Replay"):
                logger.info(f"New replay detected: {src_path}")
                self._process_with_debounce(src_path)

    def _process_with_debounce(self, file_path: str):
        """Wait for file to be fully written before processing."""
        time.sleep(self.debounce_seconds)

        try:
            with get_db_context() as db:
                service = ReplayService(db)

                # Calculate hash to check if we've already seen this
                replay_hash = calculate_replay_hash(file_path)

                if service.get_existing_match_by_hash(replay_hash):
                    logger.info(
                        f"Replay {os.path.basename(file_path)} already exists in database (Hash: {replay_hash[:10]}). Skipping."
                    )
                    return

                with open(file_path, "rb") as f:
                    content = f.read()

                logger.info(f"Processing new replay: {os.path.basename(file_path)}")
                result = service.process_replay(
                    file_content=content,
                    filename=os.path.basename(file_path),
                    use_advanced_parser=True,
                    use_cc_parser=settings.observer_use_cc_parser,
                )
                logger.info(f"Successfully processed Match #{result.match.id}")

        except Exception as e:
            logger.error(
                f"Error processing observed replay {file_path}: {e}", exc_info=True
            )


class ReplayObserverService:
    """Service that manages the watchdog observer and initial directory scan."""

    def __init__(self):
        self.watch_path = settings.watch_directory
        self.observer = Observer()
        self.handler = ReplayHandler(
            debounce_seconds=settings.observer_debounce_seconds
        )

    def start(self, force_reprocess_all: bool = False):
        """Start the observer and perform initial scan."""
        if not os.path.exists(self.watch_path):
            logger.warning(f"Watch directory does not exist: {self.watch_path}")
            # Try to create it if it's within the project, otherwise just fail
            if "/home/vtee/projects/sc2mmr" in self.watch_path:
                os.makedirs(self.watch_path, exist_ok=True)
                logger.info(f"Created watch directory: {self.watch_path}")
            else:
                logger.error("Cannot start observer: invalid watch directory.")
                return

        if settings.observer_initial_scan:
            self.perform_initial_scan(force_reprocess_all=force_reprocess_all)

        logger.info(f"Starting ReplayObserver on: {self.watch_path}")
        self.observer.schedule(self.handler, self.watch_path, recursive=False)
        self.observer.start()

    def stop(self):
        """Stop the observer."""
        self.observer.stop()
        self.observer.join()
        logger.info("ReplayObserver stopped.")

    def perform_initial_scan(self, force_reprocess_all: bool = False):
        """Scan directory for any replays not yet in the database or missing metrics."""
        logger.info(
            f"Performing initial scan of {self.watch_path} (Force: {force_reprocess_all})..."
        )
        replay_files = list(Path(self.watch_path).glob("*.SC2Replay"))
        logger.info(f"Found {len(replay_files)} files in directory.")

        processed_count = 0
        skipped_count = 0

        with get_db_context() as db:
            from app.models import MatchPlayer, PlayerMatchMetrics

            service = ReplayService(db)
            for file_path in replay_files:
                try:
                    str_path = str(file_path)
                    replay_hash = calculate_replay_hash(str_path)

                    match = service.get_existing_match_by_hash(replay_hash)
                    if match:
                        if force_reprocess_all:
                            logger.info(f"Forcing reprocess: {file_path.name}")
                            if service.reprocess_match_metrics(
                                str_path,
                                match,
                                use_cc_parser=settings.observer_use_cc_parser,
                            ):
                                processed_count += 1
                            else:
                                skipped_count += 1
                            continue

                        # Check if this match has detailed metrics
                        metrics = (
                            db.query(PlayerMatchMetrics)
                            .join(MatchPlayer)
                            .filter(MatchPlayer.match_id == match.id)
                            .all()
                        )

                        has_metrics = len(metrics) > 0
                        # Check for 0 values which indicate bad old parsing
                        total_minerals = sum(
                            me.minerals_collected or 0 for me in metrics
                        )
                        total_damage = sum(me.damage_dealt or 0 for me in metrics)

                        # We reprocess if it has 0 minerals (impossible in a real game)
                        # Or if it's missing metrics entirely
                        is_incomplete = not has_metrics or total_minerals < 100

                        if not is_incomplete:
                            skipped_count += 1
                            continue

                        logger.info(
                            f"Match exists but metrics are incomplete (Min: {total_minerals}, Dmg: {total_damage}). Backfilling: {file_path.name}"
                        )
                        if service.reprocess_match_metrics(
                            str_path,
                            match,
                            use_cc_parser=settings.observer_use_cc_parser,
                        ):
                            processed_count += 1
                        else:
                            skipped_count += 1
                        continue

                    logger.info(f"Syncing missing replay: {file_path.name}")

                    with open(str_path, "rb") as f:
                        content = f.read()

                    service.process_replay(
                        file_content=content,
                        filename=file_path.name,
                        use_advanced_parser=True,
                        use_cc_parser=settings.observer_use_cc_parser,
                    )
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync {file_path.name}: {e}")

        logger.info(
            f"Initial scan complete. Processed/Backfilled: {processed_count}, Skipped: {skipped_count}"
        )


if __name__ == "__main__":
    # Basic CLI runner for testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    service = ReplayObserverService()
    try:
        service.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
