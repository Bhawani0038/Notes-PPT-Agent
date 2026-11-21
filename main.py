import argparse
import time

from batch import BatchJob, parse_topics

ap = argparse.ArgumentParser(description="Topics ki list se PDF + PPT - multi-agent, free local models")
ap.add_argument("topic", nargs="?", help="ek topic (ya --file use karo)")
ap.add_argument("--file", help="text file, har line par ek topic")
ap.add_argument("--audience", default="College students")
ap.add_argument("--level", default="Beginner")
ap.add_argument("--language", default="English", choices=["English", "Hinglish"])
ap.add_argument("--mentor", default="")
ap.add_argument("--name", default=time.strftime("playlist_%Y%m%d"))
a = ap.parse_args()
text = open(a.file, encoding="utf-8").read() if a.file else (a.topic or "")
topics = parse_topics(text)
if not topics:
    ap.error("topic ya --file do")
job = BatchJob(topics, a.audience, a.level, a.language, a.mentor, a.name, echo=True)
job.run()
print("\nSaved in:", job.root)
