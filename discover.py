"""Find jobs without logging in to LinkedIn, and the official page to apply on.

- LinkedIn public (guest) search: titles, companies, descriptions. No account, no session to lose.
- Claude web search: the company's own application page for that posting (careers site / ATS).
"""
from __future__ import annotations

import html
import json
import os
import re
import time
from urllib.parse import quote_plus

import httpx

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
GUEST = "https://www.linkedin.com/jobs-guest/jobs/api"


def _get(url: str) -> str:
    for attempt in range(3):
        r = httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}, timeout=30, follow_redirects=True)
        if r.status_code == 200:
            return r.text
        time.sleep(5 * (attempt + 1))
    return ""


def search(keywords: str, location: str, remote: bool = False, pages: int = 2, period: str = "r86400",
           easy_apply: bool = False) -> list[str]:
    ids: list[str] = []
    for p in range(pages):
        url = (f"{GUEST}/seeMoreJobPostings/search?keywords={quote_plus(keywords)}&location={quote_plus(location)}"
               f"&f_TPR={period}&sortBy=DD&start={p * 25}" + ("&f_WT=2" if remote else "") + ("&f_AL=true" if easy_apply else ""))
        h = _get(url)
        found = re.findall(r"jobPosting:(\d+)", h)
        for i in found:
            if i not in ids:
                ids.append(i)
        if len(found) < 10:
            break
        time.sleep(2)
    return ids


def posting(job_id: str) -> dict:
    h = _get(f"{GUEST}/jobPosting/{job_id}")

    def grab(pat):
        m = re.search(pat, h, re.S)
        return html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""

    desc = grab(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>')
    return {
        "id": job_id,
        "title": re.sub(r"\s+", " ", grab(r'top-card-layout__title[^>]*>(.*?)</h2>')),
        "company": re.sub(r"\s+", " ", grab(r'topcard__org-name-link[^>]*>(.*?)</a>') or grab(r'topcard__flavor">(.*?)</span>')),
        "location": re.sub(r"\s+", " ", grab(r'topcard__flavor topcard__flavor--bullet">(.*?)</span>')),
        "description": re.sub(r"\s+", " ", desc),
        "linkedin_url": f"https://www.linkedin.com/jobs/view/{job_id}/",
    }


def official_url(job: dict) -> str | None:
    """Ask Claude (with web search) for the official application page of this posting."""
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
    if os.environ.get("ANTHROPIC_WORKSPACE_ID"):
        headers["anthropic-workspace-id"] = os.environ["ANTHROPIC_WORKSPACE_ID"]
    prompt = (f"Find the official online application page for this job posting:\n"
              f"Title: {job['title']}\nCompany: {job['company']}\nLocation: {job['location']}\n"
              f"Excerpt: {job['description'][:600]}\n\n"
              "It must be on the company's careers site or its applicant tracking system (Greenhouse, Lever, Ashby, Workday, "
              "SmartRecruiters, iCIMS, Taleo, BambooHR, Workable, Jobvite...), for THIS posting (same title), still open. A page that links straight to the official form (e.g. it carries the ATS job id) is acceptable if the official one isn't found. "
              "Not LinkedIn, Indeed, Glassdoor or another job board. "
              'Reply with JSON only: {"url": "<url or null>", "confidence": "high|low"}')
    body = {"model": os.environ.get("JOBBOT_MODEL", "claude-haiku-5-5"), "max_tokens": 6000,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
            "messages": [{"role": "user", "content": prompt}]}
    r = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=180)
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    if os.environ.get("JOBBOT_DEBUG"):
        print("OFFICIAL_URL answer:", text[:600])
    m = re.search(r"\{[^{}]*\"url\"[^{}]*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    url = d.get("url")
    if not url or re.search(r"linkedin\.|indeed\.|glassdoor\.|ziprecruiter|simplyhired|monster\.", url, re.I):
        return None
    # check the page exists and is about this posting (a third-party mirror is fine: the agent clicks through)
    page = _get(url)
    words = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", job["title"]) if w.lower() not in ("intern", "internship", "stagiaire")]
    ats = re.search(r"greenhouse|lever\.co|ashbyhq|myworkday|smartrecruiters|icims|taleo|bamboohr|workable|jobvite|careerpuck|successfactors", url, re.I)
    if d.get("confidence") == "high":
        return url  # trust a confident answer (many careers sites block plain HTTP fetches)
    if not page and not ats:
        return None
    if page and not ats and words and not any(w.lower() in page.lower() for w in words[:4]):
        return None
    return url


if __name__ == "__main__":
    import sys
    ids = search(sys.argv[1], sys.argv[2], pages=1, period="r604800")
    print(len(ids), "postings")
    for i in ids[:3]:
        j = posting(i)
        print(j["title"], "|", j["company"], "|", j["location"], "|", len(j["description"]), "chars")
        print("   official:", official_url(j))
