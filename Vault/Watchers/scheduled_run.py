"""
Scheduled Run - Single-pass watcher execution for Task Scheduler.
Runs all three watchers once (no loop), generates drafts, and exits.
Designed to be called 2-3 times daily by Windows Task Scheduler.
"""

import sys
import os
import logging
import argparse
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

ALL_WATCHERS = {
    "linkedin": ("LinkedIn", LinkedInWatcher),
    "instagram": ("Instagram", InstagramWatcher),
    "news": ("News", NewsWatcher),
}


def run_once(platforms=None):
    vault_path = os.getenv("VAULT_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    logger.info(f"=== Scheduled run started at {datetime.now().isoformat()} ===")
    logger.info(f"Vault: {vault_path}")

    selected = platforms if platforms else list(ALL_WATCHERS.keys())
    watchers = [ALL_WATCHERS[p] for p in selected if p in ALL_WATCHERS]

    generated = []

    for name, watcher_class in watchers:
        try:
            w = watcher_class(vault_path)
            cycle = w.current_cycle_position
            items = w.check_for_updates()
            if items:
                fp = w.create_content_file(items[0])
                w.create_plan_file(fp.name)
                verified = w.auto_verify_and_complete(fp)
                w.advance_cycle()
                w.update_dashboard()
                generated.append({
                    "platform": name,
                    "file": fp.name,
                    "cycle": cycle,
                    "title": items[0]["title"],
                    "verified": verified,
                })
                logger.info(f"{name}: Draft created -> {fp.name} (cycle: {cycle}, verified: {verified})")
            else:
                logger.info(f"{name}: No new matching items found (cycle: {cycle})")
        except Exception as e:
            logger.error(f"{name}: Error - {e}")

    logger.info(f"=== Scheduled run complete. {len(generated)} drafts generated. ===")
    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run content watchers for specified platforms")
    parser.add_argument(
        "--platform",
        nargs="+",
        choices=["linkedin", "instagram", "news"],
        help="Platforms to generate drafts for (default: all)",
    )
    args = parser.parse_args()
    run_once(platforms=args.platform)
