#!/usr/bin/env python3
"""Typeset manuscript.md as a print-ready PDF.

Trim 5.5 x 8.5 in, DejaVu Serif body at 11/16, running heads (verso: title,
recto: chapter), page numbers in the footer, chapter starts on a fresh verso
page, front matter in roman numerals, and a real contents page built from the
page numbers the chapters actually land on (two PDF passes).

Requires fpdf2 and the DejaVu fonts:
    pip install --target /tmp/pylibs fpdf2
    PYTHONPATH=/tmp/pylibs python3 build_pdf.py
"""

import pathlib
import re
import sys

sys.path.insert(0, "/tmp/pylibs")
from fpdf import FPDF  # noqa: E402

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "manuscript.md"
OUT = ROOT / "the-birch-and-the-bell.pdf"

PAGE_W, PAGE_H = 5.5 * 25.4, 8.5 * 25.4  # mm
MARGIN_IN, MARGIN_TOP, MARGIN_BOT = 15.0, 18.0, 19.0
TEXT_W = PAGE_W - 2 * MARGIN_IN

BODY_PT = 10.2
BODY_LEAD = 5.05  # mm; 14.3pt at 10.2pt type (1.40 ratio)
FONT_DIR = pathlib.Path("/tmp/pylibs/matplotlib/mpl-data/fonts/ttf")

TITLE = "The Birch and the Bell"
RUNNING_TITLE = "THE BIRCH AND THE BELL"


def roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
            (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"),
            (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


# ---------------------------------------------------------------- markup


class Run:
    __slots__ = ("text", "italic", "bold")

    def __init__(self, text, italic=False, bold=False):
        self.text, self.italic, self.bold = text, italic, bold


def parse_runs(text: str):
    """Turn *italic* and **bold** spans into Run objects."""
    runs, pos = [], 0
    pattern = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*", re.S)
    for m in pattern.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos:m.start()]))
        if m.group(1) is not None:
            runs.append(Run(m.group(1), bold=True))
        else:
            runs.append(Run(m.group(2), italic=True))
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:]))
    return runs or [Run(text)]


class Book(FPDF):
    def __init__(self, toc_pages=None):
        super().__init__(orientation="P", unit="mm", format=(PAGE_W, PAGE_H))
        self.toc_pages = toc_pages or {}
        self.set_margins(MARGIN_IN, MARGIN_TOP, MARGIN_IN)
        self.set_auto_page_break(True, MARGIN_BOT)
        self.add_font("Serif", "", FONT_DIR / "DejaVuSerif.ttf")
        self.add_font("Serif", "I", FONT_DIR / "DejaVuSerif-Italic.ttf")
        self.add_font("Serif", "B", FONT_DIR / "DejaVuSerif-Bold.ttf")
        self.add_font("Serif", "BI", FONT_DIR / "DejaVuSerif-BoldItalic.ttf")
        self.chapter_running = ""
        self.first_body_page = None   # set before the first body page is added
        self._suppress_head = True
        self._opener_page = -1

    # -- page furniture ---------------------------------------------------
    def header(self):
        self.set_y(MARGIN_TOP)
        if self._suppress_head or self.first_body_page is None:
            return
        if self.page < self.first_body_page:
            return
        if self.page == self._opener_page:  # chapter openers carry no running head
            return
        self.set_font("Serif", "", 7.2)
        self.set_text_color(90, 90, 90)
        if self.page % 2 == 0:  # verso
            self.set_xy(MARGIN_IN, MARGIN_TOP - 9)
            self.cell(TEXT_W, 5, RUNNING_TITLE, align="L")
        else:  # recto
            text = self.chapter_running.upper()
            self.set_xy(MARGIN_IN, MARGIN_TOP - 9)
            self.cell(TEXT_W, 5, text, align="R")
        self.set_text_color(0, 0, 0)
        self.set_xy(MARGIN_IN, MARGIN_TOP)

    def footer(self):
        self.set_y(-16)
        if self.first_body_page is None or self.page < self.first_body_page:
            if self.page > 1:  # no folio on the title page
                self.set_font("Serif", "", 8)
                self.cell(0, 5, roman(self.page), align="C")
            return
        self.set_font("Serif", "", 8)
        self.cell(0, 5, str(self.page - self.first_body_page + 1), align="C")

    # -- typesetting ------------------------------------------------------
    def _break(self, runs, width, size):
        """Greedy word wrap across a run sequence -> list of lines of runs."""
        def style_of(r):
            return ("I" if r.italic else "") + ("B" if r.bold else "")

        lines, cur, cur_w = [], [], 0.0
        for r in runs:
            self.set_font("Serif", style_of(r), size)
            for token in re.split(r"(\s+)", r.text):
                if token == "":
                    continue
                w = self.get_string_width(token)
                if token.isspace():
                    if cur:
                        cur.append(Run(" ", r.italic, r.bold))
                        cur_w += self.get_string_width(" ")
                    continue
                if cur and cur_w + w > width:
                    while cur and cur[-1].text == " ":
                        cur.pop()
                    lines.append(cur)
                    cur, cur_w = [], 0.0
                cur.append(Run(token, r.italic, r.bold))
                cur_w += w
        while cur and cur[-1].text == " ":
            cur.pop()
        if cur:
            lines.append(cur)
        return lines

    def _break_indented(self, runs, width, indent, size):
        """Greedy wrap where line 1 is `indent` narrower than the rest."""
        def style_of(r):
            return ("I" if r.italic else "") + ("B" if r.bold else "")

        lines, cur, cur_w = [], [], 0.0
        line_no = 0
        for r in runs:
            self.set_font("Serif", style_of(r), size)
            for token in re.split(r"(\s+)", r.text):
                if token == "":
                    continue
                if token.isspace():
                    if cur:
                        cur.append(Run(" ", r.italic, r.bold))
                        cur_w += self.get_string_width(" ")
                    continue
                avail = width - (indent if line_no == 0 else 0.0)
                w = self.get_string_width(token)
                if cur and cur_w + w > avail:
                    while cur and cur[-1].text == " ":
                        cur.pop()
                    lines.append(cur)
                    cur, cur_w = [], 0.0
                    line_no += 1
                cur.append(Run(token, r.italic, r.bold))
                cur_w += w
        while cur and cur[-1].text == " ":
            cur.pop()
        if cur:
            lines.append(cur)
        return lines

    def para(self, runs, first_indent=True, space_after=0.0, align="J",
             lead=BODY_LEAD, size=BODY_PT):
        indent = 5.2 if first_indent else 0.0
        lines = self._break_indented(runs, TEXT_W, indent, size)
        bottom = PAGE_H - MARGIN_BOT
        if self.get_y() < MARGIN_TOP:
            self.set_y(MARGIN_TOP)
        i = 0
        while i < len(lines):
            remaining = len(lines) - i
            # avoid a one-line orphan at the foot of a page
            if remaining == 1 and i > 0 and self.get_y() + 2 * lead > bottom:
                self.add_page()
            elif self.get_y() + lead > bottom:
                self.add_page()
            y = self.get_y()
            x0 = self.l_margin + (indent if i == 0 else 0.0)
            w = TEXT_W - (indent if i == 0 else 0.0)
            self._write_line(lines[i], w, lead, y, x0,
                             align if i < len(lines) - 1 else "L", size)
            self.set_y(y + lead)
            i += 1
        if space_after:
            self.ln(space_after)

    def _write_line(self, line, width, lead, y, x0, align, size):
        spans = []
        for r in line:
            self.set_font("Serif", ("I" if r.italic else "") + ("B" if r.bold else ""), size)
            spans.append((r, self.get_string_width(r.text)))
        total = sum(w for _, w in spans)
        gaps = sum(1 for r in line if r.text == " ")
        extra = (width - total) / gaps if (align == "J" and gaps and total < width) else 0.0
        x = x0
        for r, w in spans:
            if r.text == " ":
                x += w + extra
                continue
            style = ("I" if r.italic else "") + ("B" if r.bold else "")
            self.set_font("Serif", style, size)
            self.text(x, y + lead * 0.78, r.text)
            x += w

    def center_line(self, text, size, style="", gap=6.0, tracking=0.0):
        self.set_font("Serif", style, size)
        if tracking:
            self.set_char_spacing(tracking)
        self.set_xy(MARGIN_IN, self.get_y())
        self.cell(TEXT_W, gap, text, align="C")
        if tracking:
            self.set_char_spacing(0)
        self.ln(gap)

    def rule(self, width_frac=0.22, gap_before=5.0, gap_after=5.0):
        self.ln(gap_before)
        w = TEXT_W * width_frac
        x = (PAGE_W - w) / 2
        self.set_draw_color(120, 120, 120)
        self.set_line_width(0.2)
        self.line(x, self.get_y(), x + w, self.get_y())
        self.ln(gap_after)

    def new_chapter_page(self):
        self.add_page()
        self._suppress_head = False
        self.set_y(MARGIN_TOP)


# ---------------------------------------------------------------- parsing


def load_blocks():
    text = SRC.read_text()
    blocks = []
    for chunk in text.split("\n\n"):
        c = chunk.strip("\n")
        if not c.strip():
            continue
        if re.fullmatch(r"-{3,}", c.strip()):
            blocks.append(("rule", None))
        elif c.startswith("# "):
            blocks.append(("h1", c[2:].strip()))
        elif c.startswith("## "):
            blocks.append(("h2", c[3:].strip()))
        elif c.startswith("> "):
            blocks.append(("quote", c[2:].strip()))
        elif re.fullmatch(r"\d+\.\s+.*", c.strip()):
            blocks.append(("numlist", c.strip()))
        else:
            blocks.append(("p", c))
    return blocks


def build(toc_pages):
    pdf = Book(toc_pages)
    pdf.set_title(TITLE)
    pdf.set_author("Arena Agent")
    pdf.set_subject("A Novella of Warsaw, 1958")
    pdf.set_creator("Arena Agent")

    blocks = load_blocks()

    # ---- title page (page 1, no number) --------------------------------
    pdf.add_page()
    pdf._suppress_head = True
    pdf.ln(38)
    pdf.center_line(TITLE, 21, "B", gap=11)
    pdf.rule(0.3, 2, 8)
    pdf.center_line("A NOVELLA OF WARSAW, 1958", 8.2, "", gap=7, tracking=0.55)
    pdf.ln(30)
    pdf.center_line("Arena Agent", 10.5, "", gap=6)
    pdf.ln(PAGE_H - pdf.get_y() - 40)
    pdf.center_line("An Arena Books original", 7.5, "", gap=5)

    # ---- epigraph (page 2) ---------------------------------------------
    pdf.add_page()
    pdf._suppress_head = True
    pdf.ln(52)
    pdf.set_font("Serif", "I", 11.5)
    pdf.set_x(MARGIN_IN + 12)
    pdf.multi_cell(TEXT_W - 24, 17, "The bell does not choose who hears it.", align="C")

    # ---- contents (page 3) ---------------------------------------------
    pdf.add_page()
    pdf._suppress_head = True
    pdf.ln(14)
    pdf.center_line("CONTENTS", 8.6, "", gap=7, tracking=0.6)
    pdf.rule(0.16, 3, 10)
    chapters = [b for k, b in blocks if k == "h1" and b.startswith("Chapter")]
    for i, title in enumerate(chapters, 1):
        label = re.sub(r"^Chapter\s+\w+:\s*", "", title)
        pdf.set_font("Serif", "", 9.6)
        page = toc_pages.get(title, "")
        pdf.set_x(MARGIN_IN + 4)
        pdf.cell(10, 7.2, str(i), align="L")
        pdf.set_x(MARGIN_IN + 4 + 10)
        pdf.cell(TEXT_W - 34, 7.2, label, align="L")
        pdf.cell(20, 7.2, str(page), align="R")
        pdf.ln(7.2)
    pdf.ln(4)
    pdf.set_font("Serif", "", 9.6)
    for label, key in (("Afterword", "Afterword"),
                       ("A Note on History", "A Note on History")):
        pdf.set_x(MARGIN_IN + 4)
        pdf.cell(TEXT_W - 24, 7.2, label, align="L")
        pdf.cell(20, 7.2, str(toc_pages.get(key, "")), align="R")
        pdf.ln(8)

    # ---- body -----------------------------------------------------------
    pdf._suppress_head = False
    first_chapter = True
    seen_chapters = 0
    marks = {}

    # skip the front-matter blocks already typeset by hand (title, epigraph,
    # contents heading and its numbered list) and begin at Chapter One
    start = next(n for n, (k, v) in enumerate(blocks)
                 if k == "h1" and v.startswith("Chapter One"))
    i = start
    started = False
    while i < len(blocks):
        kind, val = blocks[i]
        if kind == "h1":
            started = True
            if first_chapter:  # the contents page has just been closed
                pdf.first_body_page = pdf.page + 1
            pdf._opener_page = pdf.page + 1
            pdf.new_chapter_page()
            is_chapter = bool(re.match(r"^Chapter\s+\w+:", val))
            pdf.chapter_running = re.sub(r"^Chapter\s+\w+:\s*", "", val)
            if not is_chapter:      # back matter: plain centered heading
                pdf.ln(26)
                pdf.center_line(val.upper(), 10.5, "", gap=9, tracking=0.7)
                pdf.rule(0.14, 2, 10)
                pdf._opener_page = pdf.page
                marks[val] = pdf.page - pdf.first_body_page + 1
                pdf.start_section(val, level=0)
                i += 1
                continue
            first_chapter = False
            seen_chapters += 1
            num = re.match(r"^Chapter\s+(\w+):", val)
            pdf.ln(14)
            if num:
                pdf.center_line(num.group(1).upper(), 8.4, "", gap=8, tracking=0.7)
            title = re.sub(r"^Chapter\s+\w+:\s*", "", val)
            pdf.set_font("Serif", "B", 15.5)
            pdf.set_x(MARGIN_IN)
            pdf.multi_cell(TEXT_W, 21, title, align="C")
            pdf.ln(4)
            pdf.rule(0.14, 2, 9)
            pdf._opener_page = pdf.page
            marks[val] = pdf.page - pdf.first_body_page + 1
            pdf.start_section(val, level=0)
            i += 1
            continue
        if kind == "h2":
            pdf._opener_page = pdf.page + 1
            pdf.new_chapter_page()
            pdf.chapter_running = val
            pdf.ln(16)
            pdf.center_line(val.upper(), 9.6, "", gap=9, tracking=0.5)
            pdf.rule(0.14, 3, 10)
            pdf._opener_page = pdf.page
            marks[val] = pdf.page - pdf.first_body_page + 1
            i += 1
            continue
        if kind == "rule":
            pdf.rule(0.10, 6, 6)
            i += 1
            continue
        if kind == "quote":
            pdf.ln(4)
            pdf.set_font("Serif", "I", 11)
            pdf.set_x(MARGIN_IN + 14)
            pdf.multi_cell(TEXT_W - 28, 17, val, align="C")
            pdf.ln(6)
            i += 1
            continue
        if kind == "numlist":
            pdf.para(parse_runs(val), first_indent=False, space_after=1.2)
            i += 1
            continue
        # paragraph: first paragraph after a heading is flush, others indented
        prev_kind = blocks[i - 1][0] if i > 0 else "rule"
        flush = prev_kind in ("h1", "h2", "rule", "quote")
        pdf.para(parse_runs(val), first_indent=not flush)
        pdf.ln(1.6)
        i += 1

    pdf.output(OUT)
    return marks


def main():
    first_pass = build({})
    print(f"pass 1: {first_pass}")
    final = build(first_pass)
    print(f"pass 2: {final}")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} kB)")


if __name__ == "__main__":
    main()
