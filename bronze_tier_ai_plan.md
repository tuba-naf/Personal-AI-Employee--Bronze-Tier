# Personal AI Employee Hackathon 2026 – Bronze Tier Plan

## Focus: Content Creation (LinkedIn, Instagram, News)

### Objective
Build a Bronze Tier Digital FTE that creates verified content drafts for LinkedIn, Instagram, and News sources. No posting or automation is included at this tier. The AI monitors sources, generates content drafts, verifies factual accuracy, and saves them for human review.

### Bronze Tier: Foundation (Minimum Viable Deliverable)
- Obsidian vault with `Dashboard.md` and `Company_Handbook.md`
- One working Watcher script (Gmail OR file system monitoring)
- Claude Code successfully reading from and writing to the vault
- Basic folder structure: `/Inbox`, `/Needs_Action`, `/Done`
- All AI functionality implemented as Agent Skills

---

## 1. Folder Structure

```
/Vault
    /Inbox           # Optional for raw task drop
    /Needs_Action    # Current drafts waiting verification
    /Plans           # Bronze Plan.md for AI task processing
    /Completed            # Completed tasks (verified/approved)
    /Watchers        # Watcher scripts per platform
Dashboard.md        # Pending drafts overview
Company_Handbook.md # Rules, engagement, workflow
```
### Bronze Tier Minimum Folders
- /Inbox – Raw tasks for AI watcher
- /Needs_Action – Draft content waiting verification
- /Plans – AI-generated plan templates for each task
- /Completed – Completed and verified tasks
- /Watchers – Scripts to monitor platforms
- Dashboard.md – Summarizes pending drafts
- Company_Handbook.md – Rules and workflow

# Dashboard - Bronze Tier

## Pending Content Drafts
- LinkedIn: 0
- Instagram: 0
- News: 0

# Company Handbook - Bronze Tier

## Rules
- AI only drafts content; no posting
- All drafts must be verified and approved by humans
- Completed drafts moved to /Completed 
- Watchers create Plans for new tasks automatically
## Notes
- Check /Needs_Action for new drafts
- Use Plans folder for AI-generated task plans

**Notes:**
- Each watcher writes content as `.md` files in `/Needs_Action/`.
- Human reviews drafts before moving them to `/Completed/`.

---

## 2. Watchers – Content Generation Scripts

### 2.1 LinkedIn Watcher
**Purpose:** Monitor LinkedIn for post inspiration, mentions, or trending topics.  
**Output:** Draft post saved in `/Needs_Action/`.

```python
class LinkedInWatcher:
    def check_for_updates(self):
        # Detect trending topics or latest issues
        return [{'text': 'Draft LinkedIn post: Pakistan’s urban air pollution problem and hope in renewable solutions'}]

    def create_content_file(self, item):
        filepath = f'./Vault/Needs_Action/LINKEDIN_{hash(item["text"])}.md'
        with open(filepath, 'w') as f:
            f.write(f'''---
platform: LinkedIn
status: pending
---

{item["text"]}
''')
        return filepath
```

**Content Example (500+ words, Problem → Hopeful)**
**Topic:** Urban Air Pollution in Pakistan → Renewable Energy Hope  
**Problem Post (Pakistan Context):**
Pakistan’s major cities, including Karachi, Lahore, and Islamabad, have been witnessing alarming levels of air pollution in recent years. According to the World Air Quality Report 2023, Lahore ranks among the 10 most polluted cities globally, with PM2.5 levels averaging 106 µg/m³, over 4 times the WHO recommended safe limit. This pollution has resulted in a surge of respiratory illnesses, heart disease, and premature deaths, particularly affecting children and the elderly. The primary sources include vehicle emissions, industrial discharge, and widespread burning of crop residues. For instance, during the 2023 rice harvesting season, smog from burning fields covered Punjab, causing school closures and hospital emergencies. Case studies from Karachi show that in winter 2022, hospitals reported a 35% increase in asthma-related visits compared to the previous year. Such conditions not only threaten public health but also contribute to economic losses exceeding $1.5 billion annually due to reduced workforce productivity and healthcare costs.

**Hopeful Post (Renewable Solutions & Positivity):**
Despite these challenges, Pakistan is slowly adopting renewable energy and green urban policies. The Lahore Metrobus Green Project and Karachi’s solar rooftop initiatives have shown that integrating renewable solutions can significantly reduce carbon emissions. Experts at the Pakistan Institute of Development Economics report that a 15% increase in solar energy adoption in urban households could reduce PM2.5 levels by up to 12% within five years. NGOs like Aahung and Clean Karachi are actively planting urban greenery, reducing dust, and raising public awareness. With rising investment in wind and solar farms in Sindh and Punjab, there is a tangible path toward cleaner air. By combining policy, public participation, and technological solutions, Pakistan can move from crisis to a hopeful, sustainable future.

---

### 2.2 Instagram Watcher
**Purpose:** Monitor hashtags, mentions, or relevant content trends.  
**Output:** Draft captions stored in `/Needs_Action/`.

```python
class InstagramWatcher:
    def check_for_updates(self):
        return [{'text': 'Draft Instagram caption: Inspiring sustainability in daily life!'}]

    def create_content_file(self, item):
        filepath = f'./Vault/Needs_Action/INSTA_{hash(item["text"])}.md'
        with open(filepath, 'w') as f:
            f.write(f'''---
platform: Instagram
status: pending
---

{item["text"]}
''')
        return filepath
```

**Content Example (300+ words, Problem → Hopeful)**
**Topic:** Water Scarcity in Pakistan → Community Water Projects  
**Problem Post:**
Pakistan faces one of the most severe water crises in South Asia. Per UNICEF 2023, more than 50 million Pakistanis lack access to safe drinking water, and 20 million are at risk of extreme scarcity by 2030. Karachi alone loses 37% of treated water due to leakage, while rural areas rely on unsafe hand pumps. Communities in Tharparkar report chronic dehydration and malnutrition, with children showing stunted growth due to contaminated water. The crisis is compounded by climate change, over-extraction of groundwater, and poor infrastructure.

**Hopeful Post:**
Positive strides are happening nationwide. NGOs like The Citizens Foundation and Aga Khan Development Network have launched community water filtration and rainwater harvesting projects. In Sindh, the Thar Desert Rainwater Initiative has provided clean water to over 12,000 families, showing that community-driven solutions can overcome systemic challenges. Instagram posts showcasing local heroes and sustainable practices inspire citizens to adopt simple measures—like rainwater collection, responsible water usage, and advocacy for improved infrastructure. Through education and action, Pakistanis are actively participating in building a resilient, water-secure future.

---

### 2.3 News Watcher
**Purpose:** Scan RSS feeds or news APIs to summarize articles into content ideas.  
**Output:** Draft content in `/Needs_Action/`.


```python
class NewsWatcher:
    def check_for_updates(self):
        return [
            {'title': 'Global Floods in 2026', 'summary': 'Extreme flooding in Europe and Asia linked to climate change.'},
            {'title': 'Local Deforestation Crisis', 'summary': 'Pakistan loses 2 million hectares of forest annually, impacting biodiversity.'}
        ]

    def create_content_file(self, item):
        filepath = f'./Vault/Needs_Action/NEWS_{hash(item["title"])}.md'
        with open(filepath, 'w') as f:
            f.write(f'''---
platform: News
status: pending
title: {item["title"]}
---

{item["summary"]}
''')
        return filepath
```

**Content Example:**
**Global Issue:** Extreme Flooding in Europe & Asia → Lessons for Pakistan  
- **Case:** 2026 floods in Germany and Bangladesh  
- **Connection:** Urban planning and emergency response lessons for Karachi and Lahore  
- **Critique:** Governments slow to implement climate-adaptive infrastructure  
- **Hopeful angle:** NGOs and community preparedness programs reduce fatalities 
- Global news drafts must include a paragraph connecting the issue to Pakistan's context, highlighting lessons, risks, or opportunities.

**Local Issue:** Deforestation in Pakistan → Community Forestry Hope  
- **Fact:** Pakistan loses 2 million hectares annually, impacting wildlife  
- **Real story:** Community-led forestation in Northern Pakistan planted 500,000 saplings in 2023  
- **Critique:** Logging regulations poorly enforced  
- **Hopeful angle:** Youth-led climate initiatives show measurable improvement  

Content Sequencing & Rules:
- **Post Pattern Sequence:**
  1. **Local Issue / Problem Post:** Highlight a current, trending problem in Pakistan.
     - Include **facts, figures, case studies**, and credible references.
  2. **Local Hopeful / Positive Post:** Show solutions, success stories, or community initiatives addressing the same or related local issue.
  3. **Global Issue / Problem Post:** Highlight a trending global problem, then connect its **relevance or lessons for Pakistan**.
  4. **Global Hopeful / Positive Post:** Showcase global solutions, innovations, or success stories, and how they could **inspire local action** in Pakistan.
- **Alternating Pattern:** The AI should follow this cycle continuously for each platform (LinkedIn, Instagram, News) to maintain relevance, diversity, and positivity balance.
- **News Drafts Specifics:**
  - Include critiques of existing policies or practices (local or global).
  - Include hopeful angles or actionable recommendations.
  - Ensure all content is **verified, factual, and includes real-life examples**. 
  Content Rotation Rules:
- One post focuses on a local problem/issue in Pakistan.
- The next post highlights a local hopeful/positive solution.
- The following post addresses a global issue, connected back to Pakistan.
- The next post highlights global hopeful/positive developments connected to Pakistan.
- This sequence repeats continuously for all platforms.


---

## 3. Workflow – Bronze Tier
1. **Detection:** Watchers periodically check LinkedIn, Instagram, and News sources for content opportunities. 
---
created: 2026-02-23
status: pending
---

---
created: YYYY-MM-DD
status: pending
---

## Objective
Process the draft from /Needs_Action/<draft_file>.md

## Steps
- [ ] Read draft content
- [ ] Verify facts and references
- [ ] Edit tone and clarity
- [ ] Move draft to /Completed

2. **Content Generation:** For each detected item, create a `.md` file in `/Needs_Action/` with draft content. 
- Watchers must prioritize latest and trending topics based on news feeds, hashtags, mentions, or LinkedIn trends.
- Only content from the last 7–14 days should be considered to ensure relevance.

  - Each article should include a **critique** of current policies/practices and a **hopeful angle** for improvement.
- Ensure all content is **factual, verified, and includes real case studies, statistics, and references**. 
3. **Content Verification:** Claude AI or human reviews facts, sources, case studies, and figures for accuracy.  
4. **Human Review:** Edit for tone, clarity, and accuracy.  
5. **Approval:** Move approved drafts to `/Completed/`.  
6. **Optional Dashboard:** Maintain a `Dashboard.md` summarizing pending drafts by platform and type.

**Example Dashboard.md:**
```markdown
## Pending Content Drafts
- LinkedIn: 3 drafts
- Instagram: 2 drafts
- News: 4 drafts
```


---

## 4. Watcher Scheduling
- **On-demand:** Run watchers manually when content is needed.  
- **Periodic:** Schedule with cron (Linux/macOS) or Task Scheduler (Windows) for automatic draft generation.  
- **Recommended:** 2–3 runs per day to keep content fresh.
**Content Draft Delivery / Email Frequency:**
- **LinkedIn & Instagram:** Drafts should be emailed to the human reviewer every **2 days**.  
- **News Drafts:** Drafts should be emailed to the human reviewer **daily**.  
- Emails should include:
  - The .md draft file or inline text.
  - Metadata (platform, topic, urgency).
  - Verification status (if already fact-checked by AI).

---

## 5. Deliverables – Bronze Tier
| Component         | Description                                   | Format |
|------------------|-----------------------------------------------|--------|
| LinkedIn Drafts   | Ideas/posts from LinkedIn trends             | .md    |
| Instagram Drafts  | Captions based on hashtags/mentions          | .md    |
| News Drafts       | Summaries of local and global issues, critiques | .md |
| Dashboard.md      | Overview of pending content                  | Markdown |

**Completion Criteria:**
- At least one working watcher per platform.  
- Drafts successfully saved in `/Needs_Action/`.  
- Folder structure correctly implemented.  
- Human review and verification possible without additional automation.

---

## 6. Optional Enhancements
- Include metadata tags: `#topic`, `#industry`, `#urgency`.  
- Add draft suggestions for visuals: `image_prompt: <description>`.  
- Implement lightweight summary AI to rewrite content variations.

---

## 7. Security & Privacy
- No credentials required at Bronze Tier for content drafts.  
- Keep local copies of drafts; no external posting.  
- All content creation occurs locally in the Obsidian vault.

---

✅ **Outcome:**  
A Bronze Tier Digital FTE that provides a steady stream of verified content drafts for LinkedIn, Instagram, and News. All drafts are human-reviewed and fact-checked before posting or further automation.

