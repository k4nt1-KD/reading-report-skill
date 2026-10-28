# -*- coding: utf-8 -*-
"""Reusable python-pptx building blocks for literature-reading decks.

The module encodes the layout conventions that survived real review rounds
(see SKILL.md §5). Everything is plain python-pptx, so the result stays an
editable, native PPTX — no images of text except the paper crops themselves.

Typical use::

    from deck_kit import Deck, bullets, callout, pic_fit, eq_rows

    d = Deck("last-approved-deck.pptx")     # inherits master/layouts
    d.section("2. Problem Description")
    sl = d.slide("目标函数与约束")
    bullets(sl, 0.62, 1.4, 5.2, 3.0, ["…", "…"])
    eq_rows(sl, [(1, "目标函数", "最小化 makespan"), (2, "需求", "…")])
    d.save("output/deck.pptx")

Units are inches throughout; the slide is 10 x 5.625 in (16:9).
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

# ---------------------------------------------------------------- palette ---
NAVY = RGBColor(0x1F, 0x49, 0x7D)
BLUE = RGBColor(0x4F, 0x81, 0xBD)
PALE = RGBColor(0xEB, 0xF2, 0xF9)
PALE2 = RGBColor(0xF7, 0xF9, 0xFC)
LIGHT = RGBColor(0xD4, 0xDB, 0xE2)
DARK = RGBColor(0x2D, 0x37, 0x41)
MID = RGBColor(0x5F, 0x69, 0x73)
RED = RGBColor(0xC0, 0x50, 0x4D)
GREEN = RGBColor(0x4F, 0x7B, 0x5B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

SERIF = "Times New Roman"      # latin
SONG = "宋体"                   # CJK body
HEI = "Microsoft YaHei"        # CJK label / header

LEFT, RIGHT = 0.62, 9.38       # content box
TOP = 1.40



def _ea(run, family: str = SONG) -> None:
    """Latin = Times, East-Asian = family; keeps 中文 from falling back to Calibri."""
    run.font.name = SERIF
    rpr = run._r.get_or_add_rPr()
    latin = rpr.find(qn("a:latin"))
    if latin is None:
        latin = OxmlElement("a:latin")
        rpr.append(latin)
    latin.set("typeface", SERIF)
    ea = rpr.find(qn("a:ea"))
    if ea is None:
        ea = OxmlElement("a:ea")
        rpr.append(ea)
    ea.set("typeface", family)
    rpr.set("lang", "zh-CN")


def emit(p, markup: str, size: float = 11.0, color=DARK,
         bold: bool = False, italic: bool = False) -> None:
    """Inline markup: ``**bold**``, ``$math italic$``, ``^{sup}``, ``_{sub}``."""
    bold_on, italic_on = bold, italic
    buf = ""
    i = 0

    def flush(b, it, sup=False, sub=False):
        nonlocal buf
        if not buf:
            return
        r = p.add_run()
        r.text = buf
        r.font.size = Pt(size)
        r.font.bold = b
        r.font.italic = it
        r.font.color.rgb = color
        _ea(r)
        if sup:
            r.font._rPr.set("baseline", "30000")
        if sub:
            r.font._rPr.set("baseline", "-25000")
        buf = ""

    while i < len(markup):
        if markup.startswith("**", i):
            flush(bold_on, italic_on)
            bold_on = not bold_on
            i += 2
        elif markup[i] == "$":
            flush(bold_on, italic_on)
            italic_on = not italic_on
            i += 1
        elif markup.startswith("^{", i) or markup.startswith("_{", i):
            flush(bold_on, italic_on)
            depth, j = 1, i + 2
            while j < len(markup) and depth:
                depth += {"{": 1, "}": -1}.get(markup[j], 0)
                j += 1
            buf = markup[i + 2:j - 1].replace("$", "")
            flush(False, True, sup=markup[i] == "^", sub=markup[i] == "_")
            i = j
        else:
            buf += markup[i]
            i += 1
    flush(bold_on, italic_on)


# ------------------------------------------------------------- primitives ---
def textbox(sl, x, y, w, h, anchor=MSO_ANCHOR.TOP, margins: float = 0.03):
    sh = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margins)
    tf.margin_top = tf.margin_bottom = Inches(margins * 0.7)
    return sh, tf


def paragraph(tf, first: bool, markup: str, size: float = 11.0, color=DARK,
              bold: bool = False, italic: bool = False, align=PP_ALIGN.LEFT,
              space_after: float = 3, line: float = 1.12, hang: float | None = None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(0)
    p.line_spacing = line
    if hang:  # hanging indent so wrapped lines align under the text, not the bullet
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(hang))))
        pPr.set("indent", str(int(-Inches(hang))))
    emit(p, markup, size=size, color=color, bold=bold, italic=italic)
    return p


def text(sl, x, y, w, h, markup, size: float = 11.0, color=DARK, bold: bool = False,
         italic: bool = False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line: float = 1.15):
    _, tf = textbox(sl, x, y, w, h, anchor=anchor)
    paragraph(tf, True, markup, size=size, color=color, bold=bold, italic=italic,
              align=align, line=line, space_after=0)


def bullets(sl, x, y, w, h, items, size: float = 11.0, color=DARK, gap: float = 6,
            line: float = 1.16) -> None:
    _, tf = textbox(sl, x, y, w, h)
    for i, item in enumerate(items):
        paragraph(tf, i == 0, "•  " + item, size=size, color=color,
                  space_after=gap, line=line, hang=0.235)


def _kill_style(shape) -> None:
    """Remove <p:style>: keeps theme effectRef (i.e. drop shadows) from coming back."""
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def rect(sl, x, y, w, h, fill=PALE, line=None, round_: bool = True, radius: float = 0.06):
    shp = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE,
                              Inches(x), Inches(y), Inches(w), Inches(h))
    _kill_style(shp)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.8)
    if round_:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    shp.shadow.inherit = False
    return shp


def hline(sl, x1, y, x2, color=LIGHT, width: float = 0.75):
    ln = sl.shapes.add_connector(1, Inches(x1), Inches(y), Inches(x2), Inches(y))
    ln.line.color.rgb = color
    ln.line.width = Pt(width)
    return ln


def pic_fit(sl, path, x, y, w, h, align: str = "center"):
    """Place an image inside a box without distorting it."""
    iw, ih = Image.open(path).size
    s = min(w / iw, h / ih)
    dw, dh = iw * s, ih * s
    dx = x + (w - dw) / 2 if align == "center" else x
    dy = y + (h - dh) / 2
    sl.shapes.add_picture(str(path), Inches(dx), Inches(dy), Inches(dw), Inches(dh))
    return dw, dh


def callout(sl, x, y, w, h, markup, size: float = 11.5, fill=PALE, color=NAVY):
    rect(sl, x, y, w, h, fill=fill, line=None, radius=0.12)
    text(sl, x + 0.14, y, w - 0.28, h, markup, size=size, color=color, anchor=MSO_ANCHOR.MIDDLE)


def card(sl, x, y, w, h, head: str, body: str, accent=NAVY, size: float = 9.6,
         head_size: float = 10.4) -> None:
    rect(sl, x, y, w, h, fill=PALE2, line=LIGHT, radius=0.05)
    bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.05), Inches(h))
    _kill_style(bar)
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent
    bar.line.fill.background()
    bar.shadow.inherit = False
    text(sl, x + 0.13, y + 0.07, w - 0.22, 0.26, head, size=head_size, color=accent, bold=True)
    if body:
        text(sl, x + 0.13, y + 0.36, w - 0.24, h - 0.42, body, size=size, line=1.14)


def tag(sl, x, y, w, label: str, fill=NAVY, size: float = 9.5, h: float = 0.30) -> None:
    rect(sl, x, y, w, h, fill=fill, line=None, radius=0.25)
    text(sl, x, y, w, h, label, size=size, color=WHITE, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def eq_rows(sl, rows, crops, top: float = 1.60, row_h: float = 0.645,
            eq_w: float = 3.45, size: float = 9.6) -> None:
    """One paper-cropped formula per row, explanation immediately to its right.

    ``rows``  = [(number, bold_lead, explanation), ...]
    ``crops`` = directory holding ``eq01.png`` ... (cropped with the number inside).
    """
    for i, (num, lead, body) in enumerate(rows):
        y = top + i * row_h
        if i:
            hline(sl, LEFT, y, RIGHT, LIGHT, 0.6)
        path = Path(crops) / f"eq{num:02d}.png"
        iw, ih = Image.open(path).size
        h = eq_w * ih / iw
        sl.shapes.add_picture(str(path), Inches(LEFT + 0.05),
                              Inches(y + (row_h - h) / 2), Inches(eq_w), Inches(h))
        _, tf = textbox(sl, LEFT + eq_w + 0.26, y + 0.03,
                        RIGHT - LEFT - eq_w - 0.26, row_h - 0.06,
                        anchor=MSO_ANCHOR.MIDDLE, margins=0.02)
        paragraph(tf, True, f"**{lead}**　{body}", size=size, line=1.12, space_after=0)


# ------------------------------------------------------------------ deck ---
class Deck:
    """A deck that inherits master/layouts from an already-approved deck."""

    def __init__(self, base: str | Path, layout: int = 1):
        self.prs = Presentation(str(base))
        for sid in list(self.prs.slides._sldIdLst):  # drop slides, keep masters
            self.prs.part.drop_rel(sid.rId)
            self.prs.slides._sldIdLst.remove(sid)
        self.layout = layout
        self.page = 0
        self.section_text = ""

    # -- slides ------------------------------------------------------------
    def section(self, title: str) -> None:
        """English section title used by every following slide header."""
        self.section_text = title

    def slide(self, title: str | None, section: str | None = None):
        sl = self.prs.slides.add_slide(self.prs.slide_layouts[self.layout])
        head = sl.placeholders[0]
        head.text = section if section is not None else self.section_text
        for p in head.text_frame.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            for r in p.runs:
                r.font.name = SERIF
                r.font.size = Pt(12.5)
                r.font.color.rgb = BLUE
                r.font.bold = False
                _ea(r, HEI)
        for idx in (10, 11):  # date / footer placeholders
            if idx in sl.placeholders:
                sl.placeholders[idx].text = ""

        if title:
            bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(LEFT), Inches(0.95),
                                      Inches(0.055), Inches(0.34))
            _kill_style(bar)
            bar.fill.solid()
            bar.fill.fore_color.rgb = NAVY
            bar.line.fill.background()
            bar.shadow.inherit = False
            text(sl, LEFT + 0.13, 0.90, RIGHT - LEFT - 0.13, 0.44, title,
                 size=17.5, color=NAVY, bold=True)

        self.page += 1
        # NOTE: python-pptx does not clone the slide-number placeholder (idx 12),
        # so the page number must be drawn as a normal text box.
        text(sl, 8.52, 5.16, 0.86, 0.26, str(self.page), size=9.5, color=MID,
             align=PP_ALIGN.RIGHT)
        return sl

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(path))
        return path

