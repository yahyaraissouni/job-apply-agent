# Job Apply Agent

**An AI agent that applies to jobs for you, with an anti-ATS CV rewritten for every single posting.** For each job it reads the description, rebuilds your one-page CV around that posting's keywords so it gets past ATS filters (applicant tracking systems that reject CVs before a human sees them), from your real facts only, never invented, then opens the company's site and fills the whole application like a person would: creates the account, reads the email verification code, answers the questions, clicks Submit. Also does LinkedIn Easy Apply. **About $0.15–0.30 per application** with your own Claude API key.

## How it works

1. **Find**: company job boards (Greenhouse, Lever, Ashby) and LinkedIn's public job search, filtered by title, field and location (`searches.yaml`).
2. **Tailor (anti-ATS)**: for each posting, Claude picks the lines and skills from your `facts.yaml` that use the posting's own keywords, puts the most relevant first and bolds them. The PDF is ATS-friendly: one page, one column, real selectable text, standard section titles (Education, Experience, Skills), no images or tables. It never writes new text, so the CV stays true.
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

## Where it runs

- **Your own computer** (macOS or Linux; Windows through WSL). Nothing else needed.
- **Night mode**: before bed, leave it plugged in and on, run `./night.sh` (8 h, 3 browsers in parallel by default; `./night.sh 10 4` for 10 h with 4). It keeps the computer awake while it applies at full speed, then stops by itself. The daily cap still applies.
- **A server** only if you want it 24/7 with your computer off (a small VPS or Oracle Cloud's free tier; see `deploy/`). LinkedIn often blocks cloud IPs, so Easy Apply works best from home.
- Not on Anthropic's cloud: the Claude API only does the thinking; the browser and your logins live on your machine.

## Cost per application

Measured on 150 real submitted applications: a form takes **about 45 agent steps** (median), 6 of them on Sonnet when the agent gets stuck, the rest on Haiku. That is **about $0.15 per submitted application**, including the tailored CV (estimated from Claude's prices; long Workday forms cost more). Postings that fail midway also cost calls, so **budget about $0.30 per application sent**: 30 applications/day ≈ $9/day.

**Set a monthly spend limit on your API key** (platform.claude.com → Settings → Limits) and use a key that nothing else depends on.

## Use it responsibly

Automated applying may break some sites' terms (LinkedIn's included). Review your `facts.yaml` and `profile.yaml` carefully: every answer goes out under your name.

## License

MIT
