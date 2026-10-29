#!/usr/bin/env python3
"""Method v21 extractor for tip_1 multi-subject LGS study workbooks (pypdfium2).

Book model (verified from İÇİNDEKİLER + page dumps):
  p1-6 cover/TOC | unit section | unit key page(s) | then per exam year:
  cover ('2018-2019 Sınavla ... Merkezî Sınav Soruları') | subject-titled pages | exam key

- cal01 Fen, cal02 Matematik, cal06 Türkçe: single-subject books.
- cal05: İnkılap Tarihi (units 7-99), Din (101-182), İngilizce (184-342);
  exam sections carry per-subject page headers (T.C. İNKILAP... / DİN KÜLTÜRÜ... /
  YABANCI DİL...) with 10 questions per subject per year.

Answer-key layouts (verified by rect dumps):
  * unit key pages: 'N. Ünite/Unit/Tema' label at left; below it, rows of
    'k. L' pairs (up to 10 per row, several rows, ~40-50 per unit).
  * exam key pages (cal01/02/06): single column 'k.' + letter, rows top-down.
  * exam key pages (cal05): three columns labelled by subject name above.

v21 contract:
  * content bbox from TEXT boxes only (page rules/curves are layout, not content)
  * 20 pt margin measured from that text envelope on all four sides
  * center divider from rendered colored vertical band
  * one PNG per complete question (number + stem + figure + all choices)
  * answer keys parsed with coordinate-based row/column detection
  * six subject folders + answers.json + manifest.json directly in the repo root

Coordinate flip: pdfium rects are (left, bottom, right, top), y grows UP.
We flip to top-down: y0 = H - top, y1 = H - bottom.

Usage:
  python3 extract_tip1_v21.py --subjects ingilizce
  python3 extract_tip1_v21.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pypdfium2 as pdfium

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları")
OUTPUT_DIR = REPO

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
HEADER_CUT_PT = 80.0
QRE = re.compile(r"^(\d{1,3})[.)]?$")
# Question anchors in these workbooks are always 'N.' — require the dot so
# graph axis labels ('90', '80', ...) never become anchors.
ANCHOR_RE = re.compile(r"^(\d{1,3})\.$")
QLINE_RE = re.compile(r"^(\d{1,2})[.)]\s")
UNIT_LABEL_RE = re.compile(r"^(\d{1,2})[.)]\s*(Ünite|Unit|Tema)", re.IGNORECASE)
PAIR_RE = re.compile(r"^(\d{1,2})[.)]\s*([A-E])$")

SLUGS = ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]
SLUG_NAME = {
    "turkce": "Türkçe",
    "matematik": "Matematik",
    "fen-bilimleri": "Fen Bilimleri",
    "ingilizce": "Yabancı Dil (İngilizce)",
    "din-kulturu": "Din Kültürü ve Ahlak Bilgisi",
    "inkilap-tarihi": "T.C. İnkılap Tarihi ve Atatürkçülük",
}
BOOKS = {
    "cal01.pdf": ["fen-bilimleri"],
    "cal02.pdf": ["matematik"],
    "cal05.pdf": ["inkilap-tarihi", "din-kulturu", "ingilizce"],
    "cal06.pdf": ["turkce"],
}
KEY_MARKERS = ["CEVAP ANAHTARI", "ANSWER KEY"]
COVER_RE = re.compile(r"(\d{4})-(\d{4})\s+Sınavla", re.IGNORECASE)
# header rules in priority order (checked against the first lines of a page)
HEADER_RULES = [
    ("ingilizce", ["YABANCI DİL", "İNGİLİZCE", "ENGLISH"]),
    ("din-kulturu", ["DİN KÜLTÜRÜ", "AHLAK BİLGİSİ"]),
    ("inkilap-tarihi", ["T.C. İNKILAP", "İNKILAP TARİHİ", "ATATÜRKÇÜLÜK"]),
    ("fen-bilimleri", ["FEN BİLİMLERİ"]),
    ("matematik", ["MATEMATİK"]),
    ("turkce", ["TÜRKÇE"]),
]


# ------------------------------------------------------------------ page level

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def page_rects(page) -> list[dict]:
    """Text runs {x0,y0,x1,y1,text}, top-down y, from pdfium bounded rects."""
    tp = page.get_textpage()
    height = page.get_size()[1]
    out = []
    for i in range(tp.count_rects()):
        left, bottom, right, top = tp.get_rect(i)
        text = tp.get_text_bounded(left, bottom, right, top)
        if not text or not text.strip():
            continue
        out.append({"x0": float(left), "x1": float(right),
                    "y0": height - float(top), "y1": height - float(bottom),
                    "text": text.strip()})
    out.sort(key=lambda r: (r["y0"], r["x0"]))
    return out


def visual_lines(rects: list[dict]) -> list[dict]:
    """Merge runs sharing a baseline band into visual lines, left-to-right."""
    lines: list[dict] = []
    for r in rects:
        placed = False
        for ln in lines:
            if abs(r["y0"] - ln["y0"]) <= 3.0 and abs(r["y1"] - ln["y1"]) <= 3.0:
                ln["runs"].append(r)
                ln["x0"] = min(ln["x0"], r["x0"])
                ln["x1"] = max(ln["x1"], r["x1"])
                ln["y0"] = min(ln["y0"], r["y0"])
                ln["y1"] = max(ln["y1"], r["y1"])
                placed = True
                break
        if not placed:
            lines.append({"x0": r["x0"], "x1": r["x1"], "y0": r["y0"], "y1": r["y1"],
                          "runs": [r]})
    for ln in lines:
        ln["runs"].sort(key=lambda r: r["x0"])
        parts: list[str] = []
        prev = None
        for r in ln["runs"]:
            if prev is not None and r["x0"] - prev > 2.0:
                parts.append(" ")
            parts.append(r["text"])
            prev = r["x1"]
        ln["text"] = "".join(parts).strip()
    lines.sort(key=lambda l: (l["y0"], l["x0"]))
    return lines


def render(page, dpi: int = DPI):
    return page.render(scale=dpi / 72).to_pil().convert("RGB")


def load_book(path: Path) -> list[dict]:
    doc = pdfium.PdfDocument(str(path))
    pages = []
    for i in range(len(doc)):
        page = doc[i]
        rects = page_rects(page)
        pages.append({
            "index": i + 1,
            "page": page,
            "rects": rects,
            "lines": visual_lines(rects),
            "size": page.get_size(),
        })
    return pages


# ------------------------------------------------------------ v21 crop geometry

def divider_x(img, width_pt: float) -> float | None:
    """Colored vertical band near the page centre (v21 divider rule)."""
    scale = img.width / width_pt
    center = int((width_pt / 2) * scale)
    best = None
    for x in range(max(0, center - int(20 * scale)), min(img.width, center + int(40 * scale))):
        colored = 0
        for y in range(0, img.height, 2):
            r, g, b = img.getpixel((x, y))
            if max(r, g, b) - min(r, g, b) > 55 and min(r, g, b) < 220:
                colored += 1
        if best is None or colored > best[1]:
            best = (x, colored)
    if best and best[1] >= (img.height / 2) * 0.20:
        return best[0] / scale
    return None


def anchors_of(rects: list[dict], width_pt: float, height_pt: float | None = None) -> list[dict]:
    """Rect-level anchor detection: 'N.' runs near a column edge (v21 anchor rule).

    Works on raw rects (not merged visual lines) so two-column pages keep
    separate left/right anchors instead of fusing them into one line.

    Filters:
      * page numbers (y > 770 near the bottom edge);
      * two-digit anchors are trusted anywhere near an edge; single-digit
        anchors must sit in the far-left band (x0 < 60) or the right-column
        band — mid-column digits ('0' inside a figure) are dropped.
    """
    out = []
    for r in rects:
        m = ANCHOR_RE.fullmatch(r["text"])
        if not m:
            continue
        num = int(m.group(1))
        if not 1 <= num <= 250:
            continue
        x0 = r["x0"]
        if height_pt is not None and r["y0"] > height_pt - 70.0:
            continue                     # footer / page number band
        left_band = x0 <= 80.0
        right_band = width_pt / 2 - 5.0 <= x0 <= width_pt / 2 + 55.0
        if num < 10 and not (x0 <= 60.0 or right_band):
            continue                     # digit inside content/figures
        if left_band or right_band:
            out.append({"num": num, "x0": x0, "y0": r["y0"]})
    return out


def content_bbox(rects, y_from: float, y_to: float,
                 x_from: float, x_to: float) -> dict | None:
    sel = [r for r in rects
           if y_from - 2.0 <= r["y0"] < y_to
           and x_from <= r["x0"] and r["x1"] <= x_to]
    if not sel:
        return None
    return {
        "x0": min(r["x0"] for r in sel),
        "y0": min(r["y0"] for r in sel),
        "x1": max(r["x1"] for r in sel),
        "y1": max(r["y1"] for r in sel),
    }


def crop_specs(page, rects, anchors, width_pt, height_pt, head_cut) -> list[dict]:
    left = [a for a in anchors if a["x0"] < width_pt / 2]
    right = [a for a in anchors if a["x0"] >= width_pt / 2]
    div = divider_x(render(page, 72), width_pt)

    if left and right:
        groups = {"left": left, "right": right}
        bounds = {
            "left": (MARGIN_PT, width_pt / 2, 0.0, width_pt / 2),
            "right": (width_pt / 2, width_pt - MARGIN_PT, width_pt / 2, width_pt),
        }
        if div is not None:
            bounds["left"] = (bounds["left"][0], div - MARGIN_PT, bounds["left"][2], div)
            bounds["right"] = (div, bounds["right"][1], div, bounds["right"][3])
    else:
        groups = {"single": anchors}
        bounds = {"single": (MARGIN_PT, width_pt - MARGIN_PT, 0.0, width_pt)}

    specs = []
    for column, col in groups.items():
        col = sorted(col, key=lambda a: a["y0"])
        crop_left, crop_right, scan_left, scan_right = bounds[column]
        for idx, a in enumerate(col):
            next_y = col[idx + 1]["y0"] if idx + 1 < len(col) else height_pt - FOOTER_PT
            bbox = content_bbox(rects, a["y0"], next_y, scan_left, scan_right)
            if bbox:
                top = max(0.0, bbox["y0"] - MARGIN_PT, head_cut)
                bottom = min(height_pt, next_y, bbox["y1"] + MARGIN_PT)
                l = max(crop_left, bbox["x0"] - MARGIN_PT)
                r = min(crop_right, bbox["x1"] + MARGIN_PT)
            else:
                top = max(0.0, a["y0"] - MARGIN_PT, head_cut)
                bottom, l, r = next_y, crop_left, crop_right
            if bottom <= top or r <= l:
                continue
            specs.append({
                "questionNumber": a["num"],
                "column": column,
                "clipRectPt": {"x0": round(l, 3), "y0": round(top, 3),
                               "x1": round(r, 3), "y1": round(bottom, 3)},
            })
    return sorted(specs, key=lambda s: s["questionNumber"])


# ------------------------------------------------------------- answer key model

def parse_pairs(rects: list[dict]) -> dict[int, str]:
    """Parse 'k.' runs + nearest A-E run to the right on the same baseline.

    Handles both separate runs ('1.' 'D') and fused runs ('43. A')."""
    rows: dict[int, list[dict]] = defaultdict(list)
    for r in rects:
        rows[round(r["y0"] / 3.0)].append(r)
    pairs: dict[int, str] = {}
    for _row, runs in rows.items():
        runs = sorted(runs, key=lambda r: r["x0"])
        # 1) fused runs like '43. A'
        for r in runs:
            m = PAIR_RE.fullmatch(r["text"])
            if m:
                pairs.setdefault(int(m.group(1)), m.group(2))
        # 2) separate 'k.' + letter runs
        for i, r in enumerate(runs):
            m = QRE.fullmatch(r["text"])
            if not m:
                continue
            qn = int(m.group(1))
            if not 1 <= qn <= 250:
                continue
            if qn in pairs:
                continue
            for other in runs[i + 1:]:
                if other["x0"] - r["x0"] > 45:
                    break
                letter = other["text"].strip()
                if re.fullmatch(r"[A-E]", letter):
                    pairs.setdefault(qn, letter)
                    break
    return pairs


def _rect_qn(r: dict) -> int | None:
    """Question number of a key-page rect: '5.', or fused '43. A'."""
    m = QRE.fullmatch(r["text"])
    if m:
        return int(m.group(1))
    m = PAIR_RE.fullmatch(r["text"])
    if m:
        return int(m.group(1))
    return None


def unit_key_blocks(rects: list[dict]) -> list[tuple[int, list[dict]]]:
    """Split a unit key page into blocks by reading order, not by label position.

    Answer rows run row-major (1..k per unit). A block boundary is where the
    question number sequence RESETS to 1 (probe-verified on all four books).
    Block k is then unit k of that subject (numbering continues across the
    book's consecutive key pages). Each block's selection keeps ALL rects in
    its y-range (letters included) so parse_pairs can pair them up.
    """
    numbered: list[dict] = []
    for r in rects:
        qn = _rect_qn(r)
        if qn is not None and 1 <= qn <= 250:
            numbered.append(r)
    rows: dict[int, list[dict]] = {}
    for r in numbered:
        rows.setdefault(round(r["y0"] / 3), []).append(r)
    ordered: list[dict] = []
    for band in sorted(rows):
        ordered.extend(sorted(rows[band], key=lambda r: r["x0"]))
    if not ordered:
        return []
    # Split on reset-to-1. A unit LABEL ('1. Ünite') also prints a bare '1'
    # mid-row, but the next numbered rect in reading order is a continuation
    # (41, 42, ...). A genuine unit boundary restarts 1, 2, 3, ... so require
    # the '1' to be immediately followed by '2'.
    splits: list[int] = [0]
    prev = _rect_qn(ordered[0])
    for i, r in enumerate(ordered[1:], 1):
        qn = _rect_qn(r)
        next_qn = _rect_qn(ordered[i + 1]) if i + 1 < len(ordered) else None
        if qn == 1 and prev != 0 and next_qn == 2:
            splits.append(i)
        prev = qn
    splits.append(len(ordered))
    out: list[tuple[int, list[dict]]] = []
    for k in range(len(splits) - 1):
        chunk = ordered[splits[k]:splits[k + 1]]
        if not chunk:
            continue
        y_from = min(r["y0"] for r in chunk)
        y_to = max(r["y1"] for r in chunk)
        sel = [r for r in rects if y_from - 1.0 <= r["y0"] <= y_to + 1.0]
        out.append((k + 1, sel))
    return out


def exam_key_columns(rects: list[dict]) -> list[tuple[str, float, float, list[dict]]] | None:
    """Exam key page. Returns column specs, or None if no subject labels found.

    cal01/02/06: one column, a subject label above ('Fen Bilimleri', ...).
    cal05: three columns, each labelled by subject name fragments.
    """
    labels = [r for r in rects
              if len(r["text"]) > 3
              and not re.search(r"\d", r["text"])
              and r["text"].upper() not in {"CEVAP ANAHTARI", "ANSWER KEY",
                                            "SÖZEL BÖLÜM", "SAYISAL BÖLÜM",
                                            "MEB ÖLÇME, DEĞERLENDIRME VE SINAV HIZMETLERI GENEL MÜDÜRLÜĞÜ"}]
    cols = []
    for r in labels:
        t = r["text"].upper()
        for slug, name in SLUG_NAME.items():
            up = name.upper()
            # match 'FEN BİLİMLERİ' ~ 'FEN BİLİMLERİ', 'T.C. İNKILAP' ~ prefix
            if up[:10] in t or t[:10] in up:
                cols.append((slug, r["x0"], r["x1"], r["y0"]))
                break
    if not cols:
        return None
    # de-duplicate labels per slug, keep topmost
    seen: dict[str, tuple] = {}
    for c in sorted(cols, key=lambda c: c[3]):
        seen.setdefault(c[0], c)
    xs = sorted(seen.values(), key=lambda c: c[1])
    out = []
    for i, (slug, x0, x1, _y) in enumerate(xs):
        x_end = xs[i + 1][1] if i + 1 < len(xs) else 10_000.0
        sel = [r for r in rects if x0 - 40 <= r["x0"] < x_end - 5
               and r["text"] not in {seen[slug][0:2] and "", ""}]  # keep all; labels filtered below
        out.append((slug, x0, x_end, sel))
    return out


# ------------------------------------------------------------------ book model

def header_subject(lines: list[dict]) -> str | None:
    """Subject from a page's top lines; None for content pages without headers."""
    head = " ".join(l["text"] for l in lines[:4]).upper()
    for slug, keys in HEADER_RULES:
        if any(k in head for k in keys):
            return slug
    return None


def is_key_page(p: dict) -> bool:
    text_up = " ".join(l["text"] for l in p["lines"]).upper()
    return any(m in text_up for m in KEY_MARKERS)


UNIT_KEY_LINE_RE = re.compile(r"^(\d{1,2})[.)]\s*[A-E](\s+\d{1,2}[.)]\s*[A-E])*\s*$")


def is_key_continuation(p: dict) -> bool:
    """A page that continues the previous key page (e.g. cal05 p344).

    cal05's English answer key spills onto a second page that carries no
    'ANSWER KEY' banner: its lines are dense fused pair rows like
    '1.D 2.D 3.A 4.C'. Detect: >=3 such rows among the first 6 lines.
    """
    pair_lines = sum(1 for l in p["lines"][:6] if UNIT_KEY_LINE_RE.fullmatch(l["text"]))
    return pair_lines >= 3


def is_cover_page(p: dict) -> bool:
    return bool(COVER_RE.search(" ".join(l["text"] for l in p["lines"])))


def has_meb_strip(p: dict) -> bool:
    """'MEB ● Ölçme, Değerlendirme ...' running strip on exam pages."""
    return "ÖLÇME" in " ".join(l["text"] for l in p["lines"][:4]).upper()


def extract_page(p: dict, slug: str, bucket: dict, prefix: str,
                 year: str | None, trace: list[str], unit_no: int | None = None,
                 source_file: str = "") -> int:
    """Crop all questions on one page into the bucket. Returns count written.

    Sequential-expectation filter: within a tag (unit or exam), question
    numbers must arrive in order. An anchor whose number is smaller than the
    next expected one (or already seen) is a matching-list digit inside a
    question ('1. Do you play...?'), not a new question.
    """
    width_pt, height_pt = p["size"]
    anchors = anchors_of(p["rects"], width_pt, height_pt)
    if not anchors:
        return 0
    # Header cut applies ONLY when the MEB 'Ölçme, Değerlendirme...' strip is
    # actually printed on this page; exam pages without the strip (and all
    # unit pages) start their first question near y~42 and must not be cut.
    head_cut = HEADER_CUT_PT if (p["index"] > 6 and has_meb_strip(p)) else 0.0
    tag_prefix = f"u{unit_no:02d}" if unit_no else prefix
    # next expected question number for this tag
    expect = max([q for (t, q) in bucket["seen"] if t == tag_prefix], default=0) + 1
    anchors = [a for a in anchors if a["num"] >= expect]
    anchors = sorted(anchors, key=lambda a: (a["y0"], a["x0"]))
    specs = crop_specs(p["page"], p["rects"], anchors, width_pt, height_pt, head_cut)
    if not specs:
        return 0
    img = render(p["page"])
    sx = img.width / width_pt
    sy = img.height / height_pt
    out = OUTPUT_DIR / slug
    out.mkdir(parents=True, exist_ok=True)
    tag = f"u{unit_no:02d}" if unit_no else prefix
    written = 0
    for spec in specs:
        qn = spec["questionNumber"]
        key = (tag, qn)
        if key in bucket["seen"]:
            continue
        rect = spec["clipRectPt"]
        box = (round(rect["x0"] * sx), round(rect["y0"] * sy),
               round(rect["x1"] * sx), round(rect["y1"] * sy))
        if box[2] <= box[0] or box[3] <= box[1]:
            trace.append(f"  [{slug}] {tag}-q{qn:02d} invalid box {box}")
            continue
        bucket["seen"].add(key)
        ident = f"{tag}-q{qn:02d}"
        fp = out / f"{ident}.png"
        img.crop(box).save(fp, "PNG")
        bucket["questions"].append({
            "id": f"STUDY-TIP1-{slug.upper()}-{ident}",
            "file": f"{ident}.png",
            "questionNumber": qn,
            "page": p["index"],
            "sourceFile": source_file,
            "column": spec["column"],
            "section": "EXAM" if year else "UNIT",
            "examYear": year,
            "unitNo": unit_no,
            "representation": "IMAGE_BACKED",
            "visual": {
                "publicPath": f"/{slug}/{ident}.png",
                "clipRectPt": rect,
                "renderDpi": DPI,
                "authority": "ORIGINAL_STUDY_WORKBOOK_PDF",
                "reconstructedFromOcr": False,
                "assetSha256": sha256(fp),
            },
            "status": "NEEDS_REVIEW",
            "published": False,
        })
        written += 1
    return written


def run(subjects_filter: list[str] | None) -> int:
    trace: list[str] = []
    combined: dict[str, dict] = {}

    def bucket_for(slug: str) -> dict:
        if slug not in combined:
            combined[slug] = {"questions": [], "answers": {}, "sources": [],
                              "shas": {}, "seen": set()}
        b = combined[slug]
        return b

    for fname, book_subjects in BOOKS.items():
        path = INPUT_DIR / fname
        if not path.exists():
            trace.append(f"MISSING {fname}")
            continue
        src_sha = sha256(path)
        pages = load_book(path)
        n = len(pages)
        trace.append(f"{fname}: {n} pages")

        keys = [p["index"] for p in pages if is_key_page(p)]
        # key continuation pages: follow a real key page and carry dense pairs
        cont_keys = [p["index"] for i, p in enumerate(pages)
                     if p["index"] > 6 and is_key_continuation(p)
                     and any(k == p["index"] - 1 for k in keys)]
        keys = sorted(set(keys) | set(cont_keys))
        covers = [p["index"] for p in pages if is_cover_page(p)]
        # Unit key pages: subject-titled + multi-block. Exam key pages:
        # 'SÖZEL/SAYISAL BÖLÜM' titled (or a single 10-question column).
        unit_key_pages: list[int] = []
        exam_key_pages: list[int] = []
        for k in keys:
            if k <= 6:
                continue                      # TOC
            head = " ".join(l["text"] for l in pages[k - 1]["lines"][:3]).upper()
            blocks = unit_key_blocks(pages[k - 1]["rects"])
            real_blocks = [s for _, s in blocks if len(parse_pairs(s)) >= 4]
            if "BÖLÜM" in head or len(real_blocks) <= 1:
                exam_key_pages.append(k)
            else:
                unit_key_pages.append(k)
        trace.append(f"  covers={covers}")
        trace.append(f"  unit_keys={unit_key_pages} exam_keys={exam_key_pages}")

        single = len(book_subjects) == 1
        first_cover = covers[0] if covers else n + 1

        # ---------- unit sections (pages 7 .. first cover, minus key pages) ----------
        unit_pages = [p for p in pages[6:first_cover - 1] if p["index"] not in keys]

        # Walk unit pages in order; the CURRENT subject switches on unit cover
        # pages (most content pages carry no running header in these books).
        # A new unit starts on a page whose own header/label announces it
        # ('1. Ünite', 'Unit 1', '1. Tema', or a GRADE English unit cover).
        # Within a unit, matching-list digits (1., 2., ... inside a question)
        # must NOT restart the count, so the 'expect' rule is only applied on
        # pages that follow a unit cover.
        per_subject_unit: dict[str, int] = {s: 0 for s in book_subjects}
        current: str | None = book_subjects[0] if single else None
        for p in unit_pages:
            hs = header_subject(p["lines"])
            page_text0 = " ".join(l["text"] for l in p["lines"][:4])
            is_unit_cover = bool(
                re.search(r"(\d{1,2})[.)]\s*(Ünite|Unit|Tema)", page_text0, re.IGNORECASE)
                or re.search(r"\bUnit\s+\d+\b", page_text0, re.IGNORECASE)
            )
            if hs:
                current = hs
            if current is None:
                continue
            if subjects_filter and current not in subjects_filter:
                continue
            slug = current
            if is_unit_cover:
                m = (re.search(r"(\d{1,2})[.)]\s*(?:Ünite|Unit|Tema)", page_text0, re.IGNORECASE)
                     or re.search(r"\b(?:Ünite|Unit|Tema)\s+(\d{1,2})\b", page_text0, re.IGNORECASE))
                if m:
                    per_subject_unit[slug] = int(m.group(1))
                elif per_subject_unit[slug] == 0:
                    per_subject_unit[slug] = 1
            if per_subject_unit[slug] == 0:
                per_subject_unit[slug] = 1
            bucket = bucket_for(slug)
            if fname not in bucket["sources"]:
                bucket["sources"].append(fname)
                bucket["shas"][fname] = src_sha
            extract_page(p, slug, bucket, "u", None, trace, per_subject_unit[slug],
                         source_file=fname)

        # ---------- unit answers ----------
        # Unit key pages follow the book's own section order:
        #   cal01/02/06: one key block-set for the single subject.
        #   cal05: p100 İnkılap, p183 Din, p343+p344 İngilizce (consecutive pages
        #   continue the same subject's unit numbering).
        # TOC (p6) also contains a few numbered runs; ignore key pages with
        # fewer than 2 blocks or whose total pairs are trivial (< 10).
        unit_key_subject_map: dict[int, str] = {}
        if single:
            unit_key_subject_map = {kp: book_subjects[0] for kp in unit_key_pages}
        elif fname == "cal05.pdf":
            unit_key_subject_map = {100: "inkilap-tarihi", 183: "din-kulturu",
                                    343: "ingilizce", 344: "ingilizce"}
        unit_counter: dict[str, int] = {}
        for kp in unit_key_pages:
            blocks = unit_key_blocks(pages[kp - 1]["rects"])
            if not blocks:
                continue
            slug = unit_key_subject_map.get(kp)
            if slug is None:
                hs = header_subject(pages[kp - 1]["lines"])
                slug = hs or (book_subjects[0] if single else None)
            if slug is None:
                trace.append(f"  unit key p{kp}: subject UNKNOWN, skipped")
                continue
            if subjects_filter and slug not in subjects_filter:
                continue
            b = bucket_for(slug)
            base = unit_counter.get(slug, 0)
            for offset_idx, (_blk, sel) in enumerate(blocks):
                pairs = parse_pairs(sel)
                if len(pairs) < 2:      # TOC fragments / noise
                    continue
                unit_no = base + offset_idx + 1
                for q, a in pairs.items():
                    b["answers"].setdefault(f"u{unit_no:02d}-q{q:02d}", a)
                trace.append(f"  unit key p{kp} {slug} unit{unit_no}: {len(pairs)} pairs")
            unit_counter[slug] = base + len(blocks)

        # ---------- exam sections ----------
        for ci, cover in enumerate(covers):
            m = COVER_RE.search(" ".join(l["text"] for l in pages[cover - 1]["lines"]))
            year = m.group(1) if m else f"exam{ci}"
            sec_end = covers[ci + 1] - 1 if ci + 1 < len(covers) else n
            key_pages = [k for k in exam_key_pages if cover < k <= sec_end]
            span = [p for p in pages[cover:sec_end] if p["index"] not in key_pages]

            if single:
                slug = book_subjects[0]
                if subjects_filter and slug not in subjects_filter:
                    continue
                bucket = bucket_for(slug)
                if fname not in bucket["sources"]:
                    bucket["sources"].append(fname)
                    bucket["shas"][fname] = src_sha
                cnt = 0
                for p in span:
                    cnt += extract_page(p, slug, bucket, f"lgs{year}", year, trace,
                                        source_file=fname)
                trace.append(f"  exam {year} ({slug}): {cnt} questions from "
                             f"p{cover + 1}-{sec_end}")
            else:
                # multi-subject exam: split by subject-titled pages
                current: str | None = None
                for p in span:
                    hs = header_subject(p["lines"])
                    if hs:
                        current = hs
                    if current is None:
                        continue
                    if subjects_filter and current not in subjects_filter:
                        continue
                    bucket = bucket_for(current)
                    if fname not in bucket["sources"]:
                        bucket["sources"].append(fname)
                        bucket["shas"][fname] = src_sha
                    extract_page(p, current, bucket, f"lgs{year}", year, trace,
                                 source_file=fname)
                trace.append(f"  exam {year}: split by headers over p{cover + 1}-{sec_end}")

            # exam answers
            for kp in key_pages:
                kpage = pages[kp - 1]
                cols = exam_key_columns(kpage["rects"])
                if cols:
                    for slug, x0, x_end, sel in cols:
                        if subjects_filter and slug not in subjects_filter:
                            continue
                        pairs = parse_pairs(sel)
                        b = bucket_for(slug)
                        for q, a in pairs.items():
                            b["answers"].setdefault(f"lgs{year}-q{q:02d}", a)
                        trace.append(f"  exam key p{kp} col {slug}: {len(pairs)} answers")
                else:
                    slug = book_subjects[0] if single else None
                    if slug and not (subjects_filter and slug not in subjects_filter):
                        pairs = parse_pairs(kpage["rects"])
                        b = bucket_for(slug)
                        for q, a in pairs.items():
                            b["answers"].setdefault(f"lgs{year}-q{q:02d}", a)
                        trace.append(f"  exam key p{kp} single {slug}: {len(pairs)} answers")

    # ---------- outputs ----------
    for slug in SLUGS:
        data = combined.get(slug)
        if not data or not data["questions"]:
            continue
        out = OUTPUT_DIR / slug
        out.mkdir(parents=True, exist_ok=True)
        data["questions"].sort(key=lambda q: (q["section"], q["examYear"] or "",
                                              q["unitNo"] or 0, q["questionNumber"]))
        (out / "answers.json").write_text(
            json.dumps(data["answers"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest = {
            "manifestVersion": "1.0",
            "status": "NEEDS_REVIEW",
            "published": False,
            "method": "v21",
            "render": {"dpi": DPI, "margin_pt_all_sides": MARGIN_PT,
                       "footer_exclusion_pt": FOOTER_PT, "header_cut_pt": HEADER_CUT_PT,
                       "bbox_source": "text_boxes_only", "reconstructed_from_ocr": False},
            "source": {
                "sourceId": f"STUDY-TIP1-{slug.upper()}",
                "sourceType": "STUDY_WORKBOOK",
                "subject": SLUG_NAME[slug],
                "grade": 8,
                "files": data["sources"],
                "sha256": data["shas"],
            },
            "questions": data["questions"],
            "answerKey": data["answers"],
            "summary": {"questionsExtracted": len(data["questions"]),
                        "answersFound": len(data["answers"])},
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"subject": slug, **manifest["summary"]}, ensure_ascii=False))

    log = REPO / "logs" / "TRACE.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(trace) + "\n")
    print(json.dumps({"trace": trace}, ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", nargs="*", default=None,
                    help="subject slugs to extract (default: all six)")
    args = ap.parse_args()
    return run(args.subjects)


if __name__ == "__main__":
    sys.exit(main())
