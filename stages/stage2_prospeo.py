"""
Stage 2 — Prospeo (two-step)
Step A: POST /search-person  — find C-suite/VP contacts at each domain
Step B: POST /enrich-person  — get verified email per person_id

API docs: https://prospeo.io/api-docs
Auth: X-KEY header
"""

import logging
import time
import httpx
from config import PROSPEO_API_KEY, MAX_CONTACTS_PER_DOMAIN
from utils.retry import api_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.prospeo.io"

TARGET_SENIORITIES = ["C-Suite", "Vice President", "Director", "Founder/Owner", "Head"]
SKIP_CODES = {"NO_RESULTS", "INSUFFICIENT_CREDITS", "PLAN_REQUIRED", "NO_MATCH"}


@api_retry()
def _search_people(domain: str) -> list[dict]:
    """Step A — find senior people at a domain."""
    headers = {"X-KEY": PROSPEO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "page": 1,
        "filters": {
            "company": {"websites": {"include": [domain]}},
            "person_seniority": {"include": TARGET_SENIORITIES},
            "max_person_per_company": MAX_CONTACTS_PER_DOMAIN,
        },
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{BASE_URL}/search-person", headers=headers, json=payload)
        if resp.status_code == 400:
            code = resp.json().get("error_code", "")
            if code in SKIP_CODES:
                logger.info("[Stage 2] %s for %s — skipping", code, domain)
                return []
            logger.warning("[Stage 2] 400 for %s: %s", domain, resp.json())
            return []
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        logger.info("[Stage 2] %s → %d person(s) found", domain, len(results))
        return results


@api_retry()
def _enrich_person(person_id: str) -> str | None:
    """
    Step B — get verified email for a person_id.
    Docs: https://prospeo.io/api-docs/enrich-person

    Key fixes (from docs):
    - person_id must be inside a "data" wrapper: {"data": {"person_id": "..."}}
    - response email is nested object: person.email.email (not a plain string)
    """
    headers = {"X-KEY": PROSPEO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "data": {"person_id": person_id},   # ✅ wrapped in "data"
        "only_verified_email": True,         # only spend credits for verified emails
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{BASE_URL}/enrich-person", headers=headers, json=payload)
        if resp.status_code == 400:
            code = resp.json().get("error_code", "")
            if code in SKIP_CODES:
                return None
            logger.warning("[Stage 2] Enrich 400 for %s: %s", person_id, resp.json())
            return None
        resp.raise_for_status()
        data      = resp.json()
        person    = data.get("person", {})
        email_obj = person.get("email") or {}
        # email is nested: {"status": "VERIFIED", "revealed": true, "email": "..."}
        if isinstance(email_obj, dict):
            return email_obj.get("email")
        return email_obj if isinstance(email_obj, str) else None


def get_decision_makers(domains: list[str]) -> list[dict]:
    """Public entry-point for Stage 2."""
    if not PROSPEO_API_KEY:
        raise EnvironmentError("PROSPEO_API_KEY is not set in .env")

    all_contacts: list[dict] = []

    for i, domain in enumerate(domains[:3], 1):
        logger.info("[Stage 2] (%d/%d) Searching: %s", i, len(domains), domain)
        try:
            results = _search_people(domain)
            for result in results:
                person       = result.get("person", {})
                company      = result.get("company", {})
                person_id    = person.get("id") or person.get("person_id") or ""
                first        = person.get("first_name", "")
                last         = person.get("last_name", "")
                name         = f"{first} {last}".strip()
                title        = person.get("job_title") or person.get("position") or ""
                linkedin     = person.get("linkedin_url") or person.get("linkedin") or ""
                company_name = company.get("name") or company.get("company_name") or domain

                if not person_id:
                    logger.warning("[Stage 2] No person_id for %s — skipping", name)
                    continue

                email = _enrich_person(person_id)
                if email:
                    all_contacts.append({
                        "domain":       domain,
                        "company":      company_name,
                        "name":         name,
                        "title":        title,
                        "email":        email,
                        "linkedin_url": linkedin,
                    })
                    logger.info("[Stage 2] ✓ %s <%s>", name, email)
                else:
                    logger.warning("[Stage 2] No verified email for %s", name)

                time.sleep(8.0)   # ✅ increased — Prospeo free tier rate limit

        except Exception as exc:
            logger.warning("[Stage 2] Skipping %s — %s", domain, exc)

        time.sleep(5.0)   # between domain searches

    logger.info("[Stage 2] Total contacts with emails: %d", len(all_contacts))
    return all_contacts
