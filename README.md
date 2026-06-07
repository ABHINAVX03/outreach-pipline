# Cold Outreach Pipeline

## Setup
1. Install dependencies: `pip install httpx python-dotenv tenacity click`
2. Rename `.env` and fill in your real API keys and sender identity.
3. Run: `python main.py your-seed-domain.com`
4. Use `--dry-run` to preview without sending real emails.

## Project Structure
- `main.py` – CLI entry point
- `stages/` – one module per stage (Ocean.io, Prospeo, Brevo)
- `utils/` – retry logic and safety checkpoint
- `templates/email.txt` – personalized email template
- `data/` – intermediate CSV outputs
