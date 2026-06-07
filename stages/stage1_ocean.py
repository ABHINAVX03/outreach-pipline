"""
Stage 1 — Ocean.io
Seed domain → list of lookalike company domains.

API: POST https://api.ocean.io/v3/search/companies
Auth: X-Api-Token header
Docs: https://app.ocean.io/docs/searchCompaniesV3
"""

import logging
import httpx
from config import OCEAN_API_KEY, MAX_LOOKALIKES
from utils.retry import api_retry

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ocean.io"


@api_retry()
def _call_ocean(seed_domain: str) -> dict:
    """Raw HTTP call to Ocean.io lookalike companies endpoint."""
    headers = {
        "X-Api-Token": OCEAN_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "companiesFilters": {
            "lookalikeDomains": [seed_domain],
        },
        "size": MAX_LOOKALIKES,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/v3/search/companies",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        companies = data.get("companies", [])
        logger.info("[Stage 1] total=%s credits_used=%s companies_returned=%s",
                    data.get("total"), data.get("creditsUsed"), len(companies))
        return data


def _extract_domains(data: dict) -> list[str]:
    """
    Parse Ocean.io response.
    Each result is: {"company": {"domain": "...", ...}, "relevance": "A"}
    The actual company data is nested under the "company" key.
    """
    results = data.get("companies", [])

    domains = []
    for result in results:
        # Unwrap nested "company" object
        company = result.get("company", result)
        domain = company.get("domain", "").strip().lower()
        if domain and "." in domain:
            domains.append(domain)

    return domains


def get_lookalikes(seed_domain: str) -> list[str]:
    """
    Public entry-point for Stage 1.
    Returns a deduplicated list of company domains similar to seed_domain.
    """
    if not OCEAN_API_KEY:
        raise EnvironmentError("OCEAN_API_KEY is not set in .env")

    seed_domain = seed_domain.strip().lower()
    logger.info("[Stage 1] Querying Ocean.io for lookalikes of: %s", seed_domain)

    data    = _call_ocean(seed_domain)
    domains = _extract_domains(data)

    # Remove the seed itself and preserve first-seen order.
    domains = list(dict.fromkeys(d for d in domains if d != seed_domain))

    logger.info("[Stage 1] Found %d lookalike domain(s)", len(domains))
    return domains
