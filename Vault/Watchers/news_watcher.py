"""
News Watcher - Generates content drafts from news sources.
Monitors Pakistani and international news RSS feeds and generates drafts
with critiques and hopeful angles, following the content rotation cycle.

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
    "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
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


class NewsWatcher(BaseWatcher):
    def __init__(self, vault_path: str):
        check_interval = int(os.getenv("NEWS_CHECK_INTERVAL", "7200"))
        super().__init__(vault_path, platform="news", check_interval=check_interval)

    def _get_feeds_and_keywords(self):
        """Return feeds and keywords based on current cycle position."""
        cycle = self.current_cycle_position
        if cycle in ("local_problem", "local_hopeful"):
            return LOCAL_FEEDS, LOCAL_KEYWORDS
        else:
            return GLOBAL_FEEDS, GLOBAL_KEYWORDS

    def check_for_updates(self) -> list:
        """Scan RSS feeds for newsworthy environment/climate stories."""
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
        """Create a news draft .md file in /Needs_Action/. Returns None if generation fails."""
        cycle = self.current_cycle_position
        draft_content = self.generate_draft_content(item, cycle, "News", self._get_cycle_instructions(cycle), 600)
        if draft_content is None:
            self.logger.error(f"Skipping draft creation for '{item['title']}' — content generation failed.")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"NEWS_{timestamp}_{item['id']}.md"
        filepath = self.inbox / filename

        content = f"""---
platform: News
status: pending
cycle_type: {cycle}
scope: {item.get('scope', 'local')}
source_title: "{item['title']}"
source_link: {item['link']}
source_published: "{item['published']}"
created: {datetime.now().isoformat()}
---

# News Draft — {cycle.replace('_', ' ').title()}

## Source Reference
- **Title:** {item['title']}
- **Summary:** {item['summary']}
- **Link:** {item['link']}
- **Published:** {item['published']}
- **Scope:** {item.get('scope', 'local').upper()} (Pakistan-focused)

## Content Instructions
Write a news analysis following the **{cycle.replace('_', ' ').title()}** pattern.

### Requirements:
{self._get_cycle_instructions(cycle)}

### News-Specific Requirements:
- Include a **critique** of current environmental policies or practices (local or global)
- Include a **hopeful angle** or actionable environmental recommendations
- All facts must be **verified, real, and include references**
- If the story is global, include a paragraph connecting to Pakistan's environmental context

## Draft Content

{draft_content}

## Key Facts to Verify
- [ ] Statistics cited are from credible environmental sources
- [ ] Case studies are real and recent (within 7-14 days)
- [ ] Expert quotes are attributed correctly
- [ ] Pakistan environmental connection is factual and relevant

## Sources & References
_[List all sources used for verification]_

---
*Generated by News Watcher v0.1*
"""
        filepath.write_text(content, encoding="utf-8")
        self.state.setdefault("processed_ids", []).append(item["id"])
        self.state["processed_ids"] = self.state["processed_ids"][-200:]
        self._save_state()
        self.logger.info(f"News draft created: {filename} (cycle: {cycle}, scope: {item.get('scope')})")
        return filepath

    def _get_cycle_instructions(self, cycle: str) -> str:
        instructions = {
            "local_problem": """- Deep dive into a **current environmental or climate crisis in Pakistan**
- Focus on: air pollution, water crisis, deforestation, floods, glacial melt, waste management, or biodiversity loss
- Include verified facts from Pakistan EPA, IPCC, WHO, UNDP, or academic research
- Critique existing environmental policies, enforcement gaps, or government inaction
- Provide context on affected communities, health costs, and ecological damage
- ALL content must be directly about Pakistan — not international stories""",
            "local_hopeful": """- Cover a **sustainability success story or green initiative in Pakistan**
- Highlight renewable energy projects, conservation programs, reforestation drives, or clean water solutions
- Include measurable environmental outcomes (emissions reduced, forests restored, species protected)
- Critique what still needs improvement in Pakistan's environmental policy
- End with recommendations for scaling green solutions nationally
- ALL content must be directly about Pakistan — not international stories""",
            "global_problem": """- Analyze a **major global environmental or climate crisis** currently in the news
- Focus on: extreme weather, ice melt, wildfires, ocean acidification, species extinction, or pollution
- Draw explicit parallels to Pakistan's environmental vulnerabilities
- Critique the global climate response and its implications for climate-vulnerable nations like Pakistan
- Highlight lessons from international climate science (IPCC, UNEP, COP)""",
            "global_hopeful": """- Cover **global green innovations, climate breakthroughs, or sustainability success stories**
- Analyze their applicability to Pakistan's environmental challenges
- Include data on proven results (renewable adoption rates, emission reductions, conservation wins)
- Critique barriers to adopting global green solutions in Pakistan
- Recommend actionable environmental steps for Pakistani policymakers and citizens""",
        }
        return instructions.get(cycle, "Follow the content rotation pattern.")


if __name__ == "__main__":
    vault = os.getenv("VAULT_PATH", "./Vault")
    watcher = NewsWatcher(vault)
    watcher.run()
