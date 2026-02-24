"""
Run All Watchers - Starts LinkedIn, Instagram, and News watchers in parallel threads.
This is the main entry point for the Bronze Tier content generation system.
"""

import os
import sys
import logging
import threading
from dotenv import load_dotenv

# Add watchers directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from linkedin_watcher import LinkedInWatcher
from instagram_watcher import InstagramWatcher
from news_watcher import NewsWatcher

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("watchers.log"),
    ],
)

logger = logging.getLogger("WatcherOrchestrator")


def run_watcher(watcher_class, vault_path: str):
    """Run a single watcher in a thread with error recovery."""
    while True:
        try:
            watcher = watcher_class(vault_path)
            watcher.run()
        except KeyboardInterrupt:
            logger.info(f"{watcher_class.__name__} stopped by user")
            break
        except Exception as e:
            logger.error(f"{watcher_class.__name__} crashed: {e}. Restarting in 60s...")
            import time
            time.sleep(60)


def main():
    vault_path = os.getenv("VAULT_PATH", os.path.join(os.path.dirname(__file__), ".."))
    vault_path = os.path.abspath(vault_path)

    logger.info(f"Starting all watchers with vault: {vault_path}")
    logger.info("Press Ctrl+C to stop all watchers")

    watchers = [
        ("LinkedIn", LinkedInWatcher),
        ("Instagram", InstagramWatcher),
        ("News", NewsWatcher),
    ]

    threads = []
    for name, watcher_class in watchers:
        t = threading.Thread(
            target=run_watcher,
            args=(watcher_class, vault_path),
            name=f"{name}Thread",
            daemon=True,
        )
        t.start()
        threads.append(t)
        logger.info(f"{name} watcher started")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("All watchers stopped")


if __name__ == "__main__":
    main()
