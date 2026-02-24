# AI Employee - Bronze Tier

## Project Overview
This is a Bronze Tier Personal AI Employee for the Hackathon 2026. It generates verified content drafts for LinkedIn, Instagram, and News platforms. **All content is strictly focused on sustainability, climate change, and environmental topics** — with Pakistan relevance and a Problem-to-Hope narrative cycle. **No posting or automation beyond drafting.**

## Vault Structure
The Obsidian vault is at `./Vault/` with these folders:
- `/Inbox` — Raw task drops
- `/Needs_Action` — Drafts awaiting verification and review
- `/Plans` — AI-generated task plans
- `/Completed` — Verified and approved content
- `/Watchers` — Python watcher scripts
- `/Logs` — Daily JSON action logs

## Key Files
- `Vault/Dashboard.md` — Real-time overview of pending drafts
- `Vault/Company_Handbook.md` — Rules, workflow, content standards

## Content Focus
All content must be about: **climate change, sustainability, environment, renewable energy, pollution, conservation, biodiversity, green technology, or natural disasters linked to climate.**

## Content Rotation Cycle
Always follow this sequence for each platform:
1. **Local Problem** — Environmental/climate crisis in Pakistan with facts and data
2. **Local Hopeful** — Green solutions and sustainability success stories in Pakistan
3. **Global Problem** — Global climate/environmental crisis connected to Pakistan
4. **Global Hopeful** — Global green innovations inspiring environmental action in Pakistan

## Content Standards
- LinkedIn: 500+ words, professional tone
- Instagram: 300+ words, engaging tone, image suggestions
- News: Analysis with critique + hopeful angle, verified facts
- All content must include real case studies, statistics, and references
- Only consider topics from the last 7-14 days

## Agent Skills (in `.claude/skills/`)
- `generate-content` — Create a content draft for any platform
- `verify-content` — Fact-check a draft in Needs_Action
- `review-drafts` — Review all pending drafts and summarize
- `update-dashboard` — Refresh Dashboard.md with current counts
- `process-inbox` — Process files dropped in Inbox

## Watcher Scripts (in `Vault/Watchers/`)
- `linkedin_watcher.py` — LinkedIn content from RSS feeds
- `instagram_watcher.py` — Instagram content from RSS feeds
- `news_watcher.py` — News analysis from RSS feeds
- `filesystem_watcher.py` — Monitors Inbox/Needs_Action folders
- `run_all_watchers.py` — Starts all watchers in parallel

## Rules
- AI only drafts content — never post externally
- All drafts must be human-verified before use
- Approved drafts go to `/Completed/`
- All actions are logged to `/Logs/`
