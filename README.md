# Job Apply Agent

**An AI agent that applies to jobs for you.** It finds postings, writes a one-page CV tailored to each posting from your real facts only, then opens the company's application site and fills the whole form like a person would: it creates the account, reads the email verification code, answers the questions and clicks Submit. It also does LinkedIn Easy Apply. You bring your own Claude API key.

## How it works

1. **Find**: company job boards (Greenhouse, Lever, Ashby) and LinkedIn's public job search, filtered by title, field and location (`searches.yaml`).
2. **Tailor**: for each posting, Claude picks and orders lines from your `facts.yaml` and bolds the posting's keywords. It never writes new text, so the CV stays true. Built as a one-page PDF with LaTeX.
3. **Apply**: a browser agent (Playwright + Claude) sees the page and fills it step by step. It answers from your `profile.yaml`, reads verification codes from your inbox, and skips anything it can't answer truthfully.
4. **Track**: every posting is stored in `data/jobs.db`. `report.py` shows what was applied, skipped and why.

It never solves captchas, never enters payment, SIN/SSN or passport numbers, and never invents experience.

## Install (as a Claude Code skill)

```bash
git clone https://github.com/yahyaraissouni/job-apply-agent ~/.claude/skills/job-apply-agent
```

Then in Claude Code type **`/job-apply-agent`**. It runs a guided onboarding, one step at a time: install, Claude API key, email inbox for verification codes, your CV turned into `facts.yaml`, your answers in `profile.yaml`, what jobs to look for, optional LinkedIn login, and a dry run. Keys and passwords are typed in hidden prompts, never in the chat. `python3 check.py` shows what's left.

Your `.env`, `profile.yaml`, `facts.yaml`, passwords and data stay on your machine (`.gitignore`).

## Run

```bash
./run.sh --dry-run        # does everything but stops before the final Submit
./run.sh                  # applies for real
./run-easy.sh             # LinkedIn Easy Apply (after ./linkedin-login.sh)
.venv/bin/python report.py
```

**LinkedIn: no `li_at` cookie.** Copied cookies get killed by LinkedIn and log you out everywhere. Instead `./linkedin-login.sh` opens LinkedIn in the agent's own browser and you log in yourself once; the session is saved. On a server without a screen it opens a noVNC web page: on your computer run `ssh -N -L 6080:127.0.0.1:6080 you@your-server` and open http://localhost:6080/vnc.html. LinkedIn may block cloud IPs: `tunnel.sh` routes it through your home connection (`EASY_PROXY`).

To run it every 10 minutes on a Linux server, fill in `deploy/*.service` and enable the timers with systemd.

## Cost

Each application is many Claude calls (one per form step, with a screenshot). Expect tens of cents per application, more on long forms. **Set a spend limit on your API key** and start with the low caps in `searches.yaml`.

## Use it responsibly

Automated applying may break some sites' terms (LinkedIn's included). Review your `facts.yaml` and `profile.yaml` carefully: every answer goes out under your name.

## License

MIT
