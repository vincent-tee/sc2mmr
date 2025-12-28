#!/usr/bin/env python3
"""
Launcher for the ReplayObserver service.
Runs as a standalone process to monitor SC2 replays.
"""

import sys
import os
import logging
import time
import signal

# Add the backend directory to the Python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_dir)

from app.services.replay_observer import ReplayObserverService
from app.config import settings


import argparse


def setup_logging():
    """Configure logging for the observer."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(backend_dir, "replay_observer.log")),
        ],
    )
    # Reduce noise from sc2reader
    logging.getLogger("sc2reader").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="Start the ReplayObserver service.")
    parser.add_argument(
        "--force", action="store_true", help="Force reprocess all replays in directory."
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("ReplayObserverLauncher")

    if not settings.observer_enabled:
        logger.warning("ReplayObserver is disabled in config. Exiting.")
        return

    logger.info("Initializing ReplayObserver service...")
    service = ReplayObserverService()

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Stopping observer...")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        service.start(force_reprocess_all=args.force)

        logger.info("Observer is running. Press Ctrl+C to stop.")

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except Exception as e:
        logger.error(f"Critical error in observer: {e}", exc_info=True)
        service.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
