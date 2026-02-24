"""
File System Watcher - Monitors /Inbox and /Needs_Action folders for new files.
This is the required "one working Watcher script" for Bronze tier.
When new files are dropped into /Inbox, they are moved to /Needs_Action with metadata.
When files appear in /Needs_Action, they are logged for Claude processing.
"""

import os
import sys
import time
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("FileSystemWatcher")


class InboxHandler(FileSystemEventHandler):
    """Handles files dropped into /Inbox — moves them to /Needs_Action with metadata."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.logs = self.vault_path / "Logs"
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

    def on_created(self, event):
        if event.is_directory:
            return

        source = Path(event.src_path)

        # Skip hidden/system files
        if source.name.startswith(".") or source.name.startswith("~"):
            return

        # Wait briefly for file to finish writing
        time.sleep(0.5)

        logger.info(f"New file detected in Inbox: {source.name}")

        try:
            # Watcher-generated drafts (LINKEDIN_, INSTA_, NEWS_) keep their name
            name_upper = source.name.upper()
            if any(name_upper.startswith(p) for p in ["LINKEDIN_", "INSTA_", "NEWS_"]):
                dest = self.needs_action / source.name
            else:
                dest = self.needs_action / f"FILE_{source.name}"

            # Move file (not copy) from Inbox to Needs_Action
            shutil.move(str(source), str(dest))

            # Create metadata only for non-draft files
            if not any(name_upper.startswith(p) for p in ["LINKEDIN_", "INSTA_", "NEWS_"]):
                self._create_metadata(dest, dest)

            # Log the action
            self._log_action("file_intake", source.name, "success")

            logger.info(f"File processed: {source.name} → Needs_Action/{dest.name}")
        except Exception as e:
            logger.error(f"Error processing {source.name}: {e}")
            self._log_action("file_intake", source.name, f"failure: {e}")

    def _create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_name(dest.stem + "_meta.md")
        meta_content = f"""---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
received: {datetime.now().isoformat()}
status: pending
---

## File Drop
- **Original:** {source.name}
- **Size:** {source.stat().st_size} bytes
- **Received:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Action Required
- [ ] Review file contents
- [ ] Process or categorize
- [ ] Move to /Completed when done
"""
        meta_path.write_text(meta_content, encoding="utf-8")

    def _log_action(self, action_type: str, target: str, result: str):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.json"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": "filesystem_watcher",
            "target": target,
            "result": result,
        }

        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries = []

        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


class NeedsActionHandler(FileSystemEventHandler):
    """Monitors /Needs_Action for new drafts — logs them for Claude processing."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.logs = self.vault_path / "Logs"

    def on_created(self, event):
        if event.is_directory:
            return

        source = Path(event.src_path)
        if source.suffix != ".md" or source.name.startswith("."):
            return

        logger.info(f"New draft in Needs_Action: {source.name}")
        self._update_dashboard()

    def _update_dashboard(self):
        """Recalculate and update Dashboard.md counts."""
        needs_action = self.vault_path / "Needs_Action"
        completed = self.vault_path / "Completed"

        counts = {"LinkedIn": 0, "Instagram": 0, "News": 0}
        for f in needs_action.iterdir():
            if f.suffix == ".md":
                name = f.name.upper()
                if name.startswith("LINKEDIN_"):
                    counts["LinkedIn"] += 1
                elif name.startswith("INSTA_"):
                    counts["Instagram"] += 1
                elif name.startswith("NEWS_"):
                    counts["News"] += 1

        verified = {"LinkedIn": 0, "Instagram": 0, "News": 0}
        if completed.exists():
            for f in completed.iterdir():
                if f.suffix == ".md":
                    name = f.name.upper()
                    if name.startswith("LINKEDIN_"):
                        verified["LinkedIn"] += 1
                    elif name.startswith("INSTA_"):
                        verified["Instagram"] += 1
                    elif name.startswith("NEWS_"):
                        verified["News"] += 1

        dashboard = self.vault_path / "Dashboard.md"
        content = f"""---
last_updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
auto_refresh: true
---

# AI Employee Dashboard - Bronze Tier

## System Status
- **Mode:** Draft-Only (No Posting)
- **Tier:** Bronze
- **Watchers:** LinkedIn | Instagram | News

## Pending Content Drafts
| Platform   | Pending | Verified | Total |
|------------|---------|----------|-------|
| LinkedIn   | {counts['LinkedIn']}       | {verified['LinkedIn']}        | {counts['LinkedIn'] + verified['LinkedIn']}     |
| Instagram  | {counts['Instagram']}       | {verified['Instagram']}        | {counts['Instagram'] + verified['Instagram']}     |
| News       | {counts['News']}       | {verified['News']}        | {counts['News'] + verified['News']}     |

## Recent Activity
- [{datetime.now().strftime("%Y-%m-%d %H:%M")}] Dashboard auto-updated by filesystem watcher

## Folders Quick Links
- [[Inbox]] — Raw task drops
- [[Needs_Action]] — Drafts awaiting review
- [[Plans]] — AI-generated task plans
- [[Completed]] — Verified and approved content
- [[Logs]] — Action logs

---
*Updated by AI Employee v0.1 — Bronze Tier*
"""
        dashboard.write_text(content, encoding="utf-8")


def main():
    vault_path = os.getenv("VAULT_PATH", os.path.join(os.path.dirname(__file__), ".."))
    vault_path = os.path.abspath(vault_path)

    inbox_path = os.path.join(vault_path, "Inbox")
    needs_action_path = os.path.join(vault_path, "Needs_Action")

    # Ensure directories exist
    os.makedirs(inbox_path, exist_ok=True)
    os.makedirs(needs_action_path, exist_ok=True)

    logger.info(f"File System Watcher starting...")
    logger.info(f"  Vault: {vault_path}")
    logger.info(f"  Watching: {inbox_path}")
    logger.info(f"  Watching: {needs_action_path}")

    observer = Observer()
    observer.schedule(InboxHandler(vault_path), inbox_path, recursive=False)
    observer.schedule(NeedsActionHandler(vault_path), needs_action_path, recursive=False)
    observer.start()

    logger.info("File System Watcher is running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("File System Watcher stopped.")
    observer.join()


if __name__ == "__main__":
    main()
