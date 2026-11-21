"""Internships straight from company job boards (Greenhouse, Lever, Ashby): real application URL, no search needed."""
from __future__ import annotations

import concurrent.futures as cf
import html
import re

import httpx

GREENHOUSE = """jumptrading imc drweng towerresearchcapital akunacapital wehrtyou virtu janestreet point72 schonfeld flowtraders
chicagotrading worldquant aqr pdtpartners clearstreet stripe databricks figma robinhood airbnb lyft pinterest dropbox reddit
discord coinbase instacart cloudflare datadog mongodb twilio okta samsara brex affirm chime sofi gusto carta airtable asana
gitlab elastic cockroachlabs scaleai anthropic nuro waymo faire hootsuite squarespace duolingo roblox epicgames riotgames
twitch nextdoor peloton oscar andurilindustries spacex relativity rocketlab""".split()
LEVER = "palantir spotify belvederetrading".split()
ASHBY = "ramp openai notion linear replit cursor perplexity cohere modal supabase posthog plaid wealthsimple 1password hopper sentry".split()

FIELD = re.compile(r"software|engineer|develop|data|machine learning|\bml\b|\bai\b|artificial|quant|trad|research|"
                   r"\bit\b|computer|\btech\b|technolog|platform|infra|security|systems|backend|front|full.?stack|mobile|cloud|"
                   r"informatique|logiciel|développ", re.I)
# Fields he did not ask for, even when the title also says "engineer", "research" or "data".
NOT_FIELD = re.compile(r"mechanical|electrical|hardware|propulsion|civil|chemical|aerospace|manufactur|fabricat|"
                       r"structural|industrial|biomed|environmental|mining|petroleum|nuclear|materials|"
                       r"sales|marketing|legal|policy|recruit|human resources|\bhr\b|accounting|audit|"
                       r"\bux\b|graphic|equit(y|ies) research|sector analyst|technician|apprentice", re.I)


def title_ok(title: str, must_title: str, skip_titles: str = "") -> bool:
    """Internship in his fields: software, AI/ML, quant, data, IT."""
    return bool(re.search(must_title, title, re.I) and FIELD.search(title) and not NOT_FIELD.search(title)
                and not (skip_titles and re.search(skip_titles, title, re.I)))


NORTH_AMERICA = re.compile(r"united states|\busa?\b|remote|canada|montr|toronto|vancouver|ottawa|waterloo|calgary|"
                           r"new york|\bny\b|nyc|san francisco|\bsf\b|seattle|chicago|boston|austin|los angeles|"
                           r"mountain view|palo alto|menlo|bellevue|denver|atlanta|miami|dallas|houston|philadelphia|"
                           r"washington|pittsburgh|\b(ca|wa|tx|il|ma|co|ga|fl|nj|pa|nc|va|or|ut|az|mn|mi|oh|md|ny)\b", re.I)
ELSEWHERE = re.compile(r"london|singapore|hong kong|amsterdam|sydney|india|bangalore|dublin|tokyo|paris|berlin|"
                       r"zurich|shanghai|mumbai|tel aviv|warsaw|madrid|seoul|brazil|mexico city", re.I)


def _strip(h: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(h or "")))).strip()


def _keep(title: str, location: str, must_title: str) -> bool:
    if not title_ok(title, must_title):
        return False
    if ELSEWHERE.search(location) and not re.search(r"canada|united states|new york|remote.*(us|canada)", location, re.I):
        return False
    return bool(NORTH_AMERICA.search(location))


def _greenhouse(slug: str, must_title: str) -> list[dict]:
    r = httpx.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true", timeout=30)
    if r.status_code != 200:
        return []
    out = []
    for j in r.json().get("jobs", []):
        loc = j.get("location", {}).get("name", "")
        if _keep(j["title"], loc, must_title):
            out.append({"id": f"gh:{slug}:{j['id']}", "title": j["title"], "company": j.get("company_name") or slug,
                        "location": loc, "description": _strip(j.get("content", ""))[:12000],
                        "apply_url": f"https://job-boards.greenhouse.io/embed/job_app?for={slug}&token={j['id']}",  # the bare form, never redirected
                        "linkedin_url": j["absolute_url"]})
    return out


def _lever(slug: str, must_title: str) -> list[dict]:
    r = httpx.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=30)
    if r.status_code != 200:
        return []
    out = []
    for j in r.json():
        loc = (j.get("categories") or {}).get("location", "") or ""
        if _keep(j["text"], loc, must_title):
            desc = _strip(j.get("descriptionPlain") or j.get("description", "")) + " " + " ".join(
                _strip(l.get("content", "")) for l in j.get("lists", []))
            out.append({"id": f"lv:{slug}:{j['id']}", "title": j["text"], "company": slug, "location": loc,
                        "description": desc[:12000], "apply_url": j.get("applyUrl") or j["hostedUrl"],
                        "linkedin_url": j["hostedUrl"]})
    return out


def _ashby(slug: str, must_title: str) -> list[dict]:
    r = httpx.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=30)
    if r.status_code != 200:
        return []
    out = []
    for j in r.json().get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations", [])]
        loc = " / ".join(l for l in locs if l)
        if _keep(j["title"], loc, must_title):
            out.append({"id": f"ab:{slug}:{j['id']}", "title": j["title"].strip(), "company": slug, "location": loc,
                        "description": _strip(j.get("descriptionHtml", ""))[:12000],
                        "apply_url": j.get("applyUrl") or j["jobUrl"], "linkedin_url": j["jobUrl"]})
    return out


def internships(must_title: str, preferred: list[str]) -> list[dict]:
    jobs: list[dict] = []
    tasks = [(_greenhouse, s) for s in GREENHOUSE] + [(_lever, s) for s in LEVER] + [(_ashby, s) for s in ASHBY]
    with cf.ThreadPoolExecutor(12) as ex:
        for res in ex.map(lambda t: _safe(t[0], t[1], must_title), tasks):
            jobs += res
    rank = lambda j: next((i for i, p in enumerate(preferred) if re.search(p, j["location"], re.I)), len(preferred))
    return sorted(jobs, key=rank)


def _safe(fn, slug, must_title):
    try:
        return fn(slug, must_title)
    except Exception:
        return []


if __name__ == "__main__":
    js = internships(r"intern|internship|stagiaire|co-?op", ["montr", "new york|nyc|\\bny\\b"])
    print(len(js), "internships")
    for j in js[:25]:
        print(f"  {j['company']:<22} {j['title'][:60]:<60} {j['location'][:40]}")
