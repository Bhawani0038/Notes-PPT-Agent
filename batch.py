"""Playlist mode: topics ki list ek ke baad ek, aaram se, background thread mein."""
import io
import json
import os
import re
import threading
import time
import zipfile
from collections import deque

from agents import slug
from config import OUTPUT_DIR
from pipeline import run_pipeline


def parse_topics(text):
    out, seen = [], set()
    for ln in text.splitlines():
        t = re.sub(r"^\s*(\d+[.)]|[-*\u2022])\s*", "", ln).strip()
        if not t or t.startswith("#") or t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(t)
    return out


class BatchJob:
    def __init__(self, topics, audience, level, language, mentor, name, echo=False):
        self.cfg = dict(audience=audience, level=level, language=language, mentor=mentor)
        self.root = os.path.join(OUTPUT_DIR, re.sub(r"[^\w\-]+", "_", name).strip("_") or "batch")
        self.items = [{"topic": t, "status": "queued", "error": "", "files": {},
                       "dir": os.path.join(self.root, f"{i:02d}_{slug(t)}")} for i, t in enumerate(topics, 1)]
        self.logs, self.state, self.current, self.echo = deque(maxlen=300), "idle", None, echo
        self._stop, self._cache = False, {}

    def log(self, m):
        line = time.strftime("%H:%M:%S ") + m
        self.logs.append(line)
        if self.echo:
            print(line, flush=True)

    def start(self):
        self.state = "running"
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self._stop = True
        self.log("Stop requested: current topic poora hone ke baad ruk jaunga.")

    def run(self):
        self.state = "running"
        for it in self.items:
            if self._stop:
                break
            marker = os.path.join(it["dir"], "done.json")
            if os.path.exists(marker):                      # resume: pehle ban chuke topics skip
                it["files"], it["status"] = json.load(open(marker, encoding="utf-8")), "done"
                self.log(f"Skip (already done): {it['topic']}")
                continue
            it["status"], self.current, t0 = "running", it, time.time()
            self.log(f"START: {it['topic']}")
            try:
                s = run_pipeline(it["topic"], out_dir=it["dir"],
                                 log=lambda m, t=it["topic"]: self.log(f"[{t}] {m}"), **self.cfg)
                it["files"], it["status"] = s["files"], "done"
                json.dump(it["files"], open(marker, "w", encoding="utf-8"))
                self.log(f"DONE: {it['topic']} ({int(time.time() - t0)//60} min)")
            except Exception as e:                           # ek topic fail ho to baaki chalte rahein
                it["status"], it["error"] = "error", f"{type(e).__name__}: {e}"
                self.log(f"ERROR: {it['topic']} -> {it['error']}")
        self.current = None
        self.state = "stopped" if self._stop else "finished"
        self.log(f"Batch {self.state}.")

    # ---- downloads ----
    def file_bytes(self, path):
        if path not in self._cache:
            self._cache[path] = open(path, "rb").read()
        return self._cache[path]

    def _zip(self, folders):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in folders:
                for r, _, fs in os.walk(f):
                    for n in fs:
                        if n != "done.json":
                            p = os.path.join(r, n)
                            z.write(p, os.path.relpath(p, os.path.dirname(self.root)))
        return buf.getvalue()

    def zip_item(self, it):
        return self._zip([it["dir"]])

    def zip_all(self):
        return self._zip([i["dir"] for i in self.items if i["status"] == "done"])
