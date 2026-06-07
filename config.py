import os
from dotenv import load_dotenv

load_dotenv()

# ── Required API keys ─────────────────────────────────────────────────────────
OCEAN_API_KEY     = os.getenv("OCEAN_API_KEY", "")
PROSPEO_API_KEY   = os.getenv("PROSPEO_API_KEY", "")
EAZYREACH_API_KEY = os.getenv("EAZYREACH_API_KEY", "")
BREVO_API_KEY     = os.getenv("BREVO_API_KEY", "")

# ── Sender identity ───────────────────────────────────────────────────────────
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME  = os.getenv("SENDER_NAME", "")

# ── Pipeline tuning ───────────────────────────────────────────────────────────
MAX_LOOKALIKES          = int(os.getenv("MAX_LOOKALIKES", 20))
MAX_CONTACTS_PER_DOMAIN = int(os.getenv("MAX_CONTACTS_PER_DOMAIN", 3))

# ── Guard: fail loud and early if keys are missing ───────────────────────────
REQUIRED = {
    "OCEAN_API_KEY":     OCEAN_API_KEY,
    "PROSPEO_API_KEY":   PROSPEO_API_KEY,
    "BREVO_API_KEY":     BREVO_API_KEY,
    "SENDER_EMAIL":      SENDER_EMAIL,
    "SENDER_NAME":       SENDER_NAME,
}

def validate_env() -> None:
    """Call once at startup. Raises if any required key is missing."""
    missing = [k for k, v in REQUIRED.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}\n"
            f"Copy .env.example → .env and fill in your keys."
        )
