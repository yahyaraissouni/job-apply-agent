"""Summary of the bot's work: applied, failed, skipped, and the most frequent failure reasons (to patch)."""
import collections
import re
import sqlite3
from pathlib import Path

c = sqlite3.connect(Path(__file__).resolve().parent / "data" / "jobs.db")
print("BY STATUS:", dict(c.execute("select status, count(*) from jobs group by 1").fetchall()))
print("\nAPPLIED:")
for t, co, loc, ts in c.execute("select title, company, location, ts from jobs where status='applied' order by ts"):
    print(f"  {ts[:16]}  {co} - {t} ({loc})")


def bucket(reason: str) -> str:
    r = reason.lower()
    for key, pat in [("captcha", r"captcha|verify you are human|hcaptcha|cloudflare"), ("stuck", r"stuck|too many steps|15 minutes"),
                     ("missing fact", r"unknown|not in the facts|don't have"), ("site down", r"maintenance|unavailable|down|500|502|503"),
                     ("account/login", r"sign in|login|password|account"), ("email code", r"code|verification"),
                     ("no official page", r"official page"), ("api error", r"error:")]:
        if re.search(pat, r):
            return key
    return "other"


print("\nFAILURES BY CAUSE:")
fails = c.execute("select reason, company, title from jobs where status='failed'").fetchall()
for k, n in collections.Counter(bucket(r) for r, *_ in fails).most_common():
    print(f"  {n:>3}  {k}")
    for r, co, t in [f for f in fails if bucket(f[0]) == k][:3]:
        print(f"         e.g. {co}: {r[:140]}")
print("\nSKIPS:", collections.Counter(r for (r,) in c.execute("select reason from jobs where status='skipped'")).most_common(6))
