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
from datetime import datetime, timezone, timedelta

from openai import OpenAI

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


def is_article_fresh(entry, max_age_days: int = 7) -> bool:
    """Return True if the RSS entry was published within the last max_age_days days.
    If the entry has no parseable date, it is accepted (fail-open)."""
    published_parsed = getattr(entry, "published_parsed", None)
    if not published_parsed:
        return True  # no date info — don't reject it
    try:
        import calendar
        pub_dt = datetime.fromtimestamp(calendar.timegm(published_parsed), tz=timezone.utc)
        age = datetime.now(tz=timezone.utc) - pub_dt
        return age <= timedelta(days=max_age_days)
    except Exception:
        return True  # if parsing fails, accept the article


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
        """Call OpenAI API to generate actual draft content."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            self.logger.warning("OPENAI_API_KEY not set — returning empty draft")
            return "_Draft pending generation — OPENAI_API_KEY not configured._"

        client = OpenAI(api_key=api_key)

        platform_style = {
            "LinkedIn": "professional LinkedIn post (500+ words, formal tone, include statistics and references, end with a call to action)",
            "Instagram": "engaging Instagram caption (300+ words, conversational tone, include an image suggestion and hashtags)",
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

**STRICT CONTENT RULES — violating these will cause the draft to be rejected:**
- Write {word_target}+ words of actual content — no placeholders or instructions
- ONLY include statistics and figures you are 100% certain are accurate and widely documented — if unsure, describe the situation qualitatively instead
- DO NOT fabricate or estimate specific numbers, percentages, hectares, MW capacities, or population figures
- Every specific statistic or factual claim MUST have an inline citation like [1], [2] etc.
- The content MUST be directly relevant to the source article topic — do not invent unrelated case studies
- Always connect to Pakistan's environmental context
- Write in a compelling, human voice — not robotic or generic
- Do NOT include meta-instructions — just the actual post/article

After the article, include a REFERENCES section in this exact format:
**References:**
[1] Source Name — full URL or publication name and year
[2] Source Name — full URL or publication name and year
(list every reference cited inline)

Write the full content now:"""

        last_error = None
        for attempt in range(1, 4):  # retry up to 3 times
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    timeout=30,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                self.logger.warning(f"OpenAI API attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(5 * attempt)  # 5s, 10s back-off
        self.logger.error(f"OpenAI API failed after 3 attempts: {last_error}")
        return None

    def auto_verify_and_complete(self, filepath: Path) -> bool:
        """Fact-check a draft via OpenAI, mark as verified, and move to /Completed/."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            self.logger.warning("OPENAI_API_KEY not set — skipping auto-verification")
            return False

        content = filepath.read_text(encoding="utf-8")

        # Extract body (strip frontmatter)
        body = content
        if body.startswith("---"):
            end = body.find("---", 3)
            if end != -1:
                body = body[end + 3:].strip()

        client = OpenAI(api_key=api_key)
        prompt = f"""You are a strict fact-checker for an AI content system focused on sustainability and climate change in Pakistan.

Review the following draft content with a critical eye. Your job is to REJECT content that contains fabricated or unverifiable statistics.

Check each factual claim against these criteria:
1. Is the specific number/percentage/figure a well-known, documented fact? (e.g. Quaid-e-Azam Solar Park is 500 acres and ~400 MW operational — not 6,500 acres or 1,000 MW)
2. Does the claim have a real named source cited in the text?
3. Is the content actually relevant to the source article topic — or did the AI invent unrelated case studies?
4. Are any statistics suspiciously precise without a source? (e.g. "25% increase in productivity", "5% emissions reduction") — flag these

Return your verdict in EXACTLY this format:
- Status: Verified OR Needs Review
- Verified Claims: [count]
- Flagged Items: [list each suspicious or wrong statistic specifically, or write "None"]
- Notes: [one sentence]

IMPORTANT: If ANY specific statistic is unverifiable or appears fabricated, set Status to "Needs Review". Be strict — do not pass content with made-up numbers.

Draft content:
{body[:3000]}"""

        verification_result = None
        for attempt in range(1, 4):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    timeout=30,
                )
                verification_result = response.choices[0].message.content
                break
            except Exception as e:
                self.logger.warning(f"Auto-verification attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    time.sleep(5 * attempt)
        if not verification_result:
            self.logger.error("Auto-verification failed after 3 attempts")
            return False

        # Determine pass/fail from result — must explicitly say Verified AND have no flagged items
        result_lower = verification_result.lower()
        explicitly_verified = "status: verified" in result_lower
        has_flagged_items = (
            "flagged items:" in result_lower
            and "flagged items: none" not in result_lower
            and "flagged items: n/a" not in result_lower
        )
        verified = explicitly_verified and not has_flagged_items
        new_status = "verified" if verified else "needs_review"

        # Update frontmatter status
        import re
        updated = re.sub(r"^(status:\s*).*$", f"\\1{new_status}", content, count=1, flags=re.MULTILINE)

        # Append verification section
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        updated += f"""
## Verification Results
{verification_result}
- **Verified By:** AI Employee (auto)
- **Verified On:** {now}
"""
        # Move to /Completed/ if verified, otherwise update in place
        if verified:
            completed_dir = self.vault_path / "Completed"
            completed_dir.mkdir(exist_ok=True)
            dest = completed_dir / filepath.name
            dest.write_text(updated, encoding="utf-8")
            filepath.unlink()
            self.logger.info(f"Auto-verified and moved to /Completed/: {filepath.name}")
        else:
            filepath.write_text(updated, encoding="utf-8")
            self.logger.info(f"Auto-verification flagged issues, kept in /Needs_Action/: {filepath.name}")

        return verified

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
