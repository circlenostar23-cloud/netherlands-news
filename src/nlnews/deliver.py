"""Optional email delivery via Gmail SMTP. Skipped unless GMAIL_* / EMAIL_TO are all set.

The default backup channel is GitHub's own release notifications (see README), which
needs no mailbox credentials.
"""

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from nlnews.config import SHOW_TITLE, require_env
from nlnews.models import Briefing

GMAIL_ATTACHMENT_LIMIT = 24 * 1024 * 1024
REQUIRED = ("GMAIL_USER", "GMAIL_APP_PASSWORD", "EMAIL_TO")


def configured() -> bool:
    return all(os.environ.get(n) for n in REQUIRED)


def send_email(briefing: Briefing, briefing_md: Path, mp3: Path | None, feed_url: str | None) -> None:
    env = require_env(*REQUIRED)
    msg = EmailMessage()
    msg["Subject"] = f"{SHOW_TITLE} — {briefing.date}"
    msg["From"] = env["GMAIL_USER"]
    msg["To"] = env["EMAIL_TO"]

    body = [briefing.top_line, ""] + [f"• {s.headline}" for s in briefing.stories]
    body += ["", "Attached: today's episode (MP3) and the briefing document (upload it to NotebookLM for an Audio Overview)."]
    if feed_url:
        body += ["", f"Podcast feed: {feed_url}"]
    msg.set_content("\n".join(body))

    msg.add_attachment(briefing_md.read_bytes(), maintype="text", subtype="markdown",
                       filename=f"briefing-{briefing.date}.md")
    if mp3 and mp3.stat().st_size < GMAIL_ATTACHMENT_LIMIT:
        msg.add_attachment(mp3.read_bytes(), maintype="audio", subtype="mpeg",
                           filename=f"dutch-daily-{briefing.date}.mp3")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(env["GMAIL_USER"], env["GMAIL_APP_PASSWORD"])
        smtp.send_message(msg)
