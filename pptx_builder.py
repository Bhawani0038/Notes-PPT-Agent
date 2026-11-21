"""Slides spec ko professional .pptx mein badalta hai (python-pptx, free)."""
import re
from datetime import date

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from pdf_builder import THEMES


def _rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16))


def _plain(t):
    return re.sub(r"\*\*|`", "", str(t)).strip()


def _rect(sl, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE):
    r = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    r.fill.solid(); r.fill.fore_color.rgb = _rgb(color)
    r.line.fill.background(); r.shadow.inherit = False
    return r


def _text(sl, x, y, w, h, text, size=20, bold=False, color="#222222", align=PP_ALIGN.LEFT,
          anchor=MSO_ANCHOR.TOP):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = _plain(text)
    r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = _rgb(color); r.font.name = "Calibri"
    return tb


def _bullets(sl, x, y, w, h, items, size, color="#222222"):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = _plain(it)
        r.font.size = Pt(size); r.font.color.rgb = _rgb(color); r.font.name = "Calibri"
        p.space_after = Pt(12)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", "342900"); pPr.set("indent", "-342900")
        etree.SubElement(pPr, qn("a:buChar")).set("char", "\u2022")


def build_pptx(slides, path, theme, title, author="", audience=""):
    th = THEMES.get(theme, THEMES["ocean"])
    P, A, L = th["primary"], th["accent"], th["light"]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    def footer(sl, n):
        _rect(sl, 0, 7.12, 13.333, 0.02, "#D0D0D0")
        _text(sl, 0.7, 7.15, 9, 0.3, title[:80], 10, color="#888888")
        _text(sl, 11.6, 7.15, 1.1, 0.3, str(n), 10, color="#888888", align=PP_ALIGN.RIGHT)

    def heading(sl, text):
        _rect(sl, 0, 0, 0.25, 7.5, A)
        _text(sl, 0.7, 0.4, 12, 1.0, text, 32, True, P, anchor=MSO_ANCHOR.MIDDLE)
        _rect(sl, 0.7, 1.45, 1.6, 0.06, A)

    for n, sp in enumerate(slides, 1):
        sl = prs.slides.add_slide(blank)
        k = sp["kind"]
        if k in ("title", "closing"):
            _rect(sl, 0, 0, 13.333, 7.5, P)
            _rect(sl, 0.9, 3.55, 2.2, 0.08, A)
            _text(sl, 0.9, 1.3, 11.5, 2.2, sp["title"], 46 if k == "title" else 54, True, "#FFFFFF",
                  anchor=MSO_ANCHOR.BOTTOM)
            if sp.get("subtitle"):
                _text(sl, 0.9, 3.85, 11.5, 1.0, sp["subtitle"], 22, color="#DDE9F2")
            meta = "   |   ".join(x for x in [("Mentor: " + author) if author and k == "title" else "",
                                               ("For: " + audience) if audience and k == "title" else "",
                                               date.today().strftime("%d %B %Y") if k == "title" else ""] if x)
            if meta:
                _text(sl, 0.9, 6.3, 11.5, 0.5, meta, 14, color="#BBD0E0")
        elif k == "list":
            heading(sl, sp["title"])
            items = [_plain(i) for i in sp["items"]][:6]
            total = sum(len(i) for i in items)
            size = 26 if total < 260 else 22 if total < 420 else 18
            _bullets(sl, 0.9, 1.8, 11.6, 5.0, items, size)
            footer(sl, n)
        elif k == "example":
            heading(sl, sp["title"])
            _text(sl, 0.9, 1.7, 8, 0.4, "REAL-WORLD EXAMPLE", 13, True, A)
            box = _rect(sl, 0.9, 2.1, 11.5, 2.9, L, MSO_SHAPE.ROUNDED_RECTANGLE)
            box.adjustments[0] = 0.05
            ex = _plain(sp.get("example", ""))
            _text(sl, 1.2, 2.3, 10.9, 2.5, ex, 24 if len(ex) < 200 else 20, color="#222222",
                  anchor=MSO_ANCHOR.MIDDLE)
            if sp.get("takeaway"):
                _rect(sl, 0.9, 5.4, 11.5, 1.2, A, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.15
                _text(sl, 1.2, 5.4, 10.9, 1.2, "Key takeaway: " + _plain(sp["takeaway"]), 20, True, "#FFFFFF",
                      anchor=MSO_ANCHOR.MIDDLE)
            footer(sl, n)
        if sp.get("notes"):
            sl.notes_slide.notes_text_frame.text = _plain(sp["notes"])
    prs.save(path)
    return path
