"""
Stage 3 — Eazyreach
LinkedIn profile URLs → verified work email addresses.

API docs: https://eazyreach.app  (log in → API section)
VERIFY:
  - Exact endpoint path
  - Auth header name and format
  - Request body field name for the LinkedIn URL
  - Response field name that contains the resolved email
"""

import logging
import time
import httpx
from config import EAZYREACH_API_KEY
from utils.retry import api_retry

logger = logging.getLogger(__name__)

# VERIFY: check eazyreach.app docs for the correct base URL.
BASE_URL = "https://api.eazyreach.app"


@api_retry()
def _resolve_one(linkedin_url: str) -> str | None:
    """
    Call Eazyreach to resolve a single LinkedIn URL → work email.
    Returns None if the email could not be found (404 / empty response).
    """
    headers = {
        # VERIFY: Eazyreach auth — may be 'Authorization: Bearer ...' or 'X-API-Key: ...'
        "Authorization": f"Bearer {EAZYREACH_API_KEY}",
        "Content-Type": "application/json",
    }

    # VERIFY: confirm field name ('linkedin_url' vs 'profile_url' etc.) from docs.
    payload = {"linkedin_url": linkedin_url}

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/v1/find-email",   # ← confirm in docs
            headers=headers,
            json=payload,
        )

        if resp.status_code == 404:
            return None   # profile found, email not resolved — not an error

        resp.raise_for_status()
        data = resp.json()

    # VERIFY: adjust field names to match real response.
    return (
        data.get("email")
        or data.get("work_email")
        or data.get("data", {}).get("email")
    )


def resolve_emails(contacts: list[dict]) -> list[dict]:
    """
    Public entry-point for Stage 3.
    Enriches each contact dict with a 'email' key.
    Contacts without a resolved email are dropped (not crash-worthy).
    """
    if not EAZYREACH_API_KEY:
        raise EnvironmentError("EAZYREACH_API_KEY is not set in .env")

    enriched: list[dict] = []

    for i, contact in enumerate(contacts, 1):
        linkedin_url = contact.get("linkedin_url", "").strip()

        if not linkedin_url:
            logger.warning(
                "[Stage 3] No LinkedIn URL for '%s' — skipping", contact.get("name")
            )
            continue

        logger.info(
            "[Stage 3] (%d/%d) Resolving email for: %s (%s)",
            i, len(contacts), contact.get("name"), linkedin_url,
        )

        try:
            email = _resolve_one(linkedin_url)

            if email:
                contact["email"] = email
                enriched.append(contact)
                logger.info("[Stage 3] ✓ Resolved: %s", email)
            else:
                logger.warning(
                    "[Stage 3] No email found for '%s'", contact.get("name")
                )

        except Exception as exc:
            logger.warning("[Stage 3] Skipping '%s' — %s", contact.get("name"), exc)

        time.sleep(1.5)   # credits are limited; be conservative

    logger.info(
        "[Stage 3] Resolved %d/%d email(s)", len(enriched), len(contacts)
    )
    return enriched
