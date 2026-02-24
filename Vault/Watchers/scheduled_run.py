"""
Scheduled Run - Single-pass watcher execution for Task Scheduler.
Runs all three watchers once (no loop), generates drafts, and exits.
Designed to be called 2-3 times daily by Windows Task Scheduler.
"""

import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from linkedin_watcher import LinkedInWatcher
from instagram_watcher import InstagramWatcher
from news_watcher import NewsWatcher

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "scheduled_run.log")),
    ],
)
logger = logging.getLogger("ScheduledRun")


def run_once():
    vault_path = os.getenv("VAULT_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    logger.info(f"=== Scheduled run started at {datetime.now().isoformat()} ===")
    logger.info(f"Vault: {vault_path}")

    watchers = [
        ("LinkedIn", LinkedInWatcher),
        ("Instagram", InstagramWatcher),
        ("News", NewsWatcher),
    ]

    generated = []

    for name, watcher_class in watchers:
        try:
            w = watcher_class(vault_path)
            cycle = w.current_cycle_position
            items = w.check_for_updates()
            if items:
                fp = w.create_content_file(items[0])
                w.create_plan_file(fp.name)
                w.advance_cycle()
                w.update_dashboard()
                generated.append({
                    "platform": name,
                    "file": fp.name,
                    "cycle": cycle,
                    "title": items[0]["title"],
                })
                logger.info(f"{name}: Draft created -> {fp.name} (cycle: {cycle})")
            else:
                logger.info(f"{name}: No new matching items found (cycle: {cycle})")
        except Exception as e:
            logger.error(f"{name}: Error - {e}")

    logger.info(f"=== Scheduled run complete. {len(generated)} drafts generated. ===")
    return generated


if __name__ == "__main__":
    run_once()
