# Job Apply Agent

**An AI agent that applies to jobs for you.** It finds postings, writes a one-page CV tailored to each posting from your real facts only, then opens the company's application site and fills the whole form like a person would: it creates the account, reads the email verification code, answers the questions and clicks Submit. It also does LinkedIn Easy Apply. You bring your own Claude API key.

## How it works

1. **Find**: company job boards (Greenhouse, Lever, Ashby) and LinkedIn's public job search, filtered by title, field and location (`searches.yaml`).
2. **Tailor**: for each posting, Claude picks and orders lines from your `facts.yaml` and bolds the posting's keywords. It never writes new text, so the CV stays true. Built as a one-page PDF with LaTeX.
3. **Apply**: a browser agent (Playwright + Claude) sees the page and fills it step by step. It answers from your `profile.yaml`, reads verification codes from your inbox, and skips anything it can't answer truthfully.
4. **Track**: every posting is stored in `data/jobs.db`. `report.py` shows what was applied, skipped and why.

It never solves captchas, never enters payment, SIN/SSN or passport numbers, and never invents experience.

## Setup

Needs Python 3.10+, [tectonic](https://tectonic-typesetting.github.io) (LaTeX) and a Claude API key.

```bash
git clone https://github.com/yahyaraissouni/job-apply-agent && cd job-apply-agent
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install --with-deps chromium
cp .env.example .env                    # add your ANTHROPIC_API_KEY and inbox
cp profile.example.yaml profile.yaml    # your answers to form questions
cp facts.example.yaml facts.yaml        # the only facts your CV may contain
./set-mail.sh                           # email app password, to read verification codes
```

Your `.env`, `profile.yaml`, `facts.yaml`, passwords and data stay on your machine (`.gitignore`).

## Run

```bash
./run.sh --dry-run        # does everything but stops before the final Submit
./run.sh                  # applies for real
.venv/bin/python report.py
```

**LinkedIn Easy Apply** needs you to log in once in the agent's browser: run `./login-screen.sh` on the server, open the noVNC page it shows and log in yourself (never copy cookies: LinkedIn kills copied sessions). Then `./run-easy.sh`. On a cloud server, LinkedIn may block the server's IP: `tunnel.sh` routes it through your home connection (`EASY_PROXY`).

To run it every 10 minutes on a Linux server, fill in `deploy/*.service` and enable the timers with systemd.

## Cost

Each application is many Claude calls (one per form step, with a screenshot). Expect tens of cents per application, more on long forms. **Set a spend limit on your API key** and start with the low caps in `searches.yaml`.

## Use it responsibly

Automated applying may break some sites' terms (LinkedIn's included). Review your `facts.yaml` and `profile.yaml` carefully: every answer goes out under your name.

## License

MIT
