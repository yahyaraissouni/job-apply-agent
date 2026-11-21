#!/usr/bin/env python3
"""Setup checklist (standard library only). Prints each onboarding step as OK or TODO, in order.
The skill runs this first and resumes onboarding at the first TODO."""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def env() -> dict:
    out = {}
    f = HERE / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            m = re.match(r"\s*([A-Z_]+)\s*=\s*([^#\s]*)", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def own(name: str) -> bool:
    """File exists and is no longer the untouched example."""
    f, ex = HERE / name, HERE / name.replace(".yaml", ".example.yaml")
    return f.exists() and (not ex.exists() or f.read_text() != ex.read_text()) and "example.com" not in f.read_text()


E = env()
venv_py = HERE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
browsers = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", Path.home() / ("Library/Caches/ms-playwright" if sys.platform == "darwin" else ".cache/ms-playwright")))
steps = [
    ("python", venv_py.exists(), "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"),
    ("browser", browsers.exists() and any(browsers.glob("chromium*")), ".venv/bin/playwright install --with-deps chromium"),
    ("latex", bool(shutil.which("tectonic") or os.environ.get("TECTONIC")), "install tectonic (macOS: brew install tectonic; Linux: see README)"),
    ("claude_key", E.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-"), "./set-key.sh  (user types the key in the hidden prompt)"),
    ("email", bool(E.get("MAIL_USER")) and "example.com" not in E.get("MAIL_USER", ""), "set MAIL_USER and MAIL_IMAP_HOST in .env"),
    ("email_password", (HERE / "secrets" / "mail_app_password").exists(), "./set-mail.sh  (user types the app password in the hidden prompt)"),
    ("facts", own("facts.yaml"), "build facts.yaml from the user's CV (see SKILL.md)"),
    ("profile", own("profile.yaml"), "build profile.yaml by asking the user the questions (see SKILL.md)"),
    ("searches", (HERE / "data" / ".searches_reviewed").exists(), "review searches.yaml with the user, then: mkdir -p data && touch data/.searches_reviewed"),
    ("linkedin_login (optional)", (HERE / "data" / ".linkedin_ok").exists(), "./linkedin-login.sh  (user logs in themself; skip if no Easy Apply)"),
    ("dry_run", (HERE / "data" / "jobs.db").exists(), "./run.sh --dry-run --limit 1"),
]
for name, ok, todo in steps:
    print(f"{'OK  ' if ok else 'TODO'} {name}" + ("" if ok else f"  ->  {todo}"))
left = [n for n, ok, _ in steps if not ok and "optional" not in n]
print("\nREADY" if not left else f"\nNEXT: {left[0]}")
