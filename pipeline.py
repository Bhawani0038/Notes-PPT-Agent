import json
import os

from agents import (research_agent, outline_agent, story_agent, design_agent, slides_agent, review_agent,
                    get_title, slug)
from config import MAX_REVIEW_LOOPS, OUTPUT_DIR

STAGES = ["research", "outline", "story", "design", "slides"]


def run_pipeline(topic, audience="College students", level="Beginner", language="English",
                 mentor="", out_dir=None, log=print):
    s = {"topic": topic, "audience": audience, "level": level, "language": language, "mentor": mentor,
         "out_dir": out_dir or OUTPUT_DIR}
    feedback, start, history = {}, 0, []
    for loop in range(MAX_REVIEW_LOOPS + 1):
        for stage in STAGES[start:]:
            fb = feedback.get(stage)
            if stage == "research":
                s["research"] = research_agent(s, fb, log)
            elif stage == "outline":
                s["outline"] = outline_agent(s, fb, log)
                s["title"] = get_title(s["outline"], topic)
            elif stage == "story":
                s["story"] = story_agent(s, fb, log)
            elif stage == "design":
                s["design"] = design_agent(s, fb, log)
            else:
                s["slides"] = slides_agent(s, fb, log)
        verdict = review_agent(s, log)
        history.append(verdict)
        failed = [k for k in STAGES if not verdict[k]["pass"]]
        if not failed:
            log("Reviewer: sab theek hai, PDF + PPT ready.")
            break
        if loop == MAX_REVIEW_LOOPS:
            log("Reviewer: max loops ho gaye, best available version save kar raha hoon.")
            break
        log(f"Reviewer: flaws mile in {failed}; wapas bhej raha hoon (round {loop + 1}).")
        feedback = {k: verdict[k]["feedback"] for k in failed}
        start = STAGES.index(failed[0])
    d = s["out_dir"]
    base = os.path.join(d, slug(topic))
    for name in ("research", "outline", "story"):
        open(f"{base}_{name}.md", "w", encoding="utf-8").write(s[name])
    json.dump(history, open(f"{base}_review.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    s["review_history"] = history
    s["files"] = {"pdf": s["design"]["path"], "pptx": s["slides"]["path"],
                  "research": f"{base}_research.md", "outline": f"{base}_outline.md",
                  "story": f"{base}_story.md", "review": f"{base}_review.json"}
    return s
