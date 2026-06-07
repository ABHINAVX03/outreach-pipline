"""
Automated B2B Outreach Pipeline
Usage:
    python main.py stripe.com
    python main.py stripe.com --dry-run        # stops before sending
    python main.py stripe.com --skip-confirm   # skips Y/N prompt (CI/test use only)
"""

import csv
import logging
import sys
from pathlib import Path

import click

from config import validate_env
from stages.stage1_ocean    import get_lookalikes
from stages.stage2_prospeo  import get_decision_makers
from stages.stage4_brevo    import send_outreach
from utils.checkpoint       import confirm_before_send

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")


# ── Helpers ───────────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], filename: str) -> None:
    """Persist a list of dicts to data/<filename> for debugging."""
    if not rows:
        return
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Saved %d row(s) → %s", len(rows), path)


def divider(label: str) -> None:
    logger.info("─" * 54)
    logger.info("  %s", label)
    logger.info("─" * 54)


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.command()
@click.argument("seed_domain")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Run discovery and enrichment but skip the email send entirely.",
)
@click.option(
    "--skip-confirm",
    is_flag=True,
    default=False,
    help="Bypass the Y/N safety prompt. Use in automated tests only.",
)
def run(seed_domain: str, dry_run: bool, skip_confirm: bool) -> None:
    """
    Full outreach pipeline.

    SEED_DOMAIN is the company domain you use as the lookalike seed.

    Example: python main.py stripe.com
    """
    # ── Pre-flight checks ──────────────────────────────────────────────────
    validate_env()
    seed_domain = seed_domain.strip().lower()
    logger.info("Pipeline starting for seed: %s", seed_domain)

    # ── Stage 1 — Lookalike companies ──────────────────────────────────────
    divider("Stage 1 / Ocean.io — finding lookalike companies")
    domains = get_lookalikes(seed_domain)
    save_csv([{"domain": d} for d in domains], "stage1_domains.csv")

    if not domains:
        logger.error("No lookalike domains found. Exiting.")
        sys.exit(1)

    # ── Stage 2 — Decision-makers ──────────────────────────────────────────
    divider("Stage 2 / Prospeo — finding decision-makers")
    contacts = get_decision_makers(domains)
    save_csv(contacts, "stage2_contacts.csv")

    if not contacts:
        logger.error("No contacts found. Exiting.")
        sys.exit(1)

    # ── Stage 3 — Skipped (Prospeo returns emails directly) ─────────────────
    divider("Stage 3 — skipped (emails from Prospeo)")
    enriched = contacts

    # ── Stage 4 — Send outreach ────────────────────────────────────────────
    divider("Stage 4 / Brevo — sending personalized outreach")

    if dry_run:
        logger.info("--dry-run flag set. Email send skipped.")
        logger.info("Pipeline complete (dry run). %d contacts ready.", len(enriched))
        return

    if not skip_confirm:
        if not confirm_before_send(enriched):
            logger.info("Aborted at safety checkpoint. No emails sent.")
            sys.exit(0)

    sent = send_outreach(enriched)

    divider(f"Pipeline complete — {sent}/{len(enriched)} email(s) sent")


if __name__ == "__main__":
    run()
