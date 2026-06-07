"""
Stage 4 — Brevo
Enriched contacts → personalized cold-outreach emails sent.

API docs: https://developers.brevo.com/reference/sendtransacemail
This stage is the most stable of the four — Brevo's v3 API is well-documented.
"""

import logging
import os
import time
from pathlib import Path
import httpx
from config import BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME
from utils.retry import api_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.brevo.com/v3"
TEMPLATE_PATH = Path("templates/email.txt")
SENT_EMAILS_PATH = Path("data/sent_emails.txt")
SEND_LOCK_PATH = Path("data/send_outreach.lock")
SEND_LOCK_MAX_AGE_SECONDS = 6 * 60 * 60


def _load_template() -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Email template not found at {TEMPLATE_PATH}. "
            "Create it before running Stage 4."
        )
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _personalize(template: str, contact: dict) -> tuple[str, str]:
    """
    Fill in placeholders in the template and generate a subject line.
    Placeholders supported: {first_name}, {company}, {title}, {domain}
    """
    first_name = (contact.get("name") or "there").split()[0]
    company    = contact.get("company") or contact.get("domain") or "your company"
    title      = contact.get("title", "")
    domain     = contact.get("domain", "")

    body = template.format(
        first_name=first_name,
        company=company,
        title=title,
        domain=domain,
    )
    subject = f"Quick question for {company}"
    return subject, body


def _load_sent_emails() -> set[str]:
    if not SENT_EMAILS_PATH.exists():
        return set()
    return {
        line.strip().lower()
        for line in SENT_EMAILS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _mark_sent(email: str) -> None:
    SENT_EMAILS_PATH.parent.mkdir(exist_ok=True)
    with SENT_EMAILS_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{email.lower()}\n")


def _acquire_send_lock() -> None:
    SEND_LOCK_PATH.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(SEND_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        age = time.time() - SEND_LOCK_PATH.stat().st_mtime
        if age < SEND_LOCK_MAX_AGE_SECONDS:
            raise RuntimeError("Another outreach send run appears to be active.")
        SEND_LOCK_PATH.unlink()
        fd = os.open(SEND_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(str(time.time()))


def _release_send_lock() -> None:
    try:
        SEND_LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


@api_retry()
def _send_one(contact: dict, subject: str, body: str) -> None:
    """Single transactional email via Brevo SMTP API."""
    headers = {
        "api-key": BREVO_API_KEY,   # Brevo uses 'api-key' (no 'Bearer' prefix)
        "Content-Type": "application/json",
    }

    payload = {
        "sender": {
            "name":  SENDER_NAME,
            "email": SENDER_EMAIL,
        },
        "to": [
            {
                "email": contact["email"].strip().lower(),
                "name":  contact.get("name", ""),
            }
        ],
        "subject":     subject,
        "textContent": body,   # plain-text body; swap for "htmlContent" if using HTML
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{BASE_URL}/smtp/email", headers=headers, json=payload)
        resp.raise_for_status()


def send_outreach(contacts: list[dict]) -> int:
    """
    Public entry-point for Stage 4.
    Sends a personalized email to every new contact in the list.
    Returns the number of emails successfully sent.
    """
    if not BREVO_API_KEY:
        raise EnvironmentError("BREVO_API_KEY is not set in .env")
    if not SENDER_EMAIL or not SENDER_NAME:
        raise EnvironmentError("SENDER_EMAIL / SENDER_NAME not set in .env")

    _acquire_send_lock()
    try:
        template  = _load_template()
        sent_emails = _load_sent_emails()
        sent      = 0
        failed    = 0
        skipped   = 0

        for i, contact in enumerate(contacts, 1):
            email = contact.get("email", "").strip().lower()
            if not email:
                skipped += 1
                logger.warning("[Stage 4] Skipping contact without email: %s", contact)
                continue
            if email in sent_emails:
                skipped += 1
                logger.info("[Stage 4] Skipping already-sent contact: %s", email)
                continue

            contact["email"] = email
            subject, body = _personalize(template, contact)

            logger.info(
                "[Stage 4] (%d/%d) Sending to %s <%s>",
                i, len(contacts), contact.get("name"), email,
            )

            try:
                _send_one(contact, subject, body)
                _mark_sent(email)
                sent_emails.add(email)
                sent += 1
                logger.info("[Stage 4] ✓ Sent")
            except Exception as exc:
                failed += 1
                logger.error(
                    "[Stage 4] ✗ Failed for %s — %s", email, exc
                )

            time.sleep(0.5)   # Brevo free tier: 300/day; stay polite

        logger.info(
            "[Stage 4] Done — %d sent, %d failed, %d skipped", sent, failed, skipped
        )
        return sent
    finally:
        _release_send_lock()
