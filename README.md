# Automated B2B Outreach Pipeline

A fully automated cold-outreach engine that turns a single company domain into personalised emails sent to decision-makers at lookalike companies — and deploys itself on AWS to run hands-free, every day.

---

## How It Works

1. **Provide a seed domain** — e.g. `apollo.io`
2. **Ocean.io** discovers 20 similar companies
3. **Prospeo** finds C-suite / VP contacts and resolves their verified work emails
4. **Brevo** delivers a personalised cold email to each contact

All with one command. A `--dry-run` flag lets you test the full pipeline without sending anything.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python |
| HTTP client | httpx |
| CLI | Click |
| Company discovery | Ocean.io API |
| Contact & email enrichment | Prospeo API |
| Email delivery | Brevo API |
| Cloud hosting | AWS EC2 (t3.micro) |
| Scheduling | cron |

---

## Features

- **Modular pipeline** — each stage is an isolated Python module
- **Rate-limit handling** — exponential backoff with automatic retries
- **Safety checkpoint** — interactive Y/N prompt before any real sends
- **Dry-run mode** — test end-to-end without firing a single email
- **Deduplication** — `data/sent_emails.txt` ensures no contact is emailed twice
- **Automated deployment** — EC2 + cron for daily, unattended execution

---

## Architecture

```
Seed domain
    │
    ▼
[Stage 1] Ocean.io ──────► 20 lookalike domains
    │
    ▼
[Stage 2] Prospeo ───────► Contacts + verified emails
    │
    ▼
[Stage 4] Brevo ─────────► Personalised emails sent
```

> Stage 3 (separate email enrichment) was removed — Prospeo already provides verified emails.

---

## Project Structure

```
outreach_pipeline/
├── main.py                  # CLI entry point
├── config.py                # Loads & validates .env
├── requirements.txt
├── .env.example
├── run_daily.py             # Seed rotator for cron
├── seed_list.txt            # Daily rotation seed domains
├── stages/
│   ├── stage1_ocean.py      # Lookalike domain discovery
│   ├── stage2_prospeo.py    # Contact & email resolution
│   └── stage4_brevo.py      # Email sending with deduplication
├── utils/
│   ├── retry.py             # Exponential backoff
│   └── checkpoint.py        # Y/N safety prompt
├── templates/
│   └── email.txt            # Cold email template
└── data/                    # CSV outputs & sent_emails.txt
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/ABHINAVX03/outreach-pipline.git
cd outreach-pipline
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OCEAN_API_KEY=your_ocean_io_key
PROSPEO_API_KEY=your_prospeo_key
BREVO_API_KEY=your_brevo_key
SENDER_EMAIL=your_verified_sender@domain.com
SENDER_NAME=Your Name
MAX_LOOKALIKES=20
MAX_CONTACTS_PER_DOMAIN=3
MAX_DOMAINS=3
```

### 4. Customise the email template

Edit `templates/email.txt` and replace the placeholder copy with your actual pitch.

---

## Usage

```bash
# Test the full pipeline — no emails sent
python main.py apollo.io --dry-run

# Live run — prompts for confirmation before sending
python main.py apollo.io

# Skip confirmation prompt (for automation)
python main.py apollo.io --skip-confirm
```

---

## AWS Deployment (Daily Automation)

The pipeline runs on an AWS EC2 **t3.micro** instance (free tier) at **9:00 AM IST** daily via cron.

### Daily flow

1. `run_daily.py` reads the first domain from `seed_list.txt`
2. Calls the main pipeline with that domain
3. Removes the used domain so the next run picks the next one
4. `data/sent_emails.txt` is checked — already-contacted leads are skipped automatically

### Manual trigger on the server

```bash
ssh -i your-key.pem ubuntu@<ec2-public-ip>
cd outreach-pipline
source venv/bin/activate
python main.py hubspot.com
```

### Viewing logs

```bash
tail -f ~/pipeline.log
```

---

## Real-World Results

Tested against `apollo.io` as the seed domain:

| Metric | Result |
|---|---|
| Lookalike companies found | 20 |
| Verified emails resolved | 8 |
| Emails sent | 8 |
| Delivered | 7 |
| Hard bounces | 1 |
| Notable open | Or Biderman (VP Product, Lusha) — opened within seconds |

---

## Challenges & Solutions

| Challenge | Solution |
|---|---|
| Ocean.io returned nested company objects | Adjusted extraction to unwrap the `"company"` key |
| Prospeo required two sequential API calls | Implemented a two-step search → enrich flow with correct payload wrapping |
| Brevo rejected requests with 401 errors | Whitelisted the EC2 instance IP in Brevo's security settings |
| Prospeo free-tier rate limits (429s) | Capped daily domain count and increased sleep intervals between requests |
| Vocallabs removed Eazyreach mid-project | Dropped Stage 3 cleanly; Prospeo already provides verified emails |

---
