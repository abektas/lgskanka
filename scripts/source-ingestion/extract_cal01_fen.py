#!/usr/bin/env python3
"""cal01.pdf (Fen Bilimleri) — full extractor: crop + answer-key match + save.

Book model (verified):
  p1-6   front matter; p6 = İÇİNDEKİLER
  p7-305 7 ünite (each starts with a 'N. Ünite' title page, questions 1..K)
  p306-308 ÜNİTE CEVAP ANAHTARI (blocks '1. Ünite' .. '7. Ünite', rows 'k.L k.L')
  p309-402 7 Merkezî Sınav sections (2018-2019 … 2024-2025), each 20 questions,
           each followed by a CEVAP ANAHTARI page (vertical '1. C' style)

Crop calibration = the v9 shape-aware recipe (see
skill lgs-pdf-crop-extraction/references/fen-single-subject-workbook.md).

Output: <OUT>/<file>.png + manifest.json + answers.json
  file name = cal01_p<page>_q<num>.png
  each record carries section (UNIT/EXAM), unit/year, page, question, answer.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
OUT = Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/fen")
DPI = 300
MARGIN_PT = 14.0
FOOTER_PT = 60.0
ROW_TOL = 5.0
LINE_TOL = 0.5
LEFT_KEEP_PT = 12.0
RIGHT_KEEP_PT = 12.0
PAGENUM_ZONE_PT = 70.0
LOGO_ZONE_PT = 95.0
FRAME_FRAC = 0.85
MIN_SHAPE_W = 30.0
MIN_SHAPE_H = 25.0

QRE = re.compile(r"^(\d{1,3})[.)]$")
NUM_ONLY = re.compile(r"^\d{1,3}$")
PAIR_FUSED = re.compile(r"^(\d{1,2})\.\s*([A-D])$")
UNIT_HDR = re.compile(r"^(\d)\.\s*Ünite$", re.IGNORECASE)
EXAM_COVER = re.compile(r"(\d{4})-(\d{4})\s+Merkezî\s+Sınav", re.IGNORECASE)
EXAM_KEY_MARK = "CEVAP ANAHTARI"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def page_rects(page):
    tp = page.get_textpage()
    H = page.get_size()[1]
    out = []
    for i in range(tp.count_rects()):
        l, b, r, t = tp.get_rect(i)
        txt = tp.get_text_bounded(l, b, r, t)
        if txt and txt.strip():
            out.append({"x0": float(l), "x1": float(r),
                        "y0": H - float(t), "y1": H - float(b), "text": txt.strip()})
    out.sort(key=lambda r: (r["y0"], r["x0"]))
    return out


def significant_shapes(page, W, H):
    out = []
    for obj in page.get_objects():
        if obj.type not in (2, 3):
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        x0, y0, x1, y1 = float(l), H - float(t), float(r), H - float(b)
        w, h = x1 - x0, y1 - y0
        if w < MIN_SHAPE_W or h < MIN_SHAPE_H:
            continue
        if w > FRAME_FRAC * W and h > FRAME_FRAC * H:
            continue
        if y1 < LOGO_ZONE_PT and x1 < LOGO_ZONE_PT:
            continue
        if y0 > H - LOGO_ZONE_PT and x0 > W - LOGO_ZONE_PT:
            continue
        out.append((x0, y0, x1, y1))
    return out


def drop_page_numbers(rects, W, H):
    return [r for r in rects
            if not (r["y0"] > H - PAGENUM_ZONE_PT and NUM_ONLY.fullmatch(r["text"])
                    and 0.35 * W < r["x0"] < 0.65 * W)]


def leftmost_per_line(rects, tol=4.0, W=None):
    """Leftmost rect of each text line, evaluated PER COLUMN when W is given.

    On two-column pages a left-column number and a right-column number share a
    baseline; treating them as one line drops the right number (it is not the
    leftmost). Split each line band by the page centre so each column's own
    leftmost run survives.
    """
    lines: list[list[int]] = []
    for idx, r in enumerate(rects):
        for ln in lines:
            if abs(rects[ln[0]]["y0"] - r["y0"]) <= tol:
                ln.append(idx)
                break
        else:
            lines.append([idx])
    leftmost = set()
    for ln in lines:
        if W is None:
            leftmost.add(min(ln, key=lambda i: rects[i]["x0"]))
            continue
        for half in (0, 1):
            band = [i for i in ln
                    if (rects[i]["x0"] < W / 2) == (half == 0)]
            if band:
                leftmost.add(min(band, key=lambda i: rects[i]["x0"]))
    return leftmost


def anchors(rects, W, H, col):
    """Question-number anchors in one column ('left' or 'right').

    A real question number is followed by stem text on the SAME line (to its
    right). A figure/axis label ('1.', '2.' inside a diagram) has no such text,
    so requiring a right neighbour on the same baseline drops those.
    """
    lm = leftmost_per_line(rects, W=W)
    out = []
    for idx, r in enumerate(rects):
        if idx not in lm:
            continue
        m = QRE.fullmatch(r["text"])
        if not m:
            continue
        n = int(m.group(1))
        if not 1 <= n <= 130 or r["y0"] > H - FOOTER_PT:
            continue
        x0 = r["x0"]
        if col == "left" and x0 > 60.0:
            continue
        if col == "right" and not (W / 2 - 10.0 <= x0 <= W / 2 + 60.0):
            continue
        out.append({"num": n, "y0": r["y0"], "x0": x0})
    out.sort(key=lambda a: a["y0"])
    return out


def row_top(rects, anchor_y):
    band = [r["y0"] for r in rects if abs(r["y0"] - anchor_y) <= ROW_TOL]
    return min(band) if band else anchor_y


def crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                anch, col, col_left, col_right):
    """Crop every question of one column. Returns list of records."""
    if not anch:
        return []
    bounds = [a["y0"] for a in anch] + [H - FOOTER_PT]
    recs = []
    for i, a in enumerate(anch):
        y_from, y_next = bounds[i], bounds[i + 1]
        y_end = (row_top(rects, y_next) - LINE_TOL
                 if i + 1 < len(anch) else H - FOOTER_PT)
        # text: within the column's x-band and the question's y-window
        sel = [r for r in rects if y_from - 1.0 <= r["y0"] < y_end
               and col_left <= r["x0"] and r["x1"] <= col_right]
        own = [s for s in shapes if y_from <= (s[1] + s[3]) / 2 < y_next
               and col_left - 5 <= s[0] and s[2] <= col_right + 5]
        if not sel and not own:
            continue
        xs0 = [r["x0"] for r in sel] + [s[0] for s in own] + [a["x0"]]
        ys0 = [r["y0"] for r in sel] + [s[1] for s in own]
        xs1 = [r["x1"] for r in sel] + [s[2] for s in own]
        ys1 = [r["y1"] for r in sel] + [s[3] for s in own]
        top = max(0.0, min(min(ys0), a["y0"]) - MARGIN_PT)
        bot = min(max(ys1) + MARGIN_PT, y_end)
        l = max(col_left, min(min(xs0), a["x0"]) - MARGIN_PT)
        r = min(col_right, max(xs1) + MARGIN_PT)
        if bot <= top or r <= l:
            continue
        box = (round(l * sx), round(top * sy), round(r * sx), round(bot * sy))
        fp = outdir / f"cal01_p{page_index:03d}_q{a['num']:02d}.png"
        img.crop(box).save(fp, "PNG")
        recs.append({"file": fp.name, "page": page_index, "q": a["num"],
                     "column": col,
                     "clipRectPt": [round(l, 1), round(top, 1), round(r, 1), round(bot, 1)]})
    return recs


def filter_sequential(anch):
    """Drop only clear out-of-order figure labels, keep the rest.

    Figure labels inside a question ('1. Aşama', '2. Aşama') are much SMALLER
    than the question they sit in, so a label that is less than half the running
    maximum is a figure label and is dropped. Everything else is kept — real
    question numbers can jump (a question split across columns) and must not be
    filtered by a strict +1 rule.
    """
    out = []
    last = 0
    for a in anch:
        if last >= 3 and a["num"] * 2 < last:
            continue            # a small label inside a later question
        out.append(a)
        last = max(last, a["num"])
    return out


def crop_page(page, page_index, outdir, trace, expected_start=1):
    """Crop every question on one page (single- or two-column). Returns records."""
    W, H = page.get_size()
    rects = drop_page_numbers(page_rects(page), W, H)
    shapes = significant_shapes(page, W, H)
    left = filter_sequential(anchors(rects, W, H, "left"))
    right = filter_sequential(anchors(rects, W, H, "right"))
    # A right column is only real if its numbers CONTINUE the left column
    # (e.g. left 1..7, right 8..14). A right 'anchor' smaller than the left
    # column's last number is a figure label inside the left question, not a
    # question of its own — drop it.
    if left and right:
        right = [a for a in right if a["num"] > left[-1]["num"]]
    if not left and not right:
        return []
    img = page.render(scale=DPI / 72).to_pil().convert("RGB")
    sx, sy = img.width / W, img.height / H
    # two columns when the right half has at least one anchor; otherwise single
    if right and left:
        recs = crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                           left, "left", LEFT_KEEP_PT, W / 2)
        recs += crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                            right, "right", W / 2, W - RIGHT_KEEP_PT)
        return recs
    return crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                       left or right, "single", LEFT_KEEP_PT, W - RIGHT_KEEP_PT)


# --------------------------------------------------------------- answer parsing

UNIT_HDR_TXT = re.compile(r"^(\d)\.\s*Ünite\s*$")
PAIR_TXT = re.compile(r"(\d{1,3})\.\s*([A-D])")


def parse_unit_key_text(pages_text):
    """Unit keys from the page TEXT: blocks headed 'N. Ünite', then 'k.L' pairs.

    Text is far more reliable than rect geometry here — the heading shares a
    baseline with its first answer row, and the 10-column grid plus the left
    'Ünite' label defeat label-anchored blocking. The extracted text already
    renders each block as 'N. Ünite' on its own line followed by '1.C 2.A ...'.
    """
    out = {}
    unit = None
    for text in pages_text:
        for line in text.split("\n"):
            line = line.strip()
            mh = UNIT_HDR_TXT.match(line)
            if mh:
                unit = int(mh.group(1))
                out.setdefault(unit, {})
                continue
            if unit is None:
                continue
            for num, letter in PAIR_TXT.findall(line):
                out[unit][int(num)] = letter
    return out


IPTAL_TXT = re.compile(r"(\d{1,2})\.\s*(?:İPTAL|IPTAL)", re.IGNORECASE)


def parse_exam_key_text(text):
    """Exam key page: text renders '1. C' / '2. D' lines (SAYISAL BÖLÜM style).

    'N. İPTAL' rows mean the question was cancelled in the official exam —
    collect them separately so the matcher can flag those records instead of
    silently leaving them answerless.
    """
    pairs = {}
    for num, letter in re.findall(r"(\d{1,2})\.\s*([A-D])", text):
        pairs[int(num)] = letter
    cancelled = {int(n) for n in IPTAL_TXT.findall(text)}
    return pairs, cancelled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-start", type=int, default=7)
    ap.add_argument("--page-end", type=int, default=0, help="0 = last page")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    src_sha = sha256(SRC)
    doc = pdfium.PdfDocument(str(SRC))
    n = len(doc)
    p_end = args.page_end or n
    trace = []

    # ---- 1. build section map from İÇİNDEKİLER (p6) ----
    toc = doc[5].get_textpage().get_text_range()
    unit_starts, exam_secs = {}, []
    for line in toc.split("\n"):
        line = line.strip()
        mu = re.match(r"^(\d)\.\s*Ünite:\s*(.+?)\s+(\d+)$", line)
        if mu:
            unit_starts[int(mu.group(1))] = (mu.group(2).strip(), int(mu.group(3)))
        me = re.match(r"^(\d{4})-(\d{4})\s+Merkezî\s+Sınav.*?\s(\d+)$", line)
        if me:
            exam_secs.append((f"{me.group(1)}-{me.group(2)}", int(me.group(3))))
    trace.append(f"TOC units={unit_starts}")
    trace.append(f"TOC exams={exam_secs}")

    # section boundaries: unit i spans [start_i, start_{i+1}); last unit ends at key page
    unit_bounds = []
    ordered = sorted(unit_starts.items())
    for i, (un, (name, start)) in enumerate(ordered):
        end = ordered[i + 1][1][1] if i + 1 < len(ordered) else 306
        unit_bounds.append((un, name, start, end))

    # ---- 2. crop pages ----
    records = []
    for pno in range(args.page_start, min(p_end, n) + 1):
        page = doc[pno - 1]
        txt_up = page.get_textpage().get_text_range()[:400].upper()
        if EXAM_KEY_MARK in txt_up or "İÇİNDEKİLER" in txt_up:
            continue
        recs = crop_page(page, pno, OUT, trace)
        # classify the page
        sec, unit, year = None, None, None
        for un, name, s, e in unit_bounds:
            if s <= pno < e:
                sec, unit = "UNIT", un
                break
        if sec is None:
            for yi, (yr, s) in enumerate(exam_secs):
                e = exam_secs[yi + 1][1] if yi + 1 < len(exam_secs) else 403
                if s <= pno < e:
                    sec, year = "EXAM", yr
                    break
        for r in recs:
            r["section"] = sec
            r["unit"] = unit
            r["examYear"] = year
            records.append(r)
        trace.append(f"p{pno}: {len(recs)} soru  sec={sec} unit={unit} year={year}")

    # ---- 3. parse answer keys ----
    # Unit keys on p306-308, read from page TEXT (geometry is unreliable here).
    unit_pages_text = [doc[kp - 1].get_textpage().get_text_range() for kp in (306, 307, 308)]
    unit_key = parse_unit_key_text(unit_pages_text)
    exam_key, exam_cancelled = {}, {}
    for yi, (yr, s) in enumerate(exam_secs):
        # key page is the page before the next section starts (or 403)
        nxt = exam_secs[yi + 1][1] if yi + 1 < len(exam_secs) else 403
        kp = None
        for cand in range(nxt - 1, s, -1):
            t = doc[cand - 1].get_textpage().get_text_range()[:200].upper()
            if EXAM_KEY_MARK in t:
                kp = cand
                break
        if kp:
            pairs, cancelled = parse_exam_key_text(doc[kp - 1].get_textpage().get_text_range())
            exam_key[yr] = pairs
            exam_cancelled[yr] = cancelled
            trace.append(f"exam key {yr}: p{kp} -> {len(pairs)} cevap, {len(cancelled)} iptal")
    trace.append(f"unit keys: " + ", ".join(f"u{u}={len(v)}" for u, v in sorted(unit_key.items())))

    # ---- 4. match answers ----
    matched, unmatched = 0, 0
    for r in records:
        ans = None
        if r["section"] == "UNIT" and r["unit"] in unit_key:
            ans = unit_key[r["unit"]].get(r["q"])
        elif r["section"] == "EXAM" and r["examYear"] in exam_key:
            ans = exam_key[r["examYear"]].get(r["q"])
        r["answer"] = ans
        r["answerSource"] = ("UNIT_KEY" if r["section"] == "UNIT" else "EXAM_KEY") if ans else None
        r["status"] = "NEEDS_REVIEW"
        if (r["section"] == "EXAM" and r["q"] in exam_cancelled.get(r["examYear"], set())):
            r["cancelledInSource"] = True
            r["sourceNote"] = (
                f"cal01.pdf cevap anahtari: '{r['q']}. IPTAL' — soru resmi sinavda iptal edilmis; "
                "ogrenciye sunulmaz.")
            trace.append(f"IPITAL: {r['file']} ({r['examYear']} q{r['q']})")
        if ans:
            matched += 1
        else:
            unmatched += 1

    doc.close()

    # ---- 5. write outputs ----
    records.sort(key=lambda r: (r["section"], r["unit"] or 0, r["examYear"] or "", r["page"], r["q"]))
    answers = {f'{r["section"]}:{r["unit"] or r["examYear"]}:q{r["q"]:02d}': r["answer"]
               for r in records if r["answer"]}
    (OUT / "answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "manifestVersion": "1.0", "status": "NEEDS_REVIEW", "published": False,
        "method": "v9-shape-aware",
        "render": {"dpi": DPI, "margin_pt": MARGIN_PT, "bbox": "text UNION significant shapes"},
        "source": {"sourceId": "STUDY-CAL01-FEN", "pdf": "cal01.pdf", "sha256": src_sha,
                   "subject": "Fen Bilimleri", "grade": 8},
        "units": [{"unit": u, "name": nm, "start": s, "end": e} for u, nm, s, e in unit_bounds],
        "examSections": [{"year": y, "start": s} for y, s in exam_secs],
        "summary": {"questions": len(records), "answersMatched": matched,
                    "answersUnmatched": unmatched},
        "questions": records,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log = Path("/home/selam/roller/web/lgs-ai-coach/logs/TRACE_CAL01_FEN.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(trace) + "\n", encoding="utf-8")

    print(json.dumps({"questions": len(records), "matched": matched,
                      "unmatched": unmatched, "out": str(OUT)}, ensure_ascii=False))
    print(f"unit keys: " + ", ".join(f"u{u}={len(v)}" for u, v in sorted(unit_key.items())))
    print(f"exam keys: " + ", ".join(f"{y}={len(v)}" for y, v in sorted(exam_key.items())))


if __name__ == "__main__":
    sys.exit(main())
