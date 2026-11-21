---
name: job-apply-agent
description: AI agent that applies to jobs automatically. Finds postings (Greenhouse, Lever, Ashby, LinkedIn), builds an ATS-proof one-page CV tailored to each posting (the posting's keywords, plain single-column text that applicant tracking systems parse) from the user's facts only, then fills and submits the application on the company site (account creation, email verification codes, questions) or via LinkedIn Easy Apply. Use when the user wants to auto-apply to jobs or internships, set it up (guided onboarding), run it, or check what was applied.
---

# Job Apply Agent

The code is in this skill's folder (`cd` there for every command). `README.md` explains how it works.

## Always start here

Run `python3 check.py`. It lists the setup steps as OK / TODO.
- Any TODO (other than the optional LinkedIn step) → run the **onboarding**, resuming at the first TODO.
- `READY` → do what the user asked (run, report, change searches).

## Onboarding

Open with one short message, before anything else:

> "Let's set up your job apply agent. It's a guided onboarding: about 11 steps, one at a time, ~15 minutes. You'll need your CV, an email inbox, and a Claude API key. Ready?"

Then go **one step at a time**: say which step it is (e.g. "Step 4 of 10: Claude API key"), why it's needed in one line, how to do it, wait for the user, check it worked (`python3 check.py`), then move on. Never dump all the steps at once. Skip steps already OK.

**Secrets never go in the chat.** API keys and passwords are typed by the user in a hidden prompt (`set-key.sh`, `set-mail.sh`). If the user pastes a secret in chat anyway, don't save or repeat it: tell them to revoke it and use the script. Never ask for or use a LinkedIn `li_at` cookie or any copied cookie: LinkedIn kills copied sessions and logs the user out everywhere.

1. **Install** (you run it): `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install --with-deps chromium`.
2. **LaTeX** (builds the CV PDF): macOS `brew install tectonic`; Linux: download the tectonic binary from its GitHub releases into `~/bin` and set `TECTONIC=~/bin/tectonic` in `.env`.
3. **Claude API key**: tell them to open https://platform.claude.com/settings/keys, click *Create Key*, copy it, and **set a monthly spend limit** in Settings → Limits (each application costs tens of cents). Recommend a key used by nothing else. Then they run `./set-key.sh` in their terminal and paste it there (hidden). It tests the key before saving.
4. **Email inbox** (the email they apply with; it receives the verification codes): set `MAIL_USER` and `MAIL_IMAP_HOST` in `.env` (Gmail `imap.gmail.com`, Outlook `outlook.office365.com`, Yahoo `imap.mail.yahoo.com`, iCloud `imap.mail.me.com`).
5. **Email app password** (not their normal password). Help them find it:
   - Gmail: needs 2-Step Verification on, then https://myaccount.google.com/apppasswords → create one named "job agent".
   - Outlook/Hotmail: https://account.microsoft.com/security → Advanced security options → App passwords.
   - Yahoo: Account info → Account security → Generate app password.
   - iCloud: https://account.apple.com → Sign-In and Security → App-Specific Passwords.
   Then they run `./set-mail.sh` (hidden). It logs in and shows the latest code it can see.
6. **Facts (`facts.yaml`)**: ask for their CV (file path or pasted text). Draft `facts.yaml` from it following `facts.example.yaml`: every bullet true and taken from the CV, 2-3 phrasings of each bullet in the same group (e.g. one stressing Python, one TypeScript) so the tailor can match postings, a skills pool, education. Show it, fix what they say, save. Never add a skill or number that isn't in their CV or their own words.
7. **Profile (`profile.yaml`)**: ask the questions **in small groups** and fill `profile.example.yaml`'s structure:
   name, email, phone, address (street, city, postal code, province/state) · LinkedIn and GitHub URLs · school, degree, field, start date, expected graduation and a fallback date · GPA, or high-school diploma and grade if there's no university GPA yet · standardized tests (SAT/ACT/GRE) or "none" · languages and level · citizenship and work authorization per country (authorized? needs sponsorship?) · available start date, internship lengths, relocation, on-site/hybrid, full-time OK (would they pause studies?) · salary answer · interests (for "why this company" answers) · skills they do NOT have (answered "No"). Demographic questions default to "Prefer not to say".
8. **What to look for (`searches.yaml`)**: job keywords, locations (preferred first), `must_title` (whole words: `\bintern\b`, so "Internal" doesn't match), fields to exclude (`NOT_FIELD` in `ats.py`), and the caps. Start low (≤30/day) until the first runs look right. Then `mkdir -p data && touch data/.searches_reviewed`.
9. **LinkedIn Easy Apply (optional)**: ask if they want it. If yes, they run `./linkedin-login.sh`: a browser window opens (on a server: a noVNC web page, see README) and **they log in themselves**; it closes by itself and saves the session. Mention that automating LinkedIn may break its terms and can get the account restricted.
10. **Dry run**: `./run.sh --dry-run --limit 1` (stops before the final Submit). Show them the tailored CV (`data/cvs/…`), the log (`data/bot.log`) and the last screenshot (`data/shots/`). Ask before the first real run.

11. **Night mode**: offer it: "Want it to run at full speed tonight while you're not using the computer? Leave it plugged in and on, and run `./night.sh` before bed. It keeps the computer awake, applies for 8 hours with 3 browsers in parallel, then stops." Remind them the daily cap and the API spend limit still apply.

Finish with: what's set up, how to run (`./run.sh`, `./run-easy.sh`), how to see results (`report.py`), and that they can schedule it (`deploy/`).

## Running and checking

- `./run.sh` (company sites), `./run-easy.sh` (LinkedIn Easy Apply).
- `.venv/bin/python report.py`: applied, failed (with causes), skipped.
- Logs `data/bot.log`, CVs `data/cvs/`, screenshots `data/shots/`.
- If many failures share a cause, fix the cause (filters, a missing fact in `profile.yaml`) and re-run.

## Rules

- Never solve captchas, never enter payment/SIN/SSN/passport data, never invent facts.
- Never copy LinkedIn cookies (`li_at` or others) into the agent's browser: the user logs in themself.
- Watch the API spend: keep a spend limit on the key and use a key no other product depends on.
