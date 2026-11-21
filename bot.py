"""Internship auto-apply bot.

1. Finds internships on company job boards (Greenhouse, Lever, Ashby) and LinkedIn's PUBLIC search (no login).
2. Keeps only internships, paid (or pay not stated), not senior.
3. Finds the official application page (Claude web search).
4. Builds a one-page CV with the posting's keywords (cvgen.py, facts.yaml only).
5. The AI agent (agent.py) opens the site, creates the account if needed, fills everything, submits.

Run:  ./run.sh             apply
      ./run.sh --dry-run   do everything but stop before the final Submit
"""
from __future__ import annotations

import argparse
import zlib
import datetime as dt
import random
import re
import sqlite3
import time
import traceback
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

import agent
import ats
import cvgen
import discover

HERE = Path(__file__).resolve().parent
PROFILE = yaml.safe_load((HERE / "profile.yaml").read_text())
SEARCH = yaml.safe_load((HERE / "searches.yaml").read_text())
DB = HERE / "data" / "jobs.db"
LOG = HERE / "data" / "bot.log"
SHOTS = HERE / "data" / "shots"
EMAIL = PROFILE["email"]
CV_NAME = re.sub(r"\W+", "_", cvgen.FACTS["header"]["name"]).strip("_") + "_CV.pdf"
WORKER = 0


def log(msg: str) -> None:
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} [w{WORKER}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def db() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=60)
    c.execute("pragma journal_mode=wal")
    c.execute("""create table if not exists jobs(
        id text primary key, title text, company text, location text, url text, apply_url text,
        status text, reason text, keywords text, cv text, ts text)""")
    return c


def seen(c, jid: str) -> bool:
    """Applied or skipped = never again. Failed = retried in a later run (site down, missing email code...), 3 tries max."""
    c.execute("create table if not exists attempts(id text primary key, n int)")
    if c.execute("select 1 from jobs where id=? and status in ('applied','skipped')", (jid,)).fetchone():
        return True
    row = c.execute("select ts from jobs where id=? and status='failed'", (jid,)).fetchone()
    tries = (c.execute("select n from attempts where id=?", (jid,)).fetchone() or [0])[0]
    if row and (tries >= 3 or row[0] > (dt.datetime.now() - dt.timedelta(hours=4)).isoformat()):
        return True
    return False


def count_attempt(c, jid: str) -> None:
    c.execute("create table if not exists attempts(id text primary key, n int)")
    c.execute("insert into attempts values(?,1) on conflict(id) do update set n=n+1", (jid,))
    c.commit()


def record(c, job: dict, status: str, reason: str = "", apply_url: str = "", keywords: str = "", cv: str = "") -> None:
    c.execute("insert or replace into jobs values(?,?,?,?,?,?,?,?,?,?,?)",
              (job["id"], job.get("title", ""), job.get("company", ""), job.get("location", ""), job.get("linkedin_url", ""),
               apply_url, status, reason, keywords, cv, dt.datetime.now().isoformat(timespec="seconds")))
    c.commit()


def applied_today(c) -> int:
    return c.execute("select count(*) from jobs where status='applied' and ts >= ?", (dt.date.today().isoformat(),)).fetchone()[0]


def site_key(url: str) -> str:
    """Which 'site' a failure blocks: one company on shared job platforms, a data center for Workday."""
    from urllib.parse import parse_qs, urlparse
    u = urlparse(url)
    host = u.hostname or url
    wd = re.search(r"\.(wd\d+)\.myworkday", host)
    if wd:
        return wd.group(1) + ".myworkday"  # Workday maintenance is per data center
    if "greenhouse" in host:
        return "greenhouse/" + (parse_qs(u.query).get("for", [""])[0] or u.path.strip("/").split("/")[0])
    if any(k in host for k in ("lever.co", "ashbyhq", "smartrecruiters", "workable", "recruitee", "bamboohr")):
        return host + "/" + (u.path.strip("/").split("/") or [""])[0]
    return host


def facts_for(country: str) -> str:
    auth = PROFILE["work_authorization"].get(country) or (PROFILE["work_authorization"]["CA"] + "\n" + PROFILE["work_authorization"]["US"])
    lines = [PROFILE["facts_for_questions"].strip(), "WORK AUTHORIZATION FOR THIS JOB: " + auth, "Standard answers:"]
    lines += [f"- {a['q']} -> {a['a']}" for a in PROFILE["answers"] if a["a"]]
    return "\n".join(lines)


def candidates():
    """Job dicts in preference order: company job boards first (direct URL), then LinkedIn public search."""
    done = set()
    for job in ats.internships(SEARCH["must_title"], SEARCH.get("preferred", [])):
        done.add(job["id"])
        yield job
    for loc in SEARCH["locations"]:
        for kw in SEARCH["keywords"]:
            for jid in discover.search(kw, loc, pages=2):
                if jid not in done:
                    done.add(jid)
                    yield {"id": jid, "lazy": True}
            time.sleep(random.uniform(2, 5))


def run(dry_run: bool, limit: int | None, shard: int = 0, shards: int = 1) -> None:
    c = db()
    cap_run = limit or SEARCH["max_applications_per_run"]
    cap_day = SEARCH["max_applications_per_day"]
    done = 0
    down_hosts: set[str] = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for job in candidates():
                jid = job["id"]
                if zlib.crc32(jid.encode()) % shards != shard:
                    continue  # another worker handles this one
                if done >= cap_run or (not dry_run and applied_today(c) >= cap_day):
                    break
                if seen(c, jid):
                    continue
                if job.get("lazy"):
                    job = discover.posting(jid)
                tag = f"{job['title']} @ {job['company']} ({job['location']})"
                if not re.search(SEARCH["must_title"], job["title"], re.I):
                    record(c, job, "skipped", "not an internship")
                    continue
                if not ats.title_ok(job["title"], SEARCH["must_title"], SEARCH["skip_titles"]):
                    record(c, job, "skipped", "title filtered (field or level)")
                    continue
                if len(job["description"]) < 200:
                    record(c, job, "skipped", "no description")
                    continue
                try:
                    url = job.get("apply_url") or discover.official_url(job)
                    if not url:
                        record(c, job, "skipped", "official page not found (probably LinkedIn Easy Apply only)")
                        log(f"skip {tag}: no official page")
                        continue
                    host = site_key(url)
                    if host in down_hosts:
                        record(c, job, "failed", f"{host} down this run", url)
                        continue
                    dup = c.execute("select status, ts from jobs where apply_url=? and id<>? order by ts desc", (url, jid)).fetchone()
                    if dup and (dup[0] == "applied" or (dup[0] == "failed" and dup[1] > (dt.datetime.now() - dt.timedelta(hours=4)).isoformat())):
                        record(c, job, "skipped" if dup[0] == "applied" else "failed", "same posting as another listing", url)
                        log(f"skip {tag}: duplicate of a posting already handled")
                        continue
                    safe = re.sub(r"[^A-Za-z0-9]+", "_", job["company"])[:40] or jid
                    cv_pdf = HERE / "data" / "cvs" / f"{jid}_{safe}" / CV_NAME
                    sel = cvgen.tailored_cv(f"{job['title']} at {job['company']}, {job['location']}\n\n{job['description']}", cv_pdf)
                    if sel.get("paid") == "no":
                        record(c, job, "skipped", "unpaid", url)
                        log(f"skip {tag}: unpaid")
                        continue
                    country = sel.get("country", "other")
                    log(f"APPLYING {tag} [{country}] via {url[:100]}")
                    ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="en-US",
                                              timezone_id="America/Toronto", user_agent=discover.UA)
                    page = ctx.new_page()
                    page.set_default_timeout(15000)
                    try:
                        status, note = agent.apply(page, url, job["title"], job["company"], cv_pdf,
                                                   facts_for(country), EMAIL, dry_run, log, SHOTS)
                    finally:
                        ctx.close()
                    if status == "failed":
                        count_attempt(c, jid)
                        if re.search(r"\bmaintenance\b|currently unavailable|cannot be reached|site is down|captcha", note, re.I):
                            down_hosts.add(host)
                    record(c, job, status, note[:300], url, ", ".join(sel.get("keywords", [])), str(cv_pdf))
                    log(f"{status.upper()}: {tag} {note[:120]}")
                    if status in ("applied", "dry-run"):
                        done += 1
                    time.sleep(random.uniform(10, 30))
                except Exception as e:
                    record(c, job, "failed", f"error: {str(e).splitlines()[0][:200]}")
                    log(f"ERROR {tag}: {traceback.format_exc()[-600:]}")
        finally:
            browser.close()
    log(f"run done: {done} {'dry-runs' if dry_run else 'applications'}; {applied_today(c)} applied today")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    a = ap.parse_args()
    WORKER = a.shard
    run(a.dry_run, a.limit, a.shard, a.shards)
