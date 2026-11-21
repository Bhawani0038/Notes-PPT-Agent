"""Markdown-jaisa content ko professional PDF mein badalta hai (reportlab, free)."""
import re
import textwrap
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents

THEMES = {
    "ocean":  {"primary": "#0B3C5D", "accent": "#1D8FE1", "light": "#EAF4FB"},
    "forest": {"primary": "#1B4332", "accent": "#2D9D6B", "light": "#E9F5EE"},
    "sunset": {"primary": "#7A2E12", "accent": "#E8743B", "light": "#FDF0E8"},
    "royal":  {"primary": "#2E1A6B", "accent": "#7B5CE0", "light": "#F0ECFB"},
    "slate":  {"primary": "#27323F", "accent": "#4F8A8B", "light": "#EEF2F4"},
}
W, H = A4
SPECIAL = ("```", "#", ">", "|")


def clean(t):
    """Helvetica ke unsupported characters hatao (warna black boxes aate hain)."""
    for a, b in {"→": "->", "←": "<-", "≈": "~", "≥": ">=", "≤": "<=", "✓": "", "✔": "", "−": "-",
                 "\u00a0": " ", "\u200b": ""}.items():
        t = t.replace(a, b)
    return t.encode("cp1252", "ignore").decode("cp1252")


def _balanced(s):
    stack = []
    for m in re.finditer(r"<(/?)(b|i|font)\b[^>]*>", s):
        if m.group(1):
            if not stack or stack.pop() != m.group(2):
                return False
        else:
            stack.append(m.group(2))
    return not stack


def inline(t):
    plain = escape(clean(t))
    s = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", plain)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", s)
    if _balanced(s):
        return s
    return re.sub(r"\*+|`", "", plain)   # tags gadbad hon to plain text, crash nahi


def make_styles(th, density):
    base = 10 if density == "comfortable" else 9
    lead = base * 1.5
    P = colors.HexColor(th["primary"])
    A = colors.HexColor(th["accent"])
    return {
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=base, leading=lead, spaceAfter=6,
                               textColor=colors.HexColor("#222222"), alignment=TA_LEFT),
        "H1": ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=P, spaceAfter=10),
        "H2": ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=A,
                             spaceBefore=10, spaceAfter=5),
        "H3": ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=P,
                             spaceBefore=6, spaceAfter=3),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=base, leading=lead, leftIndent=14,
                                 bulletIndent=3, spaceAfter=3, textColor=colors.HexColor("#222222")),
        "call": ParagraphStyle("call", fontName="Helvetica", fontSize=base, leading=lead,
                               textColor=colors.HexColor("#1A1A1A")),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=base - 1, leading=(base - 1) * 1.35),
        "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=base - 1, leading=(base - 1) * 1.35,
                                textColor=colors.white),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8, leading=10.5),
        "toc1": ParagraphStyle("toc1", fontName="Helvetica", fontSize=11, leading=20, textColor=P),
    }


def _is_special(ln):
    s = ln.strip()
    return (not s or s.startswith(SPECIAL) or re.match(r"^([-*•]|\d+[.)])\s+", s) is not None)


def parse(md):
    lines, blocks, i = md.splitlines(), [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
        elif s.startswith("```"):
            j, buf = i + 1, []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                buf.append(lines[j]); j += 1
            blocks.append(("code", "\n".join(buf))); i = j + 1
        elif re.match(r"^#{1,3}\s+", s):
            lvl = len(s) - len(s.lstrip("#"))
            blocks.append((f"h{lvl}", s[lvl:].strip())); i += 1
        elif s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip()); i += 1
            blocks.append(("callout", " ".join(buf)))
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in row if c):
                    rows.append(row)
                i += 1
            blocks.append(("table", rows))
        elif re.match(r"^([-*•])\s+", s):
            blocks.append(("bullet", re.sub(r"^([-*•])\s+", "", s))); i += 1
        elif re.match(r"^\d+[.)]\s+", s):
            n = re.match(r"^(\d+)[.)]\s+", s).group(1)
            blocks.append(("num", (n, re.sub(r"^\d+[.)]\s+", "", s)))); i += 1
        else:
            buf = []
            while i < len(lines) and not _is_special(lines[i]):
                buf.append(lines[i].strip()); i += 1
            if not buf:  # safety
                buf = [s]; i += 1
            blocks.append(("p", " ".join(buf)))
    return blocks


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "H1":
            self.notify("TOCEntry", (0, f.getPlainText(), self.page))


def build_pdf(md, path, title, subtitle="", theme="ocean", density="comfortable",
              author="", audience="", short_title=""):
    th = THEMES.get(theme, THEMES["ocean"])
    st = make_styles(th, density)
    P, A, L = (colors.HexColor(th[k]) for k in ("primary", "accent", "light"))
    cw = W - 40 * mm

    def cover(c, d):
        c.saveState()
        c.setFillColor(P); c.rect(0, H * 0.38, W, H * 0.62, stroke=0, fill=1)
        c.setFillColor(A); c.rect(0, H * 0.38 - 5, W, 5, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 34)
        y = H * 0.38 + H * 0.62 * 0.62
        for ln in simpleSplit(clean(title), "Helvetica-Bold", 34, W - 50 * mm):
            c.drawString(25 * mm, y, ln); y -= 42
        c.setFont("Helvetica", 15); c.setFillColor(colors.HexColor("#DDE9F2"))
        for ln in simpleSplit(clean(subtitle), "Helvetica", 15, W - 50 * mm):
            c.drawString(25 * mm, y - 6, ln); y -= 20
        c.setFillColor(P); c.setFont("Helvetica-Bold", 12)
        yy = H * 0.38 - 40
        if audience:
            c.drawString(25 * mm, yy, clean("For: " + audience)); yy -= 18
        if author:
            c.drawString(25 * mm, yy, clean("Mentor: " + author)); yy -= 18
        c.setFont("Helvetica", 10); c.setFillColor(colors.grey)
        c.drawString(25 * mm, 20 * mm, date.today().strftime("%d %B %Y"))
        c.restoreState()

    def body(c, d):
        c.saveState()
        c.setStrokeColor(A); c.setLineWidth(1.2); c.line(20 * mm, H - 15 * mm, W - 20 * mm, H - 15 * mm)
        c.setFont("Helvetica", 8.5); c.setFillColor(colors.grey)
        c.drawString(20 * mm, H - 12 * mm, clean(short_title or title)[:70])
        c.drawRightString(W - 20 * mm, 12 * mm, f"Page {d.page}")
        c.setStrokeColor(colors.lightgrey); c.setLineWidth(0.5); c.line(20 * mm, 17 * mm, W - 20 * mm, 17 * mm)
        c.restoreState()

    doc = Doc(path, pagesize=A4, title=clean(title), author=clean(author),
              leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm, bottomMargin=22 * mm)
    doc.addPageTemplates([
        PageTemplate("cover", [Frame(20 * mm, 20 * mm, cw, 20 * mm, id="c0")], onPage=cover),
        PageTemplate("body", [Frame(20 * mm, 20 * mm, cw, H - 42 * mm, id="b0")], onPage=body),
    ])

    story = [NextPageTemplate("body"), PageBreak(), Paragraph("Contents", ParagraphStyle("TocTitle", parent=st["H1"]))]
    toc = TableOfContents()
    toc.levelStyles = [st["toc1"]]
    story += [toc]

    first_h1 = True
    for kind, val in parse(md):
        if kind == "h1":
            story.append(PageBreak()); first_h1 = False
            story.append(Paragraph(inline(val), st["H1"]))
            story.append(Table([[""]], colWidths=[40 * mm], rowHeights=[3],
                               style=[("BACKGROUND", (0, 0), (-1, -1), A)], hAlign="LEFT"))
            story.append(Spacer(1, 8))
        elif kind in ("h2", "h3"):
            story.append(Paragraph(inline(val), st["H2" if kind == "h2" else "H3"]))
        elif kind == "p":
            story.append(Paragraph(inline(val), st["body"]))
        elif kind == "bullet":
            story.append(Paragraph(inline(val), st["bullet"], bulletText="\u2022"))
        elif kind == "num":
            story.append(Paragraph(inline(val[1]), st["bullet"], bulletText=val[0] + "."))
        elif kind == "callout":
            m = re.match(r"^\**([A-Za-z ]{3,24}):\**\s*(.*)$", val)
            txt = f"<b>{escape(clean(m.group(1)))}:</b> {inline(m.group(2))}" if m else inline(val)
            t = Table([[Paragraph(txt, st["call"])]], colWidths=[cw])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), L), ("LINEBEFORE", (0, 0), (0, -1), 3, A),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                   ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
            story += [Spacer(1, 3), KeepTogether([t]), Spacer(1, 7)]
        elif kind == "table" and val:
            n = max(len(r) for r in val)
            data = [[Paragraph(inline(c), st["cellh" if ri == 0 else "cell"]) for c in r + [""] * (n - len(r))]
                    for ri, r in enumerate(val)]
            t = Table(data, colWidths=[cw / n] * n, repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), P),
                                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, L]),
                                   ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            story += [Spacer(1, 3), t, Spacer(1, 8)]
        elif kind == "code":
            wrapped = "\n".join(textwrap.fill(clean(l), 88, subsequent_indent="    ") if len(l) > 88 else clean(l)
                                for l in val.splitlines())
            t = Table([[Preformatted(wrapped, st["code"])]], colWidths=[cw])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F4F4")),
                                   ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            story += [Spacer(1, 3), t, Spacer(1, 8)]
    doc.multiBuild(story)
    return path
