"""
Email Drafts - Sends pending content drafts to human reviewer via email.
- LinkedIn & Instagram drafts: emailed every 2 days
- News drafts: emailed daily

Schedule separately in Windows Task Scheduler:
  - Daily: python email_drafts.py --platform news
  - Every 2 days: python email_drafts.py --platform linkedin instagram

Requires SMTP config in .env file.
"""

import os
import sys
import json
import smtplib
import argparse
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "email_drafts.log")),
    ],
)
logger = logging.getLogger("EmailDrafts")

# SMTP config from .env
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
REVIEWER_EMAIL = os.getenv("REVIEWER_EMAIL", "")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# File prefix mapping
PLATFORM_PREFIXES = {
    "linkedin": "LINKEDIN_",
    "instagram": "INSTA_",
    "news": "NEWS_",
}


def get_pending_drafts(vault_path: str, platforms: list[str]) -> list[dict]:
    """Collect drafts from /Needs_Action/ and /Completed/ for specified platforms.
    Skips files already marked as emailed."""
    folders = [
        Path(vault_path) / "Needs_Action",
        Path(vault_path) / "Completed",
    ]
    drafts = []

    for folder in folders:
        if not folder.exists():
            continue
        for f in sorted(folder.iterdir()):
            if f.suffix != ".md":
                continue
            name_upper = f.name.upper()
            for platform in platforms:
                prefix = PLATFORM_PREFIXES.get(platform, "")
                if name_upper.startswith(prefix):
                    content = f.read_text(encoding="utf-8")

                    # Extract metadata from frontmatter
                    metadata = {}
                    if content.startswith("---"):
                        end = content.find("---", 3)
                        if end != -1:
                            for line in content[3:end].strip().split("\n"):
                                if ":" in line:
                                    key, val = line.split(":", 1)
                                    metadata[key.strip()] = val.strip().strip('"')

                    # Skip files already emailed
                    if metadata.get("status") == "emailed":
                        logger.info(f"Skipping already-emailed draft: {f.name}")
                        continue

                    drafts.append({
                        "platform": platform.title(),
                        "filename": f.name,
                        "path": str(f),
                        "content": content,
                        "metadata": metadata,
                        "cycle_type": metadata.get("cycle_type", "unknown"),
                        "status": metadata.get("status", "pending"),
                    })
    return drafts


def mark_drafts_as_emailed(drafts: list[dict]):
    """Update status to 'emailed' in frontmatter of each draft file."""
    import re
    for draft in drafts:
        path = Path(draft["path"])
        content = path.read_text(encoding="utf-8")
        # Replace status field in frontmatter
        updated = re.sub(
            r"^(status:\s*).*$",
            r"\1emailed",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        path.write_text(updated, encoding="utf-8")
        logger.info(f"Marked as emailed: {draft['filename']}")


def _cycle_badge_color(cycle_type: str) -> str:
    """Return a badge color based on cycle type."""
    colors = {
        "local_problem": "#c0392b",
        "local_hopeful": "#27ae60",
        "global_problem": "#e67e22",
        "global_hopeful": "#2980b9",
    }
    return colors.get(cycle_type, "#7f8c8d")


def _urgency_color(urgency: str) -> str:
    return "#c0392b" if urgency.lower() == "high" else "#27ae60"


def _extract_draft_content(text: str) -> str:
    """Extract only the Draft Content section, stripping any inline References block."""
    import re
    match = re.search(r"^## Draft (?:Content|Caption)\s*\n", text, re.MULTILINE)
    if not match:
        return text
    content_start = match.end()
    next_section = re.search(r"^## ", text[content_start:], re.MULTILINE)
    if next_section:
        content = text[content_start:content_start + next_section.start()].strip()
    else:
        content = text[content_start:].strip()
    # Strip inline References block so it only appears in the references panel
    content = re.sub(r"\n?\*\*References:\*\*\s*\n(?:\[\d+\].+\n?)*", "", content).strip()
    return content


def _extract_references(text: str) -> str:
    """Extract References section from draft content (inline References: block or ## Sources & References)."""
    import re
    # Try inline References: block inside draft content first
    match = re.search(r"\*\*References:\*\*\s*\n((?:\[\d+\].+\n?)+)", text)
    if match:
        return match.group(0).strip()
    # Fallback: ## Sources & References section
    match = re.search(r"^## Sources & References\s*\n", text, re.MULTILINE)
    if not match:
        return ""
    ref_start = match.end()
    next_section = re.search(r"^## ", text[ref_start:], re.MULTILINE)
    if next_section:
        content = text[ref_start:ref_start + next_section.start()].strip()
    else:
        content = text[ref_start:].strip()
    if not content or content.startswith("_[List"):
        return ""
    return content


def _md_to_simple_html(text: str) -> str:
    """Convert basic markdown formatting to HTML for email body."""
    import re
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Headers
    text = re.sub(r"^### (.+)$", r"<h4 style='color:#2c3e50;margin:16px 0 6px 0;'>\1</h4>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h3 style='color:#2c3e50;margin:20px 0 8px 0;'>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h2 style='color:#2c3e50;margin:24px 0 10px 0;'>\1</h2>", text, flags=re.MULTILINE)
    # Horizontal rule
    text = re.sub(r"^---$", r"<hr style='border:none;border-top:1px solid #ecf0f1;margin:16px 0;'>", text, flags=re.MULTILINE)
    # List items
    text = re.sub(r"^- (.+)$", r"<li style='margin:4px 0;'>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"(<li.*</li>\n?)+", r"<ul style='padding-left:20px;margin:8px 0;'>\g<0></ul>", text)
    # Numbered list items
    text = re.sub(r"^\d+\. (.+)$", r"<li style='margin:4px 0;'>\1</li>", text, flags=re.MULTILINE)
    # Paragraphs: wrap double-newline-separated blocks
    paragraphs = text.split("\n\n")
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<h") or p.startswith("<hr") or p.startswith("<ul"):
            result.append(p)
        else:
            p = p.replace("\n", "<br>")
            result.append(f"<p style='margin:10px 0;line-height:1.7;color:#34495e;'>{p}</p>")
    return "\n".join(result)


def get_verified_count(vault_path: str, platforms: list[str]) -> int:
    """Count verified drafts in /Completed/ for the given platforms."""
    completed = Path(vault_path) / "Completed"
    if not completed.exists():
        return 0
    count = 0
    for f in completed.iterdir():
        if f.suffix != ".md":
            continue
        name_upper = f.name.upper()
        for platform in platforms:
            prefix = PLATFORM_PREFIXES.get(platform, "")
            if name_upper.startswith(prefix):
                count += 1
    return count


def _time_of_day(now: datetime) -> str:
    hour = now.hour
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _generate_wavy_intro(topic: str, platform_label: str, now: datetime) -> tuple[str, str]:
    """Call OpenAI to generate a warm Wavy greeting and a topic-relevant joke.
    Returns (greeting_html, joke_html). Falls back to static text if API unavailable."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    tod = _time_of_day(now)

    if not api_key:
        greeting = (
            f"Good {tod}! I'm Wavy, your AI Employee. "
            f"I've prepared your {platform_label} content draft on <strong>{topic}</strong> — fresh, verified, and ready for your review. Let's make an impact today! 🌿"
        )
        joke = "Why did the solar panel break up with the coal plant? Because it found someone who treated it with more warmth — naturally! ☀️"
        return greeting, joke

    client = OpenAI(api_key=api_key)
    prompt = f"""You are Wavy, a warm and witty AI Employee specialising in sustainability and climate content for Pakistan.

Write two things:

1. GREETING: A friendly, energetic Good {tod} message (2-3 sentences). Address TWS members directly. Mention you've prepared their {platform_label} content draft about "{topic}". Be enthusiastic but professional. No emojis overload — max 2.

2. JOKE: One short, clever, original joke (2-4 sentences) that is genuinely funny AND relevant to the topic "{topic}" or sustainability/environment in general. It can be a pun, a light observation, or a setup-punchline. Keep it clean and witty.

Reply in exactly this format (no extra text):
GREETING: <your greeting here>
JOKE: <your joke here>"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.85,
        )
        text = response.choices[0].message.content.strip()
        greeting, joke = "", ""
        for line in text.splitlines():
            if line.startswith("GREETING:"):
                greeting = line[len("GREETING:"):].strip()
            elif line.startswith("JOKE:"):
                joke = line[len("JOKE:"):].strip()
        if not greeting:
            greeting = f"Good {tod}! I'm Wavy — your draft on <strong>{topic}</strong> is ready. 🌿"
        if not joke:
            joke = "Why don't climate scientists ever argue? Because they always find common ground! 🌍"
        return greeting, joke
    except Exception as e:
        logger.warning(f"Wavy intro generation failed: {e}")
        return (
            f"Good {tod}! I'm Wavy, your AI Employee. Your {platform_label} draft on <strong>{topic}</strong> is ready for review. 🌿",
            "Why don't climate scientists ever argue? Because they always find common ground! 🌍",
        )


def build_email(drafts: list[dict], platforms: list[str], verified_count: int = 0) -> MIMEMultipart:
    """Build a well-formatted HTML email with all pending drafts."""
    msg = MIMEMultipart("alternative")
    platform_label = " & ".join(p.title() for p in platforms)
    now = datetime.now()
    msg["Subject"] = f"[AI Employee Wavy] {platform_label} Content Draft{'s' if len(drafts) > 1 else ''} Ready for Review — {now.strftime('%d %b %Y')}"
    msg["From"] = SMTP_USER
    msg["To"] = REVIEWER_EMAIL
    msg["Date"] = now.strftime("%a, %d %b %Y %H:%M:%S +0500")
    msg["MIME-Version"] = "1.0"

    # ── Styles ──────────────────────────────────────────────────────────────
    font = "font-family:'Segoe UI',Arial,sans-serif;"

    # ── Generate Wavy greeting + joke ───────────────────────────────────────
    first_topic = drafts[0]["metadata"].get("source_title", drafts[0]["cycle_type"].replace("_", " ").title()) if drafts else "sustainability"
    wavy_greeting, wavy_joke = _generate_wavy_intro(first_topic, platform_label, now)

    # ── Build draft cards ──────────────────────────────────────────────────
    draft_cards = ""
    for i, draft in enumerate(drafts, 1):
        meta = draft["metadata"]
        cycle = draft["cycle_type"].replace("_", " ").title()
        urgency = meta.get("urgency", "normal").capitalize()
        topic = meta.get("topic", meta.get("source_title", "N/A"))
        source_title = meta.get("source_title", "N/A")
        source_link = meta.get("source_link", "#")
        badge_color = _cycle_badge_color(draft["cycle_type"])
        urg_color = _urgency_color(urgency)
        # Strip frontmatter, then extract only the Draft Content section
        content_body = draft["content"]
        if content_body.startswith("---"):
            end = content_body.find("---", 3)
            if end != -1:
                content_body = content_body[end + 3:].strip()

        references_raw = _extract_references(content_body)
        content_body = _extract_draft_content(content_body)
        content_html = _md_to_simple_html(content_body)
        references_html = _md_to_simple_html(references_raw) if references_raw else ""

        references_block = f"""
          <!-- References -->
          <div style="padding:14px 24px 20px 24px;background:#f8fafc;border-top:1px solid #e8edf2;">
            <p style="font-size:12px;color:#95a5a6;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:0.6px;font-weight:600;">References</p>
            <div style="font-size:12px;color:#5d6d7e;line-height:1.8;">{references_html}</div>
          </div>""" if references_html else ""

        draft_cards += f"""
        <div style="background:#ffffff;border:1px solid #e8edf2;border-radius:8px;margin-bottom:30px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
          <!-- Card header -->
          <div style="background:#2c3e50;padding:16px 20px;display:flex;align-items:center;">
            <span style="background:{badge_color};color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;letter-spacing:0.5px;text-transform:uppercase;">{cycle}</span>
            <span style="color:#ecf0f1;font-size:16px;font-weight:600;margin-left:12px;{font}">{draft['platform']} Draft #{i}</span>
          </div>
          <!-- Draft content -->
          <div style="padding:20px 24px;{font}font-size:14px;color:#34495e;line-height:1.7;">
            <p style="font-size:12px;color:#95a5a6;margin:0 0 14px 0;text-transform:uppercase;letter-spacing:0.6px;font-weight:600;">Draft Content</p>
            {content_html}
          </div>{references_block}
        </div>
        """

    # ── Full HTML email ────────────────────────────────────────────────────
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>AI Employee Wavy — Content Draft Ready</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;{font}">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:30px 0;">
    <tr>
      <td align="center">
        <table width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#0b2a2b 0%,#1a4a4a 100%);padding:28px 32px;border-radius:10px 10px 0 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0;color:#358682;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;">AI Employee Wavy</p>
                    <h1 style="margin:6px 0 0 0;color:#ffffff;font-size:22px;font-weight:700;{font}">Content Draft{'s' if len(drafts) > 1 else ''} Ready for Review</h1>
                  </td>
                  <td align="right" valign="top">
                    <p style="margin:0;color:#7f8c8d;font-size:12px;">{now.strftime('%d %B %Y')}</p>
                    <p style="margin:4px 0 0 0;color:#7f8c8d;font-size:12px;">{now.strftime('%H:%M PKT')}</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Wavy greeting banner -->
          <tr>
            <td style="background:#358682;padding:18px 32px;">
              <p style="margin:0 0 6px 0;color:#d4f0ee;font-size:11px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;{font}">👋 Wavy says</p>
              <p style="margin:0;color:#ffffff;font-size:15px;line-height:1.6;{font}">{wavy_greeting}</p>
            </td>
          </tr>

          <!-- Joke card -->
          <tr>
            <td style="background:#f7fffe;padding:16px 32px;border-left:4px solid #358682;border-bottom:1px solid #e8edf2;">
              <p style="margin:0 0 6px 0;color:#358682;font-size:11px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;{font}">😄 Today's Green Joke</p>
              <p style="margin:0;color:#2c3e50;font-size:14px;line-height:1.6;font-style:italic;{font}">{wavy_joke}</p>
            </td>
          </tr>

          <!-- Summary bar -->
          <tr>
            <td style="background:#ffffff;padding:18px 32px;border-bottom:2px solid #e8edf2;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0 10px;">
                    <p style="margin:0;font-size:26px;font-weight:700;color:#2c3e50;{font}">{len(drafts)}</p>
                    <p style="margin:4px 0 0 0;font-size:11px;color:#7f8c8d;text-transform:uppercase;letter-spacing:0.5px;">Total Drafts</p>
                  </td>
                  <td align="center" style="padding:0 10px;border-left:1px solid #ecf0f1;">
                    <p style="margin:0;font-size:26px;font-weight:700;color:#27ae60;{font}">{verified_count}</p>
                    <p style="margin:4px 0 0 0;font-size:11px;color:#7f8c8d;text-transform:uppercase;letter-spacing:0.5px;">Verified</p>
                  </td>
                  <td align="center" style="padding:0 10px;border-left:1px solid #ecf0f1;">
                    <p style="margin:0;font-size:14px;font-weight:700;color:#2c3e50;{font}">{platform_label}</p>
                    <p style="margin:4px 0 0 0;font-size:11px;color:#7f8c8d;text-transform:uppercase;letter-spacing:0.5px;">Platforms</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Draft cards -->
          <tr>
            <td style="background:#f0f4f8;padding:24px 32px;">
              {draft_cards}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#0b2a2b;padding:20px 32px;border-radius:0 0 10px 10px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0;color:#a8c5c4;font-size:12px;{font}">
                      <strong style="color:#ffffff;">AI Employee Wavy</strong> &nbsp;|&nbsp; Draft-Only Mode &nbsp;|&nbsp; No External Posting
                    </p>
                    <p style="margin:5px 0 0 0;color:#5a8a88;font-size:11px;{font}">
                      All drafts are AI-generated and require human review before publication. &nbsp;Generated: {now.strftime('%Y-%m-%d %H:%M')}
                    </p>
                  </td>
                  <td align="right" valign="middle">
                    <p style="margin:0;color:#dab200;font-size:12px;font-style:italic;font-weight:600;{font}">We are the seeds that will weave a sustainable tomorrow.</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""

    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_email(msg: MIMEMultipart):
    """Send email via SMTP."""
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would send email to {REVIEWER_EMAIL}")
        logger.info(f"  Subject: {msg['Subject']}")
        logger.info(f"  From: {SMTP_USER}")
        return True

    if not SMTP_USER or not SMTP_PASSWORD or not REVIEWER_EMAIL:
        logger.error("SMTP credentials or REVIEWER_EMAIL not configured in .env")
        return False

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {REVIEWER_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def log_email_action(vault_path: str, platforms: list[str], draft_count: int, success: bool):
    """Log email action to vault logs."""
    logs_dir = Path(vault_path) / "Logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": "email_drafts",
        "actor": "email_drafts_script",
        "target": REVIEWER_EMAIL,
        "parameters": {
            "platforms": platforms,
            "draft_count": draft_count,
            "dry_run": DRY_RUN,
        },
        "result": "success" if success else "failure",
    }

    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Email pending content drafts to reviewer")
    parser.add_argument(
        "--platform",
        nargs="+",
        choices=["linkedin", "instagram", "news"],
        required=True,
        help="Platforms to include in the email",
    )
    args = parser.parse_args()

    vault_path = os.getenv("VAULT_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    logger.info(f"Collecting drafts for: {', '.join(args.platform)}")

    drafts = get_pending_drafts(vault_path, args.platform)

    if not drafts:
        logger.info("No pending drafts found. No email sent.")
        return

    logger.info(f"Found {len(drafts)} pending draft(s)")
    verified_count = sum(1 for d in drafts if d["status"] == "verified")
    msg = build_email(drafts, args.platform, verified_count)
    success = send_email(msg)
    if success and not DRY_RUN:
        mark_drafts_as_emailed(drafts)
    log_email_action(vault_path, args.platform, len(drafts), success)


if __name__ == "__main__":
    main()
