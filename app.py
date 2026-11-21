import os
import time

import streamlit as st

from batch import BatchJob, parse_topics

st.set_page_config(page_title="Content Agents", page_icon="📘", layout="wide")
st.title("📘 Playlist se PDF + PPT - Multi-Agent Content Maker")
job = st.session_state.get("job")
running = job is not None and job.state == "running"

topics_text = st.text_area("Topics ki list (har line par ek topic; numbering ho to bhi chalega)", height=220,
                           disabled=running, placeholder="Python Functions\nLists and Tuples\nK-Means Clustering")
c1, c2, c3, c4 = st.columns(4)
audience = c1.text_input("Audience", "College students", disabled=running)
level = c2.selectbox("Level", ["Beginner", "Intermediate", "Advanced"], disabled=running)
language = c3.selectbox("Language", ["English", "Hinglish"], disabled=running)
mentor = c4.text_input("Mentor name (cover par)", disabled=running)
name = st.text_input("Playlist / batch ka naam (isi naam ka folder banega)",
                     value=time.strftime("playlist_%Y%m%d"), disabled=running)
topics = parse_topics(topics_text)
b1, b2, _ = st.columns([1, 1, 3])
if b1.button(f"Start ({len(topics)} topics)", type="primary", disabled=running or not topics):
    job = BatchJob(topics, audience, level, language, mentor, name)
    job.start()
    st.session_state.job, st.session_state.was_running = job, True
    st.rerun()
if b2.button("Stop after current topic", disabled=not running):
    job.stop()

ICON = {"queued": "⏳", "running": "🔄", "done": "✅", "error": "❌"}


def panel():
    job = st.session_state.get("job")
    if not job:
        return
    if st.session_state.get("was_running") and job.state != "running":
        st.session_state.was_running = False
        st.rerun()
    items = job.items
    done = [i for i in items if i["status"] == "done"]
    st.progress(len(done) / len(items), text=f"{len(done)}/{len(items)} topics done  |  {job.state}")
    if job.current:
        st.info(f"Abhi chal raha hai: **{job.current['topic']}**")
    st.caption(f"📁 Saari files is folder mein save ho rahi hain: {os.path.abspath(job.root)}")
    if done:
        if st.button("Prepare ZIP of all finished topics", key="prep_all"):
            st.session_state.all_zip = (len(done), job.zip_all())
        z = st.session_state.get("all_zip")
        if z and z[0] == len(done):
            st.download_button(f"⬇ Download ALL finished ({z[0]} topics) - ZIP", z[1],
                               file_name=os.path.basename(job.root) + ".zip", key="dl_all")
    for idx, it in enumerate(items):
        cols = st.columns([4, 1, 1, 1])
        cols[0].write(f"{ICON.get(it['status'], '⏸')} **{idx + 1}. {it['topic']}**  `{it['status']}`"
                      + (f"  - {it['error']}" if it["error"] else ""))
        if it["status"] == "done":
            f = it["files"]
            cols[1].download_button("PDF", job.file_bytes(f["pdf"]), file_name=os.path.basename(f["pdf"]),
                                    key=f"pdf{idx}")
            cols[2].download_button("PPT", job.file_bytes(f["pptx"]), file_name=os.path.basename(f["pptx"]),
                                    key=f"ppt{idx}")
            zk = f"zip{idx}"
            if zk not in st.session_state:
                st.session_state[zk] = job.zip_item(it)
            cols[3].download_button("ZIP", st.session_state[zk], file_name=os.path.basename(it["dir"]) + ".zip",
                                    key=f"z{idx}")
    with st.expander("Live log", expanded=job.state == "running"):
        st.code("\n".join(list(job.logs)[-25:]) or "-")


st.fragment(run_every=3 if running else None)(panel)()
