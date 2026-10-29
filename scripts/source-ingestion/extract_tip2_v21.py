#!/usr/bin/env python3
"""Method v21 extractor for tip_2 province-based LGS study workbooks (pypdfium2).

Book model (verified from cal07.pdf):
  p1-6 cover/TOC | then per province:
  province title page ('<İl> Ölçme Değerlendirme Merkezi Çalışma Soruları')
  subject sections with headers like 'Türkçe Soruları', 'Matematik Soruları', ...
  answer key page ('CEVAP ANAHTARI') with subject column headers

- cal07-cal12.pdf: province-based books, each containing 6 subjects.
- Subject sections: 'X Soruları' header lines at page top.
- Answer keys: multi-column, each column labelled by subject name.

v21 contract (same as tip_1):
  * content bbox from TEXT boxes only
  * 20 pt margin measured from that text envelope on all four sides
  * center divider from rendered colored vertical band
  * one PNG per complete question
  * answer keys parsed with coordinate-based row/column detection

Usage:
  python3 extract_tip2_v21.py --subjects matematik turkce
  python3 extract_tip2_v21.py
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
INPUT_DIR = Path("/media/selam/Yeni Birim/Lgs Temel Kaynaklar/lgs_çalışma_soruları/tip_2")
OUTPUT_DIR = REPO

DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
HEADER_CUT_PT = 80.0
QRE = re.compile(r"^(\d{1,2})[.)]?$")
QLINE_RE = re.compile(r"^(\d{1,2})[.)]\s")
PAIR_RE = re.compile(r"^(\d{1,2})[.)]\s*([A-E])$")

# Subject slugs and their header patterns (Turkish)
SLUGS = ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]
SLUG_NAME = {
    "turkce": "Türkçe",
    "matematik": "Matematik",
    "fen-bilimleri": "Fen Bilimleri",
    "ingilizce": "İngilizce",
    "din-kulturu": "Din Kültürü ve Ahlak Bilgisi",
    "inkilap-tarihi": "T.C. İnkılap Tarihi ve Atatürkçülük",
}

# Subject header patterns for tip_2 (Turkish). Two forms seen:
#  'Türkçe Soruları' (mixed case, one form) and bare 'TÜRKÇE' alone on a line.
SUBJECT_HEADER_RULES = [
    ("turkce", [r"TÜRKÇE(\s+SORULAR)?\b"]),
    ("matematik", [r"MATEMATİK(\s+SORULAR)?\b"]),
    ("fen-bilimleri", [r"FEN\s+BİLİMLERİ(\s+SORULAR)?\b"]),
    ("inkilap-tarihi", [r"(T\.C\.\s*)?İNKILAP\s+TARİHİ(\s+VE(\s+ATATÜRKÇÜLÜK)?(\s+SORULAR)?)?\b"]),
    ("ingilizce", [r"(İNGİLİZCE|YABANCI\s+DİL)(\s+SORULAR)?\b"]),
    ("din-kulturu", [r"DİN\s+KÜLTÜRÜ(\s+VE(\s+AHLAK\s+BİLGİSİ)?(\s+SORULAR)?)?\b"]),
]

# Province title pattern (on TOC page: '<İl> Ölçme Değerlendirme Merkezi Çalışma Soruları N')
# Some lines fuse the page number without a space ('...Soruları23'), so the
# separator before the number is optional.
PROVINCE_TOC_RE = re.compile(r"(.+?)\s+Ölçme\s+Değerlendirme\s+Merkezi\s+Çalışma\s+Soruları\s*(\d+)", re.IGNORECASE)
# Province title page (on section start: '<İl>\nÖDM\n8. Sınıf\nÇalışma Soruları')
PROVINCE_TITLE_RE = re.compile(r"^(.+?)\s*$", re.IGNORECASE)
ÖDM_MARKER = "ÖDM"

BOOKS = {
    "cal07.pdf": SLUGS,
    "cal08.pdf": SLUGS,
    "cal09.pdf": SLUGS,
    "cal10.pdf": SLUGS,
    "cal11.pdf": SLUGS,
    "cal12.pdf": SLUGS,
}

KEY_MARKERS = ["CEVAP ANAHTARI", "ANSWER KEY"]


# ------------------------------------------------------------------ page level

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def page_rects(page) -> list[dict]:
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
    out = []
    for r in rects:
        m = QRE.fullmatch(r["text"])
        if not m:
            continue
        num = int(m.group(1))
        if not 1 <= num <= 90:
            continue
        # Skip printed page numbers in the footer zone
        if height_pt is not None and r["y0"] > height_pt - FOOTER_PT:
            continue
        x0 = r["x0"]
        if x0 <= 80.0 or width_pt / 2 - 5.0 <= x0 <= width_pt / 2 + 55.0:
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
    rows: dict[int, list[dict]] = defaultdict(list)
    for r in rects:
        rows[round(r["y0"] / 3.0)].append(r)
    pairs: dict[int, str] = {}
    for _row, runs in rows.items():
        runs = sorted(runs, key=lambda r: r["x0"])
        for r in runs:
            m = PAIR_RE.fullmatch(r["text"])
            if m:
                pairs.setdefault(int(m.group(1)), m.group(2))
        for i, r in enumerate(runs):
            m = QRE.fullmatch(r["text"])
            if not m:
                continue
            qn = int(m.group(1))
            if not 1 <= qn <= 90:
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


def exam_key_columns(rects: list[dict],
                     page_size: tuple[float, float]) -> list[tuple[str, float, float, list[dict]]] | None:
    """Answer key regions labelled by subject name.

    Key pages may lay subjects in one row (tip_1 style) or in a 2-row x 3-column
    grid (tip_2 province keys: TÜRKÇE/MATEMATİK/FEN on top, İNKILAP/DİN/İNGİLİZCE
    below). Regions must therefore be segmented by BOTH y (row) and x (column) —
    sorting by x alone lets a top-row column be truncated by a bottom-row label
    that happens to sit just to its right.
    """
    W, H = page_size
    labels = [r for r in rects
              if len(r["text"]) > 3
              and not re.search(r"\d", r["text"])
              and tr_upper(r["text"]) not in {"CEVAP ANAHTARI", "ANSWER KEY",
                                              "SÖZEL BÖLÜM", "SAYISAL BÖLÜM"}]
    matched: list[tuple[str, dict]] = []
    for r in labels:
        t = tr_upper(r["text"])
        for slug, name in SLUG_NAME.items():
            up = tr_upper(name)
            if up[:10] in t or t[:10] in up:
                matched.append((slug, r))
                break
    if not matched:
        return None
    # de-duplicate per slug, keep topmost occurrence
    seen: dict[str, dict] = {}
    for slug, r in sorted(matched, key=lambda m: m[1]["y0"]):
        seen.setdefault(slug, r)
    # cluster labels into rows by y0 (tolerance covers a multi-line label block)
    rows: list[list[tuple[str, dict]]] = []
    for slug, r in sorted(seen.items(), key=lambda m: m[1]["y0"]):
        for row in rows:
            if abs(row[0][1]["y0"] - r["y0"]) <= 60.0:
                row.append((slug, r))
                break
        else:
            rows.append([(slug, r)])
    rows.sort(key=lambda row: min(m[1]["y0"] for m in row))
    out = []
    for ri, row in enumerate(rows):
        row = sorted(row, key=lambda m: m[1]["x0"])
        y_from = min(m[1]["y0"] for m in row)
        y_to = min(m[1]["y0"] for m in rows[ri + 1]) if ri + 1 < len(rows) else H
        for ci, (slug, lab) in enumerate(row):
            x0 = lab["x0"]
            x_end = row[ci + 1][1]["x0"] if ci + 1 < len(row) else W
            sel = [r for r in rects
                   if x0 - 40 <= r["x0"] < x_end - 5
                   and y_from - 10 <= r["y0"] < y_to - 10]
            out.append((slug, x0, x_end, sel))
    return out


# ------------------------------------------------------------------ tip_2 book model

def parse_toc_provinces(pages: list[dict]) -> list[tuple[str, int]]:
    """Parse İÇİNDEKİLER page: [(province_name, start_page), ...]."""
    out = []
    for p in pages[:10]:
        for ln in p["lines"]:
            m = PROVINCE_TOC_RE.search(ln["text"])
            if m:
                out.append((m.group(1).strip(), int(m.group(2))))
    return out


def slugify_tr(s: str) -> str:
    """ASCII slug for Turkish names: 'Şanlıurfa' -> 'sanliurfa'."""
    m = {"ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
         "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u"}
    out = "".join(m.get(ch, ch) for ch in s).lower()
    return re.sub(r"[^a-z0-9]+", "-", out).strip("-")


def tr_upper(s: str) -> str:
    """Turkish-aware upper(): 'ı'->'I' stays dotted-less, 'i'->'İ' keeps the dot.

    Python's str.upper() maps 'ı'->'I' and 'i'->'I', destroying the İ/I
    distinction that Turkish header matching depends on.
    """
    out = []
    for ch in s:
        if ch == "i":
            out.append("İ")
        elif ch == "ı":
            out.append("I")
        elif ch == "İ":
            out.append("İ")
        else:
            out.append(ch.upper())
    return "".join(out)


def detect_subject_header(lines: list[dict]) -> str | None:
    """Detect subject from page header lines like 'Türkçe Soruları'."""
    head = " ".join(l["text"] for l in lines[:5])
    head = tr_upper(head)
    for slug, patterns in SUBJECT_HEADER_RULES:
        for pat in patterns:
            if re.search(pat, head):
                return slug
    return None


def is_key_page(p: dict) -> bool:
    text_up = " ".join(l["text"] for l in p["lines"]).upper()
    return any(m in text_up for m in KEY_MARKERS)


def extract_page(p: dict, slug: str, bucket: dict, prefix: str,
                 trace: list[str], section: str = "EXAM") -> int:
    width_pt, height_pt = p["size"]
    anchors = anchors_of(p["rects"], width_pt, height_pt)
    if not anchors:
        return 0
    head_cut = HEADER_CUT_PT if p["index"] > 6 else 0.0
    specs = crop_specs(p["page"], p["rects"], anchors, width_pt, height_pt, head_cut)
    if not specs:
        return 0
    img = render(p["page"])
    sx = img.width / width_pt
    sy = img.height / height_pt
    out = OUTPUT_DIR / f"tip2-{slug}"
    out.mkdir(parents=True, exist_ok=True)
    tag = prefix
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
            "id": f"STUDY-TIP2-{slug.upper()}-{ident}",
            "file": f"tip2-{slug}/{ident}.png",
            "questionNumber": qn,
            "page": p["index"],
            "column": spec["column"],
            "section": section,
            "examYear": None,
            "unitNo": None,
            "representation": "IMAGE_BACKED",
            "visual": {
                "publicPath": f"/tip2-{slug}/{ident}.png",
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
        return combined[slug]

    for fname in sorted(BOOKS.keys()):
        path = INPUT_DIR / fname
        if not path.exists():
            trace.append(f"MISSING {fname}")
            continue
        src_sha = sha256(path)
        pages = load_book(path)
        n = len(pages)
        trace.append(f"{fname}: {n} pages")

        key_pages = set(p["index"] for p in pages if is_key_page(p))
        toc_provinces = parse_toc_provinces(pages)
        trace.append(f"  toc_provinces={[(name, p) for name, p in toc_provinces]}")
        trace.append(f"  key_pages={sorted(key_pages)}")

        if not toc_provinces:
            trace.append(f"  {fname}: no TOC provinces found; skipping")
            continue

        # Build province sections from TOC page numbers.
        # TOC numbers are relative to the province content (page 1 = first page
        # after the front matter). Find the offset: the first province's printed
        # '1' is the first question page of that province.
        toc_names = [name for name, _pg in toc_provinces]
        toc_printed = [pg for _, pg in toc_provinces]
        # Province title pages look like '<İl>\nÖDM\n8. Sınıf\nÇalışma Soruları'.
        # Find the first such page AFTER the TOC (front matter), matching the
        # first province name, to compute the printed->PDF page offset.
        first_prov_pages = []
        for p in pages:
            if p["index"] <= 7:
                continue
            text_up = " ".join(l["text"] for l in p["lines"]).upper()
            if "ÖDM" in text_up and "8. SINIF" in text_up and "ÇALIŞMA SORULARI" in text_up \
               and toc_names[0].upper() in text_up:
                first_prov_pages.append(p["index"])
                break
        if not first_prov_pages:
            trace.append(f"  {fname}: first province title page not found; skipping")
            continue
        offset = first_prov_pages[0] - toc_printed[0]  # PDF index for printed page 1
        trace.append(f"  offset={offset} (printed {toc_printed[0]} == PDF p{offset + toc_printed[0]})")

        # Province section spans in PDF indices
        starts = [pg + offset for pg in toc_printed]
        ends = starts[1:] + [n + 1]

        for pi, ((prov_name, _pg), prov_start, prov_end) in enumerate(zip(toc_provinces, starts, ends)):
            prov_name = prov_name[:30]
            prov_slug = slugify_tr(prov_name)
            book_tag = fname.replace(".pdf", "")  # e.g. 'cal07'
            # Province title page itself is at prov_start (or prov_start-1);
            # content pages run after it until the next province title.
            prov_pages = [p for p in pages[prov_start - 1:prov_end - 1]
                          if p["index"] not in key_pages and p["index"] != prov_start - 1]

            # Detect subject sections
            current_slug = None
            section_pages = []
            for p in prov_pages:
                hs = detect_subject_header(p["lines"])
                if hs:
                    # Save previous section
                    if current_slug and section_pages:
                        if subjects_filter is None or current_slug in subjects_filter:
                            bucket = bucket_for(current_slug)
                            if fname not in bucket["sources"]:
                                bucket["sources"].append(fname)
                                bucket["shas"][fname] = src_sha
                            tag = f"{book_tag}-{prov_slug}"
                            cnt = 0
                            for sp in section_pages:
                                cnt += extract_page(sp, current_slug, bucket, tag, trace, "PROVINCE")
                            trace.append(f"  {fname} {prov_name} {current_slug}: {cnt} questions")
                    current_slug = hs
                    # The header page ITSELF usually contains the first questions
                    section_pages = [p]
                else:
                    if current_slug:
                        section_pages.append(p)

            # Save last section
            if current_slug and section_pages:
                if subjects_filter is None or current_slug in subjects_filter:
                    bucket = bucket_for(current_slug)
                    if fname not in bucket["sources"]:
                        bucket["sources"].append(fname)
                        bucket["shas"][fname] = src_sha
                    tag = f"p{pi:02d}"
                    cnt = 0
                    for sp in section_pages:
                        cnt += extract_page(sp, current_slug, bucket, tag, trace, "PROVINCE")
                    trace.append(f"  {fname} {prov_name} {current_slug}: {cnt} questions")

            # Answer keys for this province
            prov_key_pages = [k for k in key_pages if prov_start <= k < prov_end]
            for kp in prov_key_pages:
                kpage = pages[kp - 1]
                cols = exam_key_columns(kpage["rects"], kpage["size"])
                if cols:
                    for slug, x0, x_end, sel in cols:
                        if subjects_filter and slug not in subjects_filter:
                            continue
                        pairs = parse_pairs(sel)
                        b = bucket_for(slug)
                        for q, a in pairs.items():
                            b["answers"].setdefault(f"{book_tag}-{prov_slug}-q{q:02d}", a)
                        trace.append(f"  {fname} {prov_name} key p{kp} col {slug}: {len(pairs)} answers")
                else:
                    trace.append(f"  {fname} {prov_name} key p{kp}: no columns found")

    # ---------- outputs ----------
    for slug in SLUGS:
        data = combined.get(slug)
        if not data or not data["questions"]:
            continue
        out = OUTPUT_DIR / f"tip2-{slug}"
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
                "sourceId": f"STUDY-TIP2-{slug.upper()}",
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

    log = REPO / "logs" / "TRACE_TIP2.log"
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
