"""Build a one-page CV tailored to a job description, from facts.yaml only.

The LLM only CHOOSES: which bullet ids, in which order, which skills (from the pool),
which words to bold. It never writes text, so the CV can't contain an invented fact.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent
FACTS = yaml.safe_load((HERE / "facts.yaml").read_text())
MODEL = os.environ.get("JOBBOT_MODEL", "claude-haiku-5-5")


# ---------- choosing ----------

def _catalog() -> str:
    lines = []
    for exp in FACTS["experience"]:
        lines.append(f"## experience {exp['id']} (pick {exp['min_bullets']}-{exp['max_bullets']}, max one per group); subtitles: {list(exp['subtitles'])}")
        for b in exp["bullets"]:
            lines.append(f"- {b['id']} [group {b['group']}]: {b['text']}")
    lines.append("## projects (pick 2-4, in order)")
    for p in FACTS["projects"]:
        lines.append(f"- {p['id']}: {p['name']} -- {p['text']}")
    lines.append("## skills pool (choose and order, per category; never add anything else)")
    for cat, items in FACTS["skills"].items():
        lines.append(f"- {cat}: {', '.join(items)}")
    return "\n".join(lines)


PROMPT = """You tailor a CV to a job posting. You may ONLY choose from the catalog below; you never write new text.

Return JSON only, no prose:
{{
  "subtitles": {{"<experience id>": "<subtitle key>"}},
  "bullets": {{"<experience id>": ["<bullet id>", ...]}},   // most relevant first
  "projects": ["<project id>", ...],                           // 3 to 4
  "skills": {{"<category>": ["<skill>", ...]}},                 // only from the pool, most relevant first, 4-10 per category
  "bold": ["<exact phrase>", ...],                              // 6-14 phrases (include single tech words like "TypeScript", "PostgreSQL" when the posting asks for them) copied EXACTLY from the chosen bullets that match the posting's keywords
  "keywords": ["<keyword from the posting>", ...],              // the posting's main required skills, for the log
  "paid": "yes|no|unknown",                                     // "no" only if the posting says unpaid / volunteer / for credit only
  "country": "CA|US|other"                                      // country where the job is located
}}

Rules: respect each experience's min/max bullets and at most one bullet per group. Prefer bullets whose words match the posting's required skills and duties.

CATALOG
{catalog}

JOB POSTING
{job}
"""


def choose(job_text: str) -> dict:
    key = os.environ["ANTHROPIC_API_KEY"]
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    if os.environ.get("ANTHROPIC_WORKSPACE_ID"):
        headers["anthropic-workspace-id"] = os.environ["ANTHROPIC_WORKSPACE_ID"]
    body = {
        "model": MODEL,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": PROMPT.format(catalog=_catalog(), job=job_text[:12000])}],
    }
    r = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=120)
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON in model answer: {text[:300]}")
    return json.loads(m.group(0))


def validate(choice: dict) -> dict:
    """Drop anything not in facts.yaml and enforce the per-experience limits."""
    out = {"subtitles": {}, "bullets": {}, "projects": [], "skills": {}, "bold": [], "keywords": choice.get("keywords", [])[:20],
           "paid": choice.get("paid", "unknown"), "country": choice.get("country", "other")}
    for exp in FACTS["experience"]:
        by_id = {b["id"]: b for b in exp["bullets"]}
        sub = choice.get("subtitles", {}).get(exp["id"])
        out["subtitles"][exp["id"]] = sub if sub in exp["subtitles"] else next(iter(exp["subtitles"]))
        picked, groups = [], set()
        for bid in choice.get("bullets", {}).get(exp["id"], []):
            b = by_id.get(bid)
            if b and b["group"] not in groups:
                picked.append(bid)
                groups.add(b["group"])
        for b in exp["bullets"]:  # top up to the minimum, in file order
            if len(picked) >= exp["min_bullets"]:
                break
            if b["group"] not in groups:
                picked.append(b["id"])
                groups.add(b["group"])
        out["bullets"][exp["id"]] = picked[: exp["max_bullets"]]
    proj_ids = [p["id"] for p in FACTS["projects"]]
    out["projects"] = [p for p in choice.get("projects", []) if p in proj_ids][:4] or proj_ids[:3]
    for cat, pool in FACTS["skills"].items():
        chosen = [s for s in choice.get("skills", {}).get(cat, []) if s in pool]
        out["skills"][cat] = chosen or pool[:6]
    chosen_text = " ".join(_bullet_text(e, b) for e, ids in out["bullets"].items() for b in ids)
    out["bold"] = [p for p in choice.get("bold", []) if isinstance(p, str) and 2 < len(p) < 60 and p in chosen_text][:14]
    return out


# ---------- rendering ----------

def _bullet_text(exp_id: str, bullet_id: str) -> str:
    exp = next(e for e in FACTS["experience"] if e["id"] == exp_id)
    return next(b["text"] for b in exp["bullets"] if b["id"] == bullet_id)


def _tex_escape_plain(s: str) -> str:
    # facts.yaml already escapes % and & where needed; only fix stray characters here
    return s.replace("#", "\\#").replace("_", "\\_")


def _bold(s: str, phrases: list[str]) -> str:
    for p in sorted(phrases, key=len, reverse=True):
        i = s.find(p)
        if i >= 0 and "\\textbf{" not in s[max(0, i - 8):i]:
            s = s[:i] + "\\textbf{" + p + "}" + s[i + len(p):]
    return s


def render_tex(sel: dict, drop: int = 0) -> str:
    """drop = how many low-priority lines to remove to fit one page."""
    f = FACTS
    bullets = {k: list(v) for k, v in sel["bullets"].items()}
    projects = list(sel["projects"])
    # trimming order: last project, then last bullet of the first experience (never below min)
    first = f["experience"][0]
    for _ in range(drop):
        if len(projects) > 2:
            projects.pop()
        elif len(bullets[first["id"]]) > first["min_bullets"]:
            bullets[first["id"]].pop()
    L = [r"\input{preamble}", r"\begin{document}", r"\begin{center}",
         r"{\LARGE\bfseries " + f["header"]["name"] + r"}\\ \vspace{2pt}",
         r"\small " + f["header"]["line"], r"\end{center}", r"\vspace{-8pt}", r"\section{Education}", r"\sstart"]
    for e in f["education"]:
        L.append(rf"\entry{{{e['school']}}}{{{e['place']}}}{{{e['degree']}}}{{{e['dates']}}}")
    L += [r"\send", r"\section{Experience}", r"\sstart"]
    for exp in f["experience"]:
        sub = exp["subtitles"][sel["subtitles"][exp["id"]]]
        L.append(rf"\entry{{{exp['title']}}}{{{exp['place']}}}{{{sub}}}{{{exp['dates']}}}")
        L.append(r"\bstart")
        for bid in bullets[exp["id"]]:
            L.append(r"\item " + _bold(_tex_escape_plain(_bullet_text(exp["id"], bid)), sel["bold"]))
        L.append(r"\bend")
    if f.get("other_experience"):
        L.append(r"\head{Other Experience \textnormal{-- " + f["other_experience"] + r"}}{}\vspace{-2pt}")
    L += [r"\send", r"\section{Projects}", r"\sstart"]
    shorts = []
    for pid in projects:
        p = next(x for x in f["projects"] if x["id"] == pid)
        if p.get("short"):
            shorts.append(r"\item \textbf{" + p["name"] + ":} " + p["text"])
            continue
        tech = r" \textnormal{-- " + p["tech"] + "}" if p["tech"] else ""
        link = r"\href{" + p["link"] + "}{GitHub}" if p["link"] else ""
        L += [rf"\head{{{p['name']}{tech}}}{{{link}}}", r"\bstart", r"\item " + _tex_escape_plain(p["text"]), r"\bend"]
    if shorts:
        L += [r"\item[] \bstart"] + shorts + [r"\bend"]
    L.append(r"\send")
    if f.get("leadership"):
        L += [r"\section{Leadership and Community}", r"\sstart", r"\item[] \bstart"]
        L += [r"\item " + x for x in f["leadership"]]
        L += [r"\bend", r"\send"]
    L += [r"\section{Technical Skills}", r"\small"]
    rows = [rf"\textbf{{{cat}:}} " + ", ".join(_tex_escape_plain(s) for s in skills) for cat, skills in sel["skills"].items() if skills]
    L.append("\\\\\n".join(rows))
    L += [r"\section{Languages and Interests}", r"\small",
          f["languages_line"] + r" \quad --- \quad " + f["interests_line"], r"\end{document}"]
    tex = "\n".join(L) + "\n"
    for bad in f.get("banned_phrases") or []:
        if bad.lower() in tex.lower():
            raise ValueError(f"banned phrase in CV: {bad}")
    return tex


def _pages(pdf: Path) -> int:
    data = pdf.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", data)) or (1 if b"%%EOF" in data else 0)


def build_pdf(sel: dict, out_pdf: Path) -> Path:
    tectonic = os.environ.get("TECTONIC", shutil.which("tectonic") or "tectonic")
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(HERE / "preamble.tex", d)
        for drop in range(0, 6):
            (Path(d) / "cv.tex").write_text(render_tex(sel, drop))
            subprocess.run([tectonic, "-X", "compile", "cv.tex"], cwd=d, check=True, capture_output=True, timeout=300)
            pdf = Path(d) / "cv.pdf"
            if _pages_by_tectonic(Path(d)) <= 1:
                break
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, out_pdf)
    return out_pdf


def _pages_by_tectonic(d: Path) -> int:
    # pdfinfo is exact when present; otherwise count page objects
    if shutil.which("pdfinfo"):
        out = subprocess.run(["pdfinfo", str(d / "cv.pdf")], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        if m:
            return int(m.group(1))
    return _pages(d / "cv.pdf")


def tailored_cv(job_text: str, out_pdf: Path) -> dict:
    sel = validate(choose(job_text))
    build_pdf(sel, out_pdf)
    return sel


if __name__ == "__main__":
    import sys
    job = Path(sys.argv[1]).read_text()
    sel = tailored_cv(job, Path(sys.argv[2]))
    print(json.dumps(sel, indent=1))
