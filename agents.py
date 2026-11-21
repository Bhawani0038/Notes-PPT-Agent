"""Agents: research(+history) -> outline -> storyteller -> designer(PDF) -> slides(PPT) -> reviewer."""
import os
import re

from config import OUTPUT_DIR
from llm import chat, parse_json
from tools import gather_sources
from pdf_builder import build_pdf, THEMES
from pptx_builder import build_pptx

LANG = {
    "English": "Write in simple, clear English.",
    "Hinglish": "Write in Hinglish: Hindi in Roman script mixed naturally with English technical terms "
                "(example: 'Is concept ko samajhna bahut easy hai'). Never use Devanagari script.",
}
YEAR = re.compile(r"\b(1[5-9]\d\d|20[0-2]\d)\b")


def slug(topic):
    return re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:40] or "content"


def _out_dir(s):
    d = s.get("out_dir") or OUTPUT_DIR
    os.makedirs(d, exist_ok=True)
    return d


def _fb(feedback):
    return f"\n\nREVIEWER FEEDBACK - fix every point:\n{feedback}" if feedback else ""


def _ctx(s):
    return f"Topic: {s['topic']}\nAudience: {s['audience']} (level: {s['level']})\n"


# 1. RESEARCH (concepts + history) -----------------------------------------
def research_agent(s, feedback=None, log=print):
    t = s["topic"]
    log("Research: concept queries bana raha hoon...")
    q = parse_json(chat(
        "You plan web research for educational content. Reply ONLY with JSON: {\"queries\": [5 short search queries]}.",
        _ctx(s) + "Cover: definition, how it works, real-world case studies, common mistakes, best practices."
        + _fb(feedback), json_mode=True)) or {}
    queries = [str(x) for x in q["queries"]][:6] if isinstance(q.get("queries"), list) else []
    queries = queries or [t, f"{t} tutorial", f"{t} real world examples"]
    log(f"Research: {len(queries)} concept queries ke sources collect ho rahe hain...")
    sources = gather_sources(queries, max_chars=11000, fetch_pages=6)

    hist_queries = [f"history of {t}", f"who invented {t}", f"{t} origin problem it solved",
                    f"{t} limitations drawbacks", f"{t} modern alternatives successor better approach"]
    log("Research: historical sources collect ho rahe hain (kisne banaya, kyun, limitations, aage kya aaya)...")
    hsources = gather_sources(hist_queries, max_chars=11000, fetch_pages=6)

    log("Research: history notes bana raha hoon...")
    s["history"] = chat(
        "You are a careful historian of science and technology writing for students. Use ONLY the sources given "
        "(plus extremely well-known, certain facts). NEVER invent names, dates, quotes or organizations. "
        "If a detail is not confirmed by the sources, write 'not clearly documented' instead of guessing.",
        f"{_ctx(s)}\nHISTORY SOURCES:\n{hsources or '(none found)'}\n\n"
        "Write markdown with these sections:\n"
        "## Historical Timeline (year - person/organization - what happened; mark approximate dates)\n"
        "## The Problem Before It Existed\n## Who Created It and Why\n"
        "## Limitations of the Original Approach\n"
        "## What Came Next (better approaches that fixed those limits, and their own trade-offs)\n"
        "## Modern Best Practice\n## Sources (only URLs that appear above)" + _fb(feedback), temperature=0.2)

    log("Research: concept notes bana raha hoon...")
    s["concepts"] = chat(
        "You are an educational research analyst. Build accurate, concrete study notes from the sources and "
        "well-established knowledge. Prefer specifics (real tools, real datasets, real companies, real numbers "
        "from the sources) over generic statements. Never invent statistics or URLs.",
        f"{_ctx(s)}\nSOURCES:\n{sources or '(no internet results - use only well-established knowledge and say so)'}\n\n"
        "Write markdown with sections: Core Concepts, Key Definitions (glossary), Prerequisites, "
        "Step-by-step Explanation, Real-world Case Studies (who used it, for what, what result), "
        "Worked Examples (with correct, runnable code and its output if the topic is technical), "
        "Common Mistakes & Misconceptions, Sources (only URLs above)." + _fb(feedback), temperature=0.3)
    return "# HISTORY NOTES\n" + s["history"] + "\n\n# CONCEPT NOTES\n" + s["concepts"]


# 2. OUTLINE ---------------------------------------------------------------
def outline_agent(s, feedback=None, log=print):
    log("Outline: learning-friendly outline draft ho rahi hai...")
    return chat(
        "You are an instructional designer. You design outlines that make learning easy: simple to hard, "
        "one idea per chapter, with clear outcomes and a story arc (problem -> idea -> limits -> better ideas).",
        f"{_ctx(s)}\nHISTORY NOTES:\n{s['history'][:3500]}\n\nCONCEPT NOTES:\n{s['concepts'][:4500]}\n\n"
        "Create an outline in markdown with EXACTLY this format:\n"
        "TITLE: <catchy title>\nOUTCOMES:\n- <3-5 measurable learning outcomes>\n"
        "Then 6 to 8 chapters, each starting with a line '## Chapter N: <title>' followed by bullets: "
        "Goal, Key points, Real example to use (concrete, from the notes), Mini activity.\n"
        "Required chapters in this order: Chapter 1 'Why this matters' (hook); Chapter 2 'History: Origin and "
        "Evolution' (the problem, who created it and when, why); then concept chapters going simple to hard; "
        "then 'Limitations and Modern Alternatives' (what the original approach could not do, and the better "
        "approaches that came after); last chapter 'Recap and Practice'." + _fb(feedback), temperature=0.4)


def _chapters(outline):
    return [p.strip() for p in re.split(r"(?m)^##\s+", outline)[1:] if p.strip()]


def get_title(outline, topic):
    m = re.search(r"(?im)^TITLE:\s*(.+)$", outline)
    return m.group(1).strip(" *#") if m else topic.title()


def _is_history(title):
    return any(w in title.lower() for w in ("histor", "origin", "evolution", "limitations", "alternatives"))


# 3. STORYTELLER -----------------------------------------------------------
def story_agent(s, feedback=None, log=print):
    chapters = _chapters(s["outline"]) or [s["outline"]]
    out, prev = [], "(this is the first chapter)"
    for i, ch in enumerate(chapters, 1):
        title = ch.splitlines()[0].strip(" *#")
        log(f"Storyteller: chapter {i}/{len(chapters)} - {title[:50]}")
        hist = _is_history(title)
        notes = (f"HISTORY NOTES:\n{s['history'][:6500]}\n\nCONCEPT NOTES:\n{s['concepts'][:2500]}" if hist
                 else f"CONCEPT NOTES:\n{s['concepts'][:6500]}\n\nHISTORY NOTES (for context):\n{s['history'][:1500]}")
        style = ("Tell it as a timeline story: the problem people faced -> who tried what, and when -> the "
                 "breakthrough -> its limitations -> what came next. Use names and years ONLY from the history notes; "
                 "if not documented, say so honestly. " if hist else
                 "Teach with REAL, concrete examples: real tools, real datasets, real companies, real numbers from "
                 "the notes, and short correct runnable code with its output where relevant. No vague generic examples. ")
        text = chat(
            "You are a master educator and storyteller who teaches like a great documentary: real events, real "
            "people, real cases, technically accurate. Never invent facts, names, dates or numbers that are not in "
            "the notes. " + LANG[s["language"]],
            f"{_ctx(s)}\nFULL OUTLINE:\n{s['outline'][:3500]}\n\n{notes}\n\n"
            f"STORY SO FAR (last chapter summary): {prev}\n\n"
            f"Now write ONLY this chapter in full:\n{ch}\n\n{style}\n"
            "Rules: 450-700 words. Open with a short real scenario or question, then explain step by step. "
            "Use '## ' for section headings (do NOT write the chapter title, I add it). Use '- ' bullets, short "
            "markdown tables when comparing things, and callouts on their own line like "
            "'> Key Takeaway: ...', '> Tip: ...', '> Common Mistake: ...'. Code in ``` blocks only if the topic "
            "needs code. Plain ASCII only (no arrows or special symbols)." + _fb(feedback), temperature=0.5)
        text = re.sub(r"(?m)^#\s+.*\n", "", text)
        out.append(f"# {title}\n\n{text}")
        prev = " ".join(text.split()[:60])
    return "\n\n".join(out)


# 4. DESIGNER (PDF) --------------------------------------------------------
def design_agent(s, feedback=None, log=print):
    log("Designer: theme choose karke PDF bana raha hoon...")
    d = parse_json(chat(
        "You are a document designer. Reply ONLY with JSON: "
        "{\"subtitle\": \"<max 12 words>\", \"theme\": \"ocean|forest|sunset|royal|slate\", "
        "\"density\": \"comfortable|compact\"}.",
        f"{_ctx(s)}Title: {s['title']}\nPick a professional theme suited to the topic. "
        "Use 'compact' only if the document is too long (many pages)." + _fb(feedback),
        json_mode=True, temperature=0.3)) or {}
    theme = d.get("theme") if d.get("theme") in THEMES else "ocean"
    density = d.get("density") if d.get("density") in ("comfortable", "compact") else "comfortable"
    path = os.path.join(_out_dir(s), f"{slug(s['topic'])}.pdf")
    build_pdf(s["story"], path, s["title"], str(d.get("subtitle", "")), theme, density,
              author=s.get("mentor", ""), audience=s["audience"])
    from pypdf import PdfReader
    return {"theme": theme, "density": density, "subtitle": str(d.get("subtitle", "")), "path": path,
            "pages": len(PdfReader(path).pages)}


# 5. SLIDES (PPT) ----------------------------------------------------------
def _outcomes(outline):
    m = re.search(r"(?is)OUTCOMES:?\s*(.*?)(?=^##\s|\Z)", outline, re.M)
    return [re.sub(r"^[-*\d.)\s]+", "", l).strip() for l in (m.group(1).splitlines() if m else [])
            if l.strip().startswith(("-", "*", "1", "2", "3", "4", "5"))][:5]


def slides_agent(s, feedback=None, log=print):
    chapters = re.split(r"(?m)^# ", s["story"])[1:]
    slides = [{"kind": "title", "title": s["title"], "subtitle": s["design"]["subtitle"] or s["topic"]}]
    oc = _outcomes(s["outline"])
    if oc:
        slides.append({"kind": "list", "title": "What you will learn", "items": oc})
    titles = [c.splitlines()[0].strip() for c in chapters]
    slides.append({"kind": "list", "title": "Roadmap", "items": titles[:6]})
    for i, blk in enumerate(chapters, 1):
        title = blk.splitlines()[0].strip()
        body = blk[len(blk.splitlines()[0]):][:5500]
        log(f"Slides: chapter {i}/{len(chapters)} - {title[:50]}")
        d = parse_json(chat(
            "You turn teaching text into crisp presentation slides for a mentor. " + LANG[s["language"]] +
            " Reply ONLY with JSON: {\"bullets\": [3 to 5 bullets, max 14 words each], "
            "\"example\": \"one concrete real example from the text, max 35 words, or empty\", "
            "\"takeaway\": \"one sentence\", \"notes\": \"speaker notes: 4-5 sentences the mentor can say aloud\"}.",
            f"Chapter: {title}\n\n{body}" + _fb(feedback), json_mode=True, temperature=0.3)) or {}
        bullets = [str(b) for b in d.get("bullets", []) if str(b).strip()] if isinstance(d.get("bullets"), list) else []
        if not bullets:
            bullets = [re.sub(r"^[-*]\s+", "", l).strip() for l in body.splitlines() if l.strip().startswith("- ")][:5]
        slides.append({"kind": "list", "title": title, "items": bullets[:5] or [title], "notes": str(d.get("notes", ""))})
        if str(d.get("example", "")).strip():
            slides.append({"kind": "example", "title": title, "example": str(d["example"]),
                           "takeaway": str(d.get("takeaway", "")), "notes": str(d.get("notes", ""))})
    slides.append({"kind": "closing", "title": "Questions?"})
    path = os.path.join(_out_dir(s), f"{slug(s['topic'])}.pptx")
    build_pptx(slides, path, s["design"]["theme"], s["title"], s.get("mentor", ""), s["audience"])
    return {"path": path, "count": len(slides), "chapters": len(chapters), "specs": slides}


# 6. REVIEWER --------------------------------------------------------------
def auto_checks(s):
    """Python se pakke checks - LLM par bharosa kam karte hain."""
    issues = {"research": [], "outline": [], "story": [], "design": [], "slides": []}
    if len(s["history"].split()) < 150:
        issues["research"].append("History notes are too thin (<150 words). Cover origin, creator, problem, "
                                  "limitations and what came next.")
    if len(s["concepts"].split()) < 250:
        issues["research"].append("Concept notes are too thin (<250 words). Add concrete case studies and examples.")
    ch_out, ch_story = _chapters(s["outline"]), re.findall(r"(?m)^# ", s["story"])
    if len(ch_out) < 5:
        issues["outline"].append("Outline needs at least 6 chapters in '## Chapter N: title' format.")
    if "OUTCOMES" not in s["outline"].upper():
        issues["outline"].append("Outline is missing the OUTCOMES section.")
    if not any("histor" in c.splitlines()[0].lower() or "origin" in c.splitlines()[0].lower() for c in ch_out):
        issues["outline"].append("Outline must include a 'History: Origin and Evolution' chapter.")
    for blk in re.split(r"(?m)^# ", s["story"])[1:]:
        t = blk.splitlines()[0]
        if len(blk.split()) < 250:
            issues["story"].append(f"Chapter '{t[:40]}' is too short; add real examples and explanation.")
        if "> " not in blk:
            issues["story"].append(f"Chapter '{t[:40]}' has no callout (Key Takeaway/Tip/Common Mistake).")
        if "histor" in t.lower() and YEAR.search(s["history"]) and len(set(YEAR.findall(blk))) < 2:
            issues["story"].append("History chapter lacks dated milestones; use years/names from the history notes.")
    if ch_out and len(ch_story) != len(ch_out):
        issues["story"].append("Number of story chapters does not match the outline.")
    if s["design"]["pages"] > 35:
        issues["design"].append("PDF is too long; use compact density.")
    sl = s["slides"]
    if sl["count"] < sl["chapters"] + 3:
        issues["slides"].append("Too few slides for the number of chapters.")
    if any(len(str(b).split()) > 25 for sp in sl["specs"] if sp["kind"] == "list" for b in sp["items"]):
        issues["slides"].append("Some slide bullets are too long; keep them under 14 words.")
    return issues


def review_agent(s, log=print):
    log("Reviewer: poora content recheck kar raha hoon...")
    story = s["story"]
    story_view = story if len(story) < 7000 else story[:3500] + "\n...[middle trimmed]...\n" + story[-3000:]
    auto = auto_checks(s)
    v = parse_json(chat(
        "You are a strict senior editor reviewing student learning material. Judge each stage honestly. "
        "Reply ONLY with JSON: {\"research\": {\"pass\": true, \"feedback\": \"\"}, \"outline\": {...}, "
        "\"story\": {...}, \"design\": {...}}. Set pass=false only for real flaws (factual errors, missing key "
        "concepts, missing history, generic or unrealistic examples, poor learning flow, confusing story). "
        "Feedback must be specific and actionable.",
        f"{_ctx(s)}\nHISTORY NOTES (trimmed):\n{s['history'][:2000]}\n\nCONCEPT NOTES (trimmed):\n{s['concepts'][:2000]}\n\n"
        f"OUTLINE:\n{s['outline'][:3000]}\n\nSTORY:\n{story_view}\n\n"
        f"DESIGN REPORT: theme={s['design']['theme']}, density={s['design']['density']}, pages={s['design']['pages']}.\n"
        f"AUTOMATIC CHECK ISSUES: {auto}\n\n"
        "Check: does the story cover who created the idea, the problem it solved, its limitations and the better "
        "approaches that followed? Are examples concrete and real (named tools/datasets/companies/numbers), not "
        "generic? Is the outline logical, the story faithful to notes, facts consistent?",
        json_mode=True, temperature=0.2)) or {}
    verdict = {}
    for k in ("research", "outline", "story", "design", "slides"):
        item = v.get(k) if isinstance(v.get(k), dict) else {}
        ok, fb = bool(item.get("pass", True)), str(item.get("feedback", "")).strip()
        if auto[k]:
            ok, fb = False, (fb + "\n" + "\n".join(auto[k])).strip()
        verdict[k] = {"pass": ok, "feedback": fb}
    return verdict
