---
name: job-apply-agent
description: AI agent that applies to jobs automatically. Finds postings (Greenhouse, Lever, Ashby, LinkedIn), builds a one-page CV tailored to each posting from the user's facts only, then fills and submits the application on the company site (account creation, email verification codes, questions) or via LinkedIn Easy Apply. Use when the user wants to auto-apply to jobs or internships, set up or run the bot, tailor CVs per posting, or check what was applied.
---

# Job Apply Agent

The code is in this folder. Read `README.md` first.

## Setting it up for a user

1. Ask for their Claude API key to be put in `.env` by the user themself (copy `.env.example`); never paste it in chat.
2. Build `facts.yaml` from their real CV (copy `facts.example.yaml`): several phrasings per bullet, grouped. Only true facts.
3. Build `profile.yaml` (copy `profile.example.yaml`): fixed answers, `facts_for_questions`, work authorization per country.
4. Edit `searches.yaml`: keywords, locations, `must_title` (whole words, e.g. `\bintern\b` so "Internal" doesn't match), caps.
5. `./set-mail.sh` for the inbox app password (hidden prompt).
6. Always do `./run.sh --dry-run` first and show the user the result before a real run.

## Running and checking

- `./run.sh` (company sites), `./run-easy.sh` (LinkedIn Easy Apply, after `./login-screen.sh`).
- `.venv/bin/python report.py`: applied, failed (with causes), skipped.
- Logs: `data/bot.log`. Tailored CVs: `data/cvs/`. Agent screenshots: `data/shots/`.

## Rules

- Never solve captchas, never enter payment/SIN/SSN/passport data, never invent facts.
- Never copy LinkedIn cookies into the server browser: the user logs in themself.
- Watch the API spend: each application costs many calls. Keep a spend limit on the key and use a key that no other product depends on.
