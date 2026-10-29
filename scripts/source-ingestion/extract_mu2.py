#!/usr/bin/env python3
"""mu2 extractor — Matematik Çalışma Kitabı (MEB, 194 sayfa, 6 ünite).

mu2 farklılıkları:
  - Merkezî Sınav bölümü YOK (sadece 6 ünite + cevap anahtarı)
  - İki sütunlu sayfalar (divider ~297.6 pt)
  - Cevap anahtarı sayfa 188-189'da, ünite bazlı
  - Soru numaraları ünite içinde artıyor (1'den başlayıp ünite sonuna kadar)
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/üniteli/mu2.pdf")
OUT_ROOT = Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları")
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
MAX_QNUM = 200
DIVIDER_X = 297.6  # İki sütunlu sayfaların divider konumu

QRE = re.compile(r"^(\d{1,3})[.)]$")
NUM_ONLY = re.compile(r"^\d{1,3}$")
UNIT_HDR_TXT = re.compile(r"^(\d)\.?\s*(?:Ünite|Tema)\s*$")
PAIR_TXT = re.compile(r"(\d{1,3})\s+([A-D])(?:\s|$)")
KEY_MARK = "CEVAP ANAHTARI"


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
            band = [i for i in ln if (rects[i]["x0"] < W / 2) == (half == 0)]
            if band:
                leftmost.add(min(band, key=lambda i: rects[i]["x0"]))
    return leftmost


def anchors(rects, W, H, col):
    lm = leftmost_per_line(rects, W=W)
    out = []
    for idx, r in enumerate(rects):
        if idx not in lm:
            continue
        m = QRE.fullmatch(r["text"])
        if not m:
            continue
        n = int(m.group(1))
        if not 1 <= n <= MAX_QNUM or r["y0"] > H - FOOTER_PT:
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


def filter_sequential(anch):
    out = []
    last = 0
    for a in anch:
        if last >= 3 and a["num"] * 2 < last:
            continue
        out.append(a)
        last = max(last, a["num"])
    return out


def crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                anch, col, col_left, col_right, book):
    if not anch:
        return []
    bounds = [a["y0"] for a in anch] + [H - FOOTER_PT]
    recs = []
    for i, a in enumerate(anch):
        y_from, y_next = bounds[i], bounds[i + 1]
        y_end = (row_top(rects, y_next) - LINE_TOL
                 if i + 1 < len(anch) else H - FOOTER_PT)
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
        fp = outdir / f"{book}_p{page_index:03d}_q{a['num']:02d}.png"
        img.crop(box).save(fp, "PNG")
        recs.append({"file": fp.name, "page": page_index, "q": a["num"],
                     "column": col,
                     "clipRectPt": [round(l, 1), round(top, 1), round(r, 1), round(bot, 1)]})
    return recs


def crop_page(page, page_index, outdir, book):
    W, H = page.get_size()
    rects = drop_page_numbers(page_rects(page), W, H)
    shapes = significant_shapes(page, W, H)
    left = filter_sequential(anchors(rects, W, H, "left"))
    right = filter_sequential(anchors(rects, W, H, "right"))
    if left and right:
        right = [a for a in right if a["num"] > left[-1]["num"]]
    if not left and not right:
        return []
    img = page.render(scale=DPI / 72).to_pil().convert("RGB")
    sx, sy = img.width / W, img.height / H
    if right and left:
        recs = crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                           left, "left", LEFT_KEEP_PT, W / 2, book)
        recs += crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                            right, "right", W / 2, W - RIGHT_KEEP_PT, book)
        return recs
    return crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                       left or right, "single", LEFT_KEEP_PT, W - RIGHT_KEEP_PT, book)


def parse_unit_key_text(pages_text):
    """Unit keys from page TEXT: blocks headed 'N. Ünite', then 'k.L' pairs.

    mu2 cevap anahtarı formatı (iki sütunlu sayfa):
    - Sayfa 188 sol: 1. ünite (1-40) + 2. ünite (41-77)
    - Sayfa 188 sağ: 3. ünite (1-30) + 4. ünite (31-59)
    - Sayfa 189 sol: 5. ünite (41-71) + 6. ünite (21-50)
    """
    import pdfplumber
    out = {}
    unit = 1
    out.setdefault(unit, {})
    for text in pages_text:
        for line in text.split("\n"):
            line = line.strip()
            mh = UNIT_HDR_TXT.match(line)
            if mh:
                n = int(mh.group(1))
                if n == 1:
                    unit = 2
                elif n == 2:
                    unit = 3
                elif n == 3:
                    unit = 3
                elif n >= 4:
                    unit = n
                out.setdefault(unit, {})
                continue
            if unit is None:
                continue
            for num, letter in PAIR_TXT.findall(line):
                out[unit][int(num)] = letter
    return out


def parse_unit_key_pdfplumber(pdf_path, key_pages):
    """Parse answer keys using pdfplumber table extraction.

    mu2 cevap anahtarı: 6 tablo, her tablo bir ünite.
    Tablonun başındaki hücrede ünite numarası var: '1 Ünite', '2 Ünite', ...
    Her tablo kendi ünitesine karşılık gelir (sayfa sırası).
    """
    import pdfplumber
    import re
    out = {}
    with pdfplumber.open(pdf_path) as pdf:
        for pno in key_pages:
            page = pdf.pages[pno - 1]
            tables = page.extract_tables()
            for table in tables:
                if not table or not table[0]:
                    continue
                # Tablonun başındaki ünite numarasını bul
                unit = None
                for row in table:
                    if row and row[0] and row[0].strip():
                        mh = re.match(r'^(\d)\.?\s*(?:Ünite|Tema)\b', row[0].strip())
                        if mh:
                            unit = int(mh.group(1))
                            break
                if unit is None:
                    continue
                out.setdefault(unit, {})
                # Tablodaki tüm cevapları satır satır oku
                for row in table:
                    for cell in row:
                        if not cell:
                            continue
                        cell = cell.strip()
                        m = re.match(r'^(\d{1,3})\s+([A-D])$', cell)
                        if m:
                            out[unit][int(m.group(1))] = m.group(2)
    return out


def find_toc_page(doc, limit=20):
    for pno in range(min(limit, len(doc))):
        if "İÇİNDEKİLER" in doc[pno].get_textpage().get_text_range().upper():
            return pno + 1
    raise SystemExit("İÇİNDEKİLER bulunamadı")


def build_sections(doc):
    """Return (unit_bounds, unit_key_pages) derived from the TOC.

    mu2: 6 ünite, Merkezî Sınav YOK.
    """
    toc_pno = find_toc_page(doc)
    toc = doc[toc_pno - 1].get_textpage().get_text_range()
    unit_starts, key_pages = {}, []
    for line in toc.split("\n"):
        line = line.strip()
        mu = re.match(r"^(\d)\.\s*(?:Ünite|Tema)\s*:?\s*(.+?)[\s.]*(\d+)$", line)
        if mu:
            unit_starts[int(mu.group(1))] = (mu.group(2).strip().rstrip("."), int(mu.group(3)))
        mk = re.match(r"^Cevap Anahtarı[\s.]*(\d+)$", line, re.IGNORECASE)
        if mk:
            key_pages.append(int(mk.group(1)))
    if not unit_starts:
        raise SystemExit("TOC okunamadı (ünite satırları yok)")
    ordered = sorted(unit_starts.items())
    # TOC sayfa numaraları "basılı sayfa" numaralarıdır; PDF sayfa numarası = basılı + 1
    key_pdf = min(key_pages) + 1 if key_pages else ordered[-1][1][1] + 1
    unit_key_pages = list(range(key_pdf, key_pdf + 2))  # 188-189
    unit_bounds = []
    for i, (un, (name, start)) in enumerate(ordered):
        start_pdf = start + 1
        end = ordered[i + 1][1][1] + 1 if i + 1 < len(ordered) else key_pdf
        unit_bounds.append((un, name, start_pdf, end))
    return unit_bounds, unit_key_pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="mu2")
    ap.add_argument("--subject", default="matematik")
    ap.add_argument("--subject-name", default="Matematik")
    ap.add_argument("--page-start", type=int, default=0)
    ap.add_argument("--page-end", type=int, default=0)
    ap.add_argument("--limit-pages", type=int, default=0)
    args = ap.parse_args()

    src = SRC
    out = OUT_ROOT / args.subject
    out.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(src))
    n = len(doc)

    unit_bounds, unit_key_pages = build_sections(doc)
    first_unit = min(s for _, _, s, _ in unit_bounds)
    p_start = args.page_start or first_unit
    p_end = args.page_end or n
    if args.limit_pages:
        p_end = min(p_end, p_start + args.limit_pages - 1)
    trace = [f"book={args.book} pages={n} units={unit_bounds} unitKeyPages={unit_key_pages}"]

    # ---- crop ----
    records = []
    for pno in range(p_start, min(p_end, n) + 1):
        page = doc[pno - 1]
        head = page.get_textpage().get_text_range()[:400].upper()
        if KEY_MARK in head or "İÇİNDEKİLER" in head:
            continue
        recs = crop_page(page, pno, out, args.book)
        sec, unit = None, None
        for un, _nm, s, e in unit_bounds:
            if s <= pno < e:
                sec, unit = "UNIT", un
                break
        for r in recs:
            r["section"], r["unit"] = sec, unit
            records.append(r)
        if recs:
            trace.append(f"p{pno}: {len(recs)} soru sec={sec} unit={unit}")

    # ---- answer keys ----
    unit_key = parse_unit_key_pdfplumber(src, unit_key_pages)
    doc.close()

    # ---- match ----
    matched = unmatched = 0
    for r in records:
        ans = None
        if r["section"] == "UNIT" and r["unit"] in unit_key:
            ans = unit_key[r["unit"]].get(r["q"])
        r["answer"] = ans
        r["answerSource"] = "UNIT_KEY" if ans else None
        r["status"] = "NEEDS_REVIEW"
        matched += 1 if ans else 0
        unmatched += 0 if ans else 1

    # ---- outputs ----
    records.sort(key=lambda r: (r["section"] or "", r["unit"] or 0, r["page"], r["q"]))
    answers = {f'{r["section"]}:{r["unit"]}:q{r["q"]:02d}': r["answer"]
               for r in records if r["answer"]}
    (out / f"answers_{args.book}.json").write_text(
        json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "manifestVersion": "1.0", "status": "NEEDS_REVIEW", "published": False,
        "method": "mu2-v1",
        "render": {"dpi": DPI, "margin_pt": MARGIN_PT, "bbox": "text UNION significant shapes"},
        "source": {"sourceId": f"STUDY-{args.book.upper()}-{args.subject.upper()}",
                   "pdf": f"{args.book}.pdf", "sha256": sha256(src),
                   "subject": args.subject_name or args.subject, "grade": 8},
        "units": [{"unit": u, "name": nm, "start": s, "end": e}
                  for u, nm, s, e in unit_bounds],
        "unitKeyPages": unit_key_pages,
        "summary": {"questions": len(records), "answersMatched": matched,
                    "answersUnmatched": unmatched},
        "questions": records,
    }
    (out / f"manifest_{args.book}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log = Path(f"/home/selam/roller/web/lgs-ai-coach/logs/TRACE_{args.book.upper()}.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(trace) + "\n", encoding="utf-8")

    print(json.dumps({"questions": len(records), "matched": matched,
                      "unmatched": unmatched, "out": str(out)}, ensure_ascii=False))
    print("unit keys: " + ", ".join(f"u{u}={len(v)}" for u, v in sorted(unit_key.items())))


if __name__ == "__main__":
    sys.exit(main())
