"""
LinkedIn Watcher - Generates content drafts for LinkedIn.
Monitors trending topics via RSS feeds and generates Pakistan-focused content
following the rotation: Local Problem → Local Hopeful → Global Problem → Global Hopeful.

LOCAL cycles only use Pakistan feeds + Pakistan keywords.
GLOBAL cycles only use international feeds + global keywords.
"""

import os
import hashlib
import logging
from pathlib import Path
from datetime import datetime

import feedparser
from dotenv import load_dotenv
from base_watcher import BaseWatcher, is_environment_relevant, is_article_fresh

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Pakistan-only feeds (for local_problem / local_hopeful) ---
LOCAL_FEEDS = [
    "https://feeds.dawn.com/feed/",
    "https://www.geo.tv/rss/1/1",
    "https://tribune.com.pk/feed/home",
]

# --- International feeds (for global_problem / global_hopeful) ---
GLOBAL_FEEDS = [
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml",
    "https://www.theguardian.com/environment/rss",
    "https://news.un.org/feed/subscribe/en/news/topic/climate-change/feed/rss.xml",
]

# Pakistan-specific environment/climate keywords (for local cycles)
LOCAL_KEYWORDS = [
    "pakistan", "lahore", "karachi", "islamabad", "punjab", "sindh",
    "balochistan", "kpk", "khyber", "peshawar", "quetta", "faisalabad",
    "smog", "pollution", "flood", "drought", "glacier", "indus",
    "deforestation", "billion tree", "clean green", "thar", "tharparkar",
    "water crisis", "water scarcity", "heatwave", "heat wave",
    "climate", "environment", "renewable", "solar", "wind energy",
    "mangrove", "waste", "plastic", "air quality", "monsoon",
    "forest", "wildlife", "biodiversity", "conservation", "sustainable",
    "carbon", "emission", "green", "energy", "coal", "recycling",
    "reforestation", "afforestation", "ecosystem", "ecological",
]

# Global environment/climate keywords (for global cycles)
GLOBAL_KEYWORDS = [
    "climate", "climate change", "global warming", "sustainability",
    "renewable", "solar", "wind energy", "clean energy", "fossil fuel",
    "carbon", "emission", "greenhouse", "net zero", "paris agreement", "cop",
    "pollution", "air quality", "deforestation", "reforestation", "biodiversity",
    "conservation", "wildlife", "endangered", "ecosystem",
    "flood", "drought", "glacier", "sea level", "heat wave", "wildfire",
    "water scarcity", "desertification", "ozone", "mangrove", "wetland",
    "recycling", "waste", "circular economy", "sustainable development",
    "electric vehicle", "green energy", "environment", "ecological",
    "coral", "ocean", "plastic", "ice melt", "arctic", "antarctic",
]


class LinkedInWatcher(BaseWatcher):
    def __init__(self, vault_path: str):
        check_interval = int(os.getenv("LINKEDIN_CHECK_INTERVAL", "14400"))
        super().__init__(vault_path, platform="linkedin", check_interval=check_interval)

    def _get_feeds_and_keywords(self):
        """Return feeds and keywords based on current cycle position."""
        cycle = self.current_cycle_position
        if cycle in ("local_problem", "local_hopeful"):
            return LOCAL_FEEDS, LOCAL_KEYWORDS
        else:
            return GLOBAL_FEEDS, GLOBAL_KEYWORDS

    def check_for_updates(self) -> list:
        """Scan RSS feeds for trending topics relevant to LinkedIn posts."""
        feeds, keywords = self._get_feeds_and_keywords()
        cycle = self.current_cycle_position
        items = []

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:50]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    link = entry.get("link", "")
                    published = entry.get("published", "")

                    combined = f"{title} {summary}"
                    if is_environment_relevant(combined) and is_article_fresh(entry):
                        item_id = hashlib.md5(title.encode()).hexdigest()[:12]
                        if item_id not in self.state.get("processed_ids", []):
                            items.append({
                                "id": item_id,
                                "title": title,
                                "summary": summary,
                                "link": link,
                                "published": published,
                                "source": feed_url,
                                "scope": "local" if "local" in cycle else "global",
                            })
            except Exception as e:
                self.logger.warning(f"Failed to fetch feed {feed_url}: {e}")

        # Fallback: if no local articles found, try global feeds
        if not items and cycle in ("local_problem", "local_hopeful"):
            self.logger.info(f"No local articles found for {cycle}, falling back to global feeds")
            for feed_url in GLOBAL_FEEDS:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:50]:
                        title = entry.get("title", "")
                        summary = entry.get("summary", entry.get("description", ""))
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        combined = f"{title} {summary}"
                        if is_environment_relevant(combined):
                            item_id = hashlib.md5(title.encode()).hexdigest()[:12]
                            if item_id not in self.state.get("processed_ids", []):
                                items.append({
                                    "id": item_id,
                                    "title": title,
                                    "summary": summary,
                                    "link": link,
                                    "published": published,
                                    "source": feed_url,
                                    "scope": "local",
                                })
                except Exception as e:
                    self.logger.warning(f"Failed to fetch feed {feed_url}: {e}")

        return items[:1] if items else []

    def create_content_file(self, item) -> Path | None:
        """Create a LinkedIn draft .md file in /Needs_Action/. Returns None if generation fails."""
        cycle = self.current_cycle_position
        draft_content = self.generate_draft_content(item, cycle, "LinkedIn", self._get_cycle_instructions(cycle), 500)
        if draft_content is None:
            self.logger.error(f"Skipping draft creation for '{item['title']}' — content generation failed.")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LINKEDIN_{timestamp}_{item['id']}.md"
        filepath = self.inbox / filename

        content = f"""---
platform: LinkedIn
status: pending
cycle_type: {cycle}
scope: {item.get('scope', 'local')}
source_title: "{item['title']}"
source_link: {item['link']}
source_published: "{item['published']}"
created: {datetime.now().isoformat()}
word_target: 500
---

# LinkedIn Draft — {cycle.replace('_', ' ').title()}

## Source Reference
- **Title:** {item['title']}
- **Summary:** {item['summary']}
- **Link:** {item['link']}
- **Scope:** {item.get('scope', 'local').upper()} (Pakistan-focused)

## Content Instructions
Write a **500+ word** LinkedIn post following the **{cycle.replace('_', ' ').title()}** pattern.

### Requirements:
{self._get_cycle_instructions(cycle)}

## Draft Content

{draft_content}

## Verification Checklist
- [ ] Facts and statistics are accurate and cited
- [ ] Real case studies or examples included
- [ ] Pakistan context is highlighted
- [ ] Tone is professional and appropriate for LinkedIn
- [ ] Word count meets 500+ target
- [ ] Sources and references are verifiable

## Suggested Hashtags
#Pakistan #ClimateAction #Sustainability #RenewableEnergy #Environment #GreenPakistan #ClimateChange #NetZero

---
*Generated by LinkedIn Watcher v0.1*
"""
        filepath.write_text(content, encoding="utf-8")
        self.state.setdefault("processed_ids", []).append(item["id"])
        self.state["processed_ids"] = self.state["processed_ids"][-200:]
        self._save_state()
        self.logger.info(f"LinkedIn draft created: {filename} (cycle: {cycle}, scope: {item.get('scope')})")
        return filepath

    def _get_cycle_instructions(self, cycle: str) -> str:
        instructions = {
            "local_problem": """- Highlight a **current environmental or climate problem in Pakistan**
- Focus on: air pollution, water scarcity, deforestation, flooding, glacial melt, biodiversity loss, or waste crisis
- Include **facts, figures, case studies**, and credible references (IPCC, WHO, Pakistan EPA, UNDP)
- Mention affected communities, health impacts, and economic costs
- Use a professional, awareness-raising tone rooted in sustainability
- ALL content must be directly about Pakistan — not international stories""",
            "local_hopeful": """- Show **sustainability solutions, green initiatives, or environmental success stories** in Pakistan
- Highlight renewable energy projects, reforestation drives (e.g., Billion Tree Tsunami), clean water programs, or green startups
- Include measurable environmental impact (CO2 reduced, trees planted, communities helped)
- Connect to the previous environmental problem post's theme
- End with a call to action for sustainable practices
- ALL content must be directly about Pakistan — not international stories""",
            "global_problem": """- Highlight a **trending global environmental or climate crisis**
- Connect its **relevance or lessons for Pakistan's environment**
- Include IPCC data, UN reports, and international comparisons
- Show how global climate trends affect Pakistan specifically (floods, heat waves, glacial melt)
- Reference expert opinions from climate scientists or environmental institutions""",
            "global_hopeful": """- Showcase **global green innovations, climate solutions, or sustainability breakthroughs**
- Explain how they could **inspire environmental action in Pakistan**
- Highlight transferable clean energy, conservation, or circular economy strategies
- Include examples of international climate collaboration
- End with an actionable sustainability takeaway for Pakistani professionals""",
        }
        return instructions.get(cycle, "Follow the content rotation pattern.")


if __name__ == "__main__":
    vault = os.getenv("VAULT_PATH", "./Vault")
    watcher = LinkedInWatcher(vault)
    watcher.run()
