"""LinkedIn Easy Apply worker (logged-in browser profile made by login-screen.sh, LinkedIn traffic optionally through EASY_PROXY).

Finds Easy Apply internships with LinkedIn's public search (Easy Apply filter), builds the tailored CV,
then the same AI agent as for company sites opens the posting, clicks Easy Apply and fills every page.
"""
from __future__ import annotations

import argparse
import os
import random
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

import agent
import ats
import bot
import cvgen
import discover

HERE = Path(__file__).resolve().parent
PROXY = os.environ.get("EASY_PROXY")  # optional, e.g. socks5://127.0.0.1:1080 (see README)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"


def run(dry_run: bool, limit: int | None) -> None:
    bot.WORKER = "easy"
    c = bot.db()
    S = bot.SEARCH
    cap = limit or S["max_applications_per_run"]
    done = 0
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(HERE / "data" / "browser"), headless=True, locale="en-US",
                                                   timezone_id="America/Toronto", viewport={"width": 1280, "height": 860},
                                                   proxy={"server": PROXY} if PROXY else None, user_agent=UA)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(15000)
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(4)
            if re.search(r"/login|/checkpoint|/authwall|/uas/", page.url):
                bot.log(f"STOPPED: LinkedIn wants a new login ({page.url[:80]}). Run login-screen.sh again.")
                (HERE / "data" / "STOPPED_EASY").write_text(page.url)
                return
            for loc in S["locations"]:
                for kw in S["keywords"]:
                    for jid in discover.search(kw, loc, pages=1, easy_apply=True):
                        if done >= cap or bot.applied_today(c) >= S["max_applications_per_day"]:
                            return
                        if bot.seen(c, jid):
                            continue
                        job = discover.posting(jid)
                        tag = f"{job['title']} @ {job['company']} ({job['location']})"
                        if not ats.title_ok(job["title"], S["must_title"], S["skip_titles"]):
                            bot.record(c, job, "skipped", "title filtered")
                            continue
                        safe = re.sub(r"[^A-Za-z0-9]+", "_", job["company"])[:40] or jid
                        cv_pdf = HERE / "data" / "cvs" / f"{jid}_{safe}" / bot.CV_NAME
                        try:
                            sel = cvgen.tailored_cv(f"{job['title']} at {job['company']}, {job['location']}\n\n{job['description']}", cv_pdf)
                            if sel.get("paid") == "no":
                                bot.record(c, job, "skipped", "unpaid")
                                continue
                            url = f"https://www.linkedin.com/jobs/view/{jid}/"
                            bot.log(f"APPLYING (Easy Apply) {tag} [{sel.get('country')}]")
                            status, note = agent.apply(page, url, job["title"], job["company"], cv_pdf,
                                                       bot.facts_for(sel.get("country", "other")) +
                                                       "\nThis is a LinkedIn posting: click the 'Easy Apply' button, then fill each page of the "
                                                       "LinkedIn form (Next / Review / Submit application). Uncheck 'Follow company'.",
                                                       bot.EMAIL, dry_run, bot.log, bot.SHOTS)
                            if status == "failed":
                                bot.count_attempt(c, jid)
                            bot.record(c, job, status, ("easy apply: " + note)[:300], url, ", ".join(sel.get("keywords", [])), str(cv_pdf))
                            bot.log(f"{status.upper()}: {tag} (Easy Apply) {note[:100]}")
                            if status in ("applied", "dry-run"):
                                done += 1
                            time.sleep(random.uniform(20, 45))
                        except Exception as e:
                            bot.record(c, job, "failed", f"easy apply error: {str(e).splitlines()[0][:200]}")
                            bot.log(f"ERROR (Easy Apply) {tag}: {e}")
                    time.sleep(random.uniform(3, 6))
        finally:
            ctx.close()
            bot.log(f"easy apply run done: {done}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    if (HERE / "data" / "STOPPED_EASY").exists():
        bot.log("easy apply not running: LinkedIn wants a new login (data/STOPPED_EASY)")
    else:
        run(a.dry_run, a.limit)
