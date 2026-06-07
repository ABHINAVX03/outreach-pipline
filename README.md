# 🚀 Automated B2B Outreach Pipeline

A fully automated cold‑outreach engine that turns a single company domain into personalised emails sent to decision‑makers at lookalike companies — and then deploys itself on AWS to run daily, hands‑free.

---

## 🧠 What it does

1. **You give it a seed domain** (e.g. `apollo.io`).
2. **Ocean.io** returns 20 similar companies.
3. **Prospeo** finds C‑suite/VP contacts at those companies and enriches their verified work emails.
4. **Brevo** sends each of them a personalised cold email.

All with **one command** — and a `--dry-run` flag to test safely.

---

## 📦 Tech Stack

| Component         | Purpose                          |
|-------------------|----------------------------------|
| Python            | Glue & flow control              |
| httpx             | Async‑capable HTTP client        |
| Click             | CLI interface                    |
| Ocean.io API      | Lookalike company discovery      |
| Prospeo API       | People search & email enrichment |
| Brevo API         | Transactional email delivery     |
| AWS EC2 (t3.micro)| Cloud deployment                 |
| cron              | Daily scheduling                 |

---

## 🎯 Features

- ✅ **Modular pipeline** – each stage is a separate Python file.
- ✅ **Rate‑limit handling** – exponential backoff & retries.
- ✅ **Safety checkpoint** – Y/N prompt before sending real emails.
- ✅ `--dry-run` flag to test the full flow without firing.
- ✅ **Persistence** – never emails the same person twice.
- ✅ **Automated deployment** on AWS EC2 with cron.

---

## 🧱 Architecture (simplified)
