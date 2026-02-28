"""
Scheduled Run - Single-pass watcher execution for Task Scheduler.
Runs all three watchers once (no loop), generates drafts, and exits.
Designed to be called 2-3 times daily by Windows Task Scheduler.
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

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

# Cooldown: how many hours must pass before generating another draft
PLATFORM_COOLDOWN_HOURS = {
    "news": 24,
    "instagram": 48,
    "linkedin": 48,
}


def _is_on_cooldown(platform: str, vault_path: str) -> bool:
    """Return True if this platform already generated a draft within its cooldown window."""
    state_file = Path(vault_path) / "Watchers" / f".{platform}_state.json"
    if not state_file.exists():
        return False
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    last_draft = state.get("last_draft_date")
    if not last_draft:
        return False
    cooldown_hours = PLATFORM_COOLDOWN_HOURS.get(platform, 24)
    last_dt = datetime.fromisoformat(last_draft)
    return datetime.now() - last_dt < timedelta(hours=cooldown_hours)


def _save_draft_date(platform: str, vault_path: str):
    """Record the current datetime as last_draft_date in the platform state file."""
    state_file = Path(vault_path) / "Watchers" / f".{platform}_state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    except (json.JSONDecodeError, OSError):
        state = {}
    state["last_draft_date"] = datetime.now().isoformat()
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_once(platforms=None):
    vault_path = os.getenv("VAULT_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    logger.info(f"=== Scheduled run started at {datetime.now().isoformat()} ===")
    logger.info(f"Vault: {vault_path}")

    selected = platforms if platforms else list(ALL_WATCHERS.keys())
    watchers = [ALL_WATCHERS[p] for p in selected if p in ALL_WATCHERS]

    generated = []

    for platform_key, (name, watcher_class) in zip(selected, watchers):
        try:
            if _is_on_cooldown(platform_key, vault_path):
                cooldown_h = PLATFORM_COOLDOWN_HOURS.get(platform_key, 24)
                logger.info(f"{name}: Skipping — already generated a draft within the last {cooldown_h}h cooldown.")
                continue

            w = watcher_class(vault_path)
            cycle = w.current_cycle_position
            items = w.check_for_updates()
            if items:
                fp = w.create_content_file(items[0])
                if fp is None:
                    logger.error(f"{name}: Draft generation failed (API error). Skipping cycle advance.")
                    continue
                w.create_plan_file(fp.name)
                verified = w.auto_verify_and_complete(fp)
                w.advance_cycle()
                w.update_dashboard()
                _save_draft_date(platform_key, vault_path)
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
