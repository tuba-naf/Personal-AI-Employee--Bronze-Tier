"""
Base Watcher - Template for all content watchers.
All watchers inherit from this class and implement check_for_updates() and create_content_file().
"""

import os
import time
import logging
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime

import anthropic

# --- Strict environment/climate keyword matching ---
# PRIMARY: Article MUST contain at least 1 of these (core environmental terms)
PRIMARY_KEYWORDS = [
    "climate", "climate change", "global warming", "sustainability",
    "pollution", "air pollution", "water pollution", "smog",
    "deforestation", "reforestation", "afforestation", "biodiversity",
    "renewable energy", "solar energy", "wind energy", "clean energy",
    "carbon emission", "greenhouse gas", "net zero",
    "flood", "drought", "glacier", "sea level rise",
    "conservation", "endangered species", "ecosystem",
    "recycling", "plastic waste", "waste management",
    "environmental", "ecological", "climate action",
    "fossil fuel", "coal plant", "carbon footprint",
    "water scarcity", "water crisis", "desertification",
    "mangrove", "wetland", "coral reef", "ozone",
    "wildfire", "heat wave", "ice melt",
    "electric vehicle", "circular economy",
    "billion tree", "clean green", "green energy",
]

# SECONDARY: Article must ALSO contain at least 1 of these (supporting context)
SECONDARY_KEYWORDS = [
    "pakistan", "environment", "climate", "pollution", "emission",
    "renewable", "solar", "wind", "forest", "water",
    "sustainable", "green", "carbon", "ecological", "conservation",
    "biodiversity", "wildlife", "waste", "recycling", "energy",
    "flood", "drought", "glacier", "ocean", "plastic",
    "temperature", "warming", "clean", "toxic", "hazardous",
    "species", "habitat", "nature", "earth", "planet",
]


def is_environment_relevant(text: str, min_primary: int = 1, min_secondary: int = 1) -> bool:
    """Check if text is genuinely about environment/climate/sustainability."""
    text_lower = text.lower()
    primary_hits = sum(1 for kw in PRIMARY_KEYWORDS if kw in text_lower)
    secondary_hits = sum(1 for kw in SECONDARY_KEYWORDS if kw in text_lower)
    return primary_hits >= min_primary and secondary_hits >= min_secondary


class BaseWatcher(ABC):
    CYCLE_ORDER = ["local_problem", "local_hopeful", "global_problem", "global_hopeful"]

    def __init__(self, vault_path: str, platform: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.inbox = self.vault_path / "Inbox"
        self.needs_action = self.vault_path / "Needs_Action"
        self.plans = self.vault_path / "Plans"
        self.logs = self.vault_path / "Logs"
        self.platform = platform
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure directories exist
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.plans.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

        # Track content rotation
        self.state_file = self.vault_path / "Watchers" / f".{platform}_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        return {"cycle_index": 0, "processed_ids": [], "last_run": None}

    def _save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    @property
    def current_cycle_position(self) -> str:
        return self.CYCLE_ORDER[self.state["cycle_index"] % len(self.CYCLE_ORDER)]

    def advance_cycle(self):
        self.state["cycle_index"] = (self.state["cycle_index"] + 1) % len(self.CYCLE_ORDER)
        self._save_state()

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new content items to process."""
        pass

    @abstractmethod
    def create_content_file(self, item) -> Path:
        """Create .md file in Needs_Action folder."""
        pass

    def create_plan_file(self, draft_filename: str) -> Path:
        """Create a Plan.md for processing this draft."""
        plan_content = f"""---
created: {datetime.now().isoformat()}
status: pending
platform: {self.platform}
draft_file: {draft_filename}
---

## Objective
Process the draft from /Needs_Action/{draft_filename}

## Steps
- [ ] Read draft content
- [ ] Verify facts and references
- [ ] Edit tone and clarity
- [ ] Move draft to /Completed
"""
        plan_path = self.plans / f"PLAN_{draft_filename}"
        plan_path.write_text(plan_content, encoding="utf-8")
        self.logger.info(f"Plan created: {plan_path.name}")
        return plan_path

    def log_action(self, action_type: str, target: str, result: str):
        """Log watcher action to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.json"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": f"{self.platform}_watcher",
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

    def update_dashboard(self):
        """Update Dashboard.md with current draft counts."""
        dashboard_path = self.vault_path / "Dashboard.md"
        if not dashboard_path.exists():
            return

        # Count drafts per platform in Needs_Action
        counts = {"LinkedIn": 0, "Instagram": 0, "News": 0}
        for f in self.needs_action.iterdir():
            if f.suffix == ".md":
                name = f.name.upper()
                if name.startswith("LINKEDIN_"):
                    counts["LinkedIn"] += 1
                elif name.startswith("INSTA_"):
                    counts["Instagram"] += 1
                elif name.startswith("NEWS_"):
                    counts["News"] += 1

        # Count verified in Completed
        completed = self.vault_path / "Completed"
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

## Content Rotation Status
- **Current Cycle Position:** {self.current_cycle_position.replace('_', ' ').title()}
- **Cycle:** Local Problem → Local Hopeful → Global Problem → Global Hopeful

## Folders Quick Links
- [[Inbox]] — Raw task drops
- [[Needs_Action]] — Drafts awaiting review
- [[Plans]] — AI-generated task plans
- [[Completed]] — Verified and approved content
- [[Logs]] — Action logs

---
*Updated by AI Employee v0.1 — Bronze Tier*
"""
        dashboard_path.write_text(content, encoding="utf-8")
        self.logger.info("Dashboard updated")

    def generate_draft_content(self, item: dict, cycle: str, platform: str, cycle_instructions: str, word_target: int) -> str:
        """Call Claude API to generate actual draft content."""
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            self.logger.warning("ANTHROPIC_API_KEY not set — returning empty draft")
            return "_Draft pending generation — ANTHROPIC_API_KEY not configured._"

        client = anthropic.Anthropic(api_key=api_key)

        platform_style = {
            "LinkedIn": "professional LinkedIn post (500+ words, formal tone, include statistics and references, end with a call to action)",
            "Instagram": "engaging Instagram caption (300+ words, conversational tone, include image suggestion and hashtags)",
            "News": "news analysis article (600+ words, journalistic tone, include critique and hopeful angle, cite sources)",
        }.get(platform, "content piece")

        prompt = f"""You are an expert sustainability and climate change content writer for Pakistan.

Write a complete, ready-to-publish {platform_style} based on the following source article.

**Source Article:**
- Title: {item['title']}
- Summary: {item['summary']}
- Published: {item['published']}
- Link: {item['link']}

**Content Cycle:** {cycle.replace('_', ' ').title()}

**Requirements:**
{cycle_instructions}

**Important rules:**
- Write {word_target}+ words of actual content — no placeholders or instructions
- Include real statistics, case studies, and references where relevant
- Always connect to Pakistan's environmental context
- Write in a compelling, human voice — not robotic or generic
- Do NOT include headings like "Draft Content" or meta-instructions — just the actual post/article

Write the full content now:"""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            return f"_Draft generation failed: {e}_"

    def run(self):
        """Main loop — check for updates and create content files."""
        self.logger.info(f"Starting {self.__class__.__name__} (interval: {self.check_interval}s)")
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    filepath = self.create_content_file(item)
                    if filepath:
                        self.create_plan_file(filepath.name)
                        self.log_action("content_draft", filepath.name, "success")
                        self.advance_cycle()
                self.state["last_run"] = datetime.now().isoformat()
                self._save_state()
                self.update_dashboard()
            except Exception as e:
                self.logger.error(f"Error in {self.__class__.__name__}: {e}")
                self.log_action("watcher_error", str(e), "failure")
            time.sleep(self.check_interval)
