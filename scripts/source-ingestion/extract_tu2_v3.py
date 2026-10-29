#!/usr/bin/env python3
"""tu2_turkce_2023.pdf — column-aware extractor v3.

v3 fixes the defect where graph/table options laid out in a 2x2 grid (and shared
full-width stimuli) were cut off: only A) and C) appeared, B) and D) were lost.

MEASURED LAYOUT
  * Divider at x≈297.6 (tall narrow vertical band). Left col x∈[20,292], right x∈[304,575].
  * Real anchors sit AT a column margin: left x0∈[24,38], right x0∈[304,322].
    In-question numbered lists are indented (x0≈60 / ≈341) and are NOT anchors.
    Page number: pure digits at y0>770, x≈290.
  * Content vertical range 36..770. No running header (so a y0>90 filter is WRONG).
  * Reading order: left column top→bottom, then right column top→bottom.
  * Question numbers restart at 1 after each 'TEST-N' header.

THREE PAGE SHAPES (all handled):
  1. plain two-column        -> crop the question's own column
  2. shared full-width stim  -> stitch(full-width stimulus, own column)
     e.g. p62 "10 ve 11. soruları aşağıdaki bilgilere göre cevaplayınız"
  3. question body spans the divider (2x2 option grid, wide tables)
     -> single full-width crop
     e.g. p130 GÖRSEL OKUMA graph question with A)B) on one row, C)D) below

VALIDATION (both must hold):
  * per (topic, TEST-N) extracted count == answer-key count  (582 == 582)
  * option completeness: every question whose crop region contains at least two of
    A)/B)/C)/D) must contain ALL FOUR  (catches the cut-off-options defect)
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/tip_1/tu2_turkce_2023.pdf")
OUT_DIR = Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce")

DPI = 300
SCALE = DPI / 72.0
MARGIN_PT = 20.0
DIVIDER_DEFAULT = 297.6
TOP_CUT = 36.0
BOTTOM_CUT = 770.0
GAP = 6.0
ROW_GROUP_TOL = 15.0
FW_MIN_WIDTH = 100.0
FW_CROSS_PAD = 15.0

STANDALONE = re.compile(r"^(\d{1,3})\.$")
PAGENUM = re.compile(r"^\d{1,3}$")
TEST_HDR = re.compile(r"^TEST-?\s*(\d{1,2})$", re.IGNORECASE)
OPT_MARK = re.compile(r"^([A-D])\)")

LEFT_MARGIN = (24, 38)
RIGHT_MARGIN = (304, 322)

TOPICS = [
    ("SÖZCÜKTE ANLAM", 7, 20),
    ("SÖZ GRUPLARINDA ANLAM (Kalıplaşmamış Söz Grupları)", 21, 26),
    ("DEYİM VE ATASÖZÜ", 27, 34),
    ("SÖZ SANATLARI", 35, 44),
    ("CÜMLEDE ANLAM", 45, 58),
    ("PARÇADA ANLAM (Ana Düşünce - Ana Duygu - Yardımcı Düşünce - Konu - Başlık)", 59, 98),
    ("PARÇADA ANLAM (Hikâye Unsurları - Metnin Dil ve Anlatım Özellikleri)", 99, 108),
    ("PARÇADA ANLAM (Parça Oluşturma - Parça Tamamlama)", 109, 114),
    ("PARÇADA ANLAM (Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları)", 115, 122),
    ("SÖZEL MANTIK / MUHAKEME", 123, 128),
    ("GÖRSEL OKUMA (Tablo / Grafik / Çizelge)", 129, 150),
    ("FİİLİMSİLER", 151, 160),
    ("CÜMLENİN ÖGELERİ", 161, 168),
    ("YAZIM KURALLARI", 169, 176),
    ("NOKTALAMA İŞARETLERİ", 177, 186),
    ("METİN TÜRLERİ", 187, 191),
]
ANSWER_PAGES = list(range(191, 196))


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
                        "y0": H - float(t), "y1": H - float(b),
                        "text": txt.strip()})
    out.sort(key=lambda r: (r["y0"], r["x0"]))
    return out


def is_pagenum(r):
    return bool(PAGENUM.fullmatch(r["text"])) and r["y0"] > 770


def detect_divider(page, W, H):
    best = None
    for obj in page.get_objects():
        if obj.type not in (2, 3):
            continue
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:
            continue
        x0, y0, x1, y1 = float(l), H - float(t), float(r), H - float(b)
        w, h = x1 - x0, y1 - y0
        if w > 20 or h < 0.3 * H:
            continue
        if best is None or h > best[1]:
            best = ((x0 + x1) / 2, h)
    return best[0] if best else DIVIDER_DEFAULT


def column_of(x0):
    if LEFT_MARGIN[0] <= x0 <= LEFT_MARGIN[1]:
        return "L"
    if RIGHT_MARGIN[0] <= x0 <= RIGHT_MARGIN[1]:
        return "R"
    return None


def merge_intervals(ivs):
    ivs = sorted(ivs)
    out = []
    for a, b in ivs:
        if out and a <= out[-1][1] + 2:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def render_page(page):
    return page.render(scale=SCALE).to_pil()


def crop_pt(img, x0, y0, x1, y1):
    box = (max(0, int(x0 * SCALE)), max(0, int(y0 * SCALE)),
           min(img.width, int(x1 * SCALE)), min(img.height, int(y1 * SCALE)))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return img.crop(box)


def stitch(crops):
    crops = [c for c in crops if c is not None]
    if not crops:
        return None
    if len(crops) == 1:
        return crops[0]
    w = max(c.width for c in crops)
    h = sum(c.height for c in crops) + 8 * (len(crops) - 1)
    out = Image.new("RGB", (w, h), "white")
    y = 0
    for c in crops:
        out.paste(c, (0, y))
        y += c.height + 8
    return out


def scan_document(doc):
    pages = {}
    for p in range(len(doc)):
        page = doc[p]
        W, H = page.get_size()
        rects = [r for r in page_rects(page) if not is_pagenum(r)]
        body = [r for r in rects if TOP_CUT < r["y0"] < BOTTOM_CUT]
        divider = detect_divider(page, W, H)

        anchors, headers, fw = [], [], []
        for r in body:
            m = STANDALONE.fullmatch(r["text"])
            if m:
                c = column_of(r["x0"])
                if c:
                    anchors.append({"n": int(m.group(1)), "col": c,
                                    "y": r["y0"], "x0": r["x0"]})
                    continue
            mh = TEST_HDR.fullmatch(r["text"])
            if mh:
                headers.append({"test": int(mh.group(1)),
                                "col": column_of(r["x0"]) or "L", "y": r["y0"]})
                continue
            # full-width content: wide rect crossing the divider
            if (r["x1"] - r["x0"]) > FW_MIN_WIDTH \
               and r["x0"] < divider - FW_CROSS_PAD and r["x1"] > divider + FW_CROSS_PAD:
                fw.append((r["y0"], r["y1"]))
        cb = {}
        for c, lo, hi in (("L", 0, divider), ("R", divider, W)):
            ys = [r["y1"] for r in body if lo <= r["x0"] < hi]
            cb[c] = max(ys) if ys else BOTTOM_CUT
        pages[p + 1] = {"anchors": anchors, "headers": headers, "cb": cb,
                        "fw": merge_intervals(fw), "divider": divider,
                        "W": W, "H": H, "body": body}
    return pages


def topic_for_page(pnum):
    for name, start, end in TOPICS:
        if start <= pnum <= end:
            return name
    return None


def build_questions(doc, pages):
    questions = []
    cur_topic = None
    cur_test = None
    seen_seq = {}
    for pnum in range(1, len(doc) + 1):
        topic = topic_for_page(pnum)
        if topic is None:
            continue
        ct = canonical_topic(topic)
        if ct != cur_topic:
            cur_topic = ct
            cur_test = None
            seen_seq = {}
        info = pages[pnum]
        col_order = {"L": 0, "R": 1}
        events = ([("hdr", h) for h in info["headers"]] +
                  [("anc", a) for a in info["anchors"]])
        events.sort(key=lambda e: (col_order[e[1]["col"]], e[1]["y"]))
        for kind, e in events:
            if kind == "hdr":
                cur_test = e["test"]
                seen_seq[cur_test] = 0
            else:
                if cur_test is None:
                    cur_test = 1
                    seen_seq.setdefault(cur_test, 0)
                seen_seq[cur_test] += 1
                questions.append({
                    "topic": cur_topic, "topicFull": topic, "test": cur_test,
                    "q_in_test": e["n"], "seq_in_test": seen_seq[cur_test],
                    "page": pnum, "col": e["col"], "y": e["y"],
                })
    return questions


def canonical_topic(s: str) -> str:
    u = s.upper().replace("İ", "I").replace("İ", "I")
    u = re.sub(r"\s+", " ", u).strip()
    if u.startswith("SÖZCÜKTE ANLAM"):
        return "SÖZCÜKTE ANLAM"
    if u.startswith("SÖZ GRUPLARINDA"):
        return "SÖZ GRUPLARINDA ANLAM"
    if u.startswith("DEYIM") or u.startswith("DEYİM"):
        return "DEYİM VE ATASÖZÜ"
    if u.startswith("SÖZ SANATLARI"):
        return "SÖZ SANATLARI"
    if u.startswith("CÜMLEDE ANLAM"):
        return "CÜMLEDE ANLAM"
    if u.startswith("PARÇADA ANLAM") or u.startswith("("):
        if "HIK" in u or "HİK" in u:
            return "PARÇADA ANLAM (HİKÂYE)"
        if "PARÇA OLUŞTURMA" in u or "PARCA OLUSTURMA" in u:
            return "PARÇADA ANLAM (PARÇA OLUŞTURMA)"
        if "ANLATIM BIÇIMLERI" in u or "ANLATIM BİÇİMLERİ" in u:
            return "PARÇADA ANLAM (ANLATIM BİÇİMLERİ)"
        return "PARÇADA ANLAM (ANA DÜŞÜNCE)"
    if u.startswith("SÖZEL MANTIK"):
        return "SÖZEL MANTIK / MUHAKEME"
    if u.startswith("GÖRSEL OKUMA") or u.startswith("GORSEL OKUMA") or "TABLO / GRAFIK" in u:
        return "GÖRSEL OKUMA"
    if u.startswith("FİİLİMSİ") or u.startswith("FIILIMSI"):
        return "FİİLİMSİLER"
    if u.startswith("CÜMLENIN ÖGELERI") or u.startswith("CÜMLENİN ÖGELERİ"):
        return "CÜMLENİN ÖGELERİ"
    if u.startswith("YAZIM"):
        return "YAZIM KURALLARI"
    if u.startswith("NOKTALAMA"):
        return "NOKTALAMA İŞARETLERİ"
    if u.startswith("METIN") or u.startswith("METİN"):
        return "METİN TÜRLERİ"
    return u


def parse_answer_keys(doc):
    parts = []
    for pi in ANSWER_PAGES:
        if pi >= len(doc):
            continue
        tp = doc[pi].get_textpage()
        parts.append(tp.get_text_range(0, tp.count_chars()))
    text = "\n".join(parts)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    cur_topic = cur_test = pending = None
    out = {}
    for line in lines:
        if line.upper().startswith("CEVAP ANAHTARI") or re.fullmatch(r"\d{1,3}", line):
            continue
        mh = TEST_HDR.fullmatch(line)
        if mh:
            cur_test = int(mh.group(1))
            continue
        pairs = re.findall(r"(\d{1,3})\.\s*([A-E])", line)
        if pairs:
            if cur_topic and cur_test:
                for qn, letter in pairs:
                    out[(cur_topic, cur_test, int(qn))] = letter
            continue
        if line.startswith("(") and pending:
            pending = f"{pending} {line}"
            cur_topic = canonical_topic(pending)
            cur_test = None
            continue
        pending = line
        cur_topic = canonical_topic(line)
        cur_test = None
    return out


def group_by_row(anchors):
    """Group anchors whose y are within ROW_GROUP_TOL; return list of (y, [anchors])."""
    ordered = sorted(anchors, key=lambda a: (a["y"], a["x0"]))
    groups = []
    for a in ordered:
        if groups and abs(a["y"] - groups[-1][0]) <= ROW_GROUP_TOL:
            groups[-1][1].append(a)
        else:
            groups.append((a["y"], [a]))
    return groups


def plan_crop(q, info):
    """Return list of (x0, y0, x1, y1) rects to render+stitch for this question."""
    W = info["W"]
    divider = info["divider"]
    col = q["col"]
    cx0, cx1 = (MARGIN_PT, divider - GAP) if col == "L" else (divider + GAP, W - MARGIN_PT)

    same_col = sorted([a for a in info["anchors"] if a["col"] == col], key=lambda a: a["y"])
    nxt = next((a for a in same_col if a["y"] > q["y"] + 1), None)
    own_y0 = max(TOP_CUT, q["y"] - GAP)
    own_y1 = (nxt["y"] - GAP) if nxt else min(info["cb"][col] + 8, BOTTOM_CUT)
    if own_y1 <= own_y0:
        own_y1 = min(own_y0 + 40, BOTTOM_CUT)

    fw = info["fw"]
    own_crossing = any(s <= own_y1 and e >= own_y0 for s, e in fw)

    # stimulus preceding this question's row group
    groups = group_by_row(info["anchors"])
    gidx = next((i for i, (gy, g) in enumerate(groups)
                 if any(a is q for a in g)), None)
    prev_y = TOP_CUT
    if gidx is not None and gidx > 0:
        prev_y = groups[gidx - 1][0]
    stims = [(s, e) for s, e in fw if s >= prev_y - 5 and e <= q["y"] + 5]

    if own_crossing:
        return [(MARGIN_PT, own_y0, W - MARGIN_PT, own_y1)], "fullwidth"
    if stims:
        s0 = min(s for s, _ in stims) - GAP
        s1 = max(e for _, e in stims) + 8
        s0 = max(TOP_CUT, s0)
        return [(MARGIN_PT, s0, W - MARGIN_PT, s1),
                (cx0, own_y0, cx1, own_y1)], "stitch"
    return [(cx0, own_y0, cx1, own_y1)], "column"


def option_markers_in(info, x0, y0, x1, y1):
    found = set()
    for r in info["body"]:
        if r["x0"] >= x0 - 1 and r["x1"] <= x1 + 1 and r["y0"] >= y0 - 1 and r["y1"] <= y1 + 1:
            m = OPT_MARK.match(r["text"])
            if m:
                found.add(m.group(1))
    return found


def main():
    doc = pdfium.PdfDocument(SRC)
    pages = scan_document(doc)
    questions = build_questions(doc, pages)
    answers = parse_answer_keys(doc)

    print(f"PDF: {len(doc)} pages")
    print(f"Bulunan anchor: {len(questions)}   Cevap anahtarı: {len(answers)}")

    expected = {}
    for (t, te, q) in answers:
        expected[(t, te)] = expected.get((t, te), 0) + 1
    found = {}
    for q in questions:
        found[(q["topic"], q["test"])] = found.get((q["topic"], q["test"]), 0) + 1
    mism = [(k, expected.get(k, 0), found.get(k, 0))
            for k in sorted(set(expected) | set(found), key=lambda k: (k[0], k[1]))
            if expected.get(k, 0) != found.get(k, 0)]
    print(f"\nTest bazında uyuşmazlık: {len(mism)}")
    for k, e, f in mism:
        print(f"  {k[0][:36]:36s} TEST-{k[1]:<2} beklenen={e} bulunan={f}")
    print(f"Toplam beklenen={sum(expected.values())} bulunan={sum(found.values())}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_questions = []
    incomplete = []
    qid = 0
    for q in questions:
        pnum = q["page"]
        info = pages[pnum]
        page = doc[pnum - 1]
        rects, mode = plan_crop(q, info)

        # option completeness check on the planned region(s)
        markers = set()
        for (x0, y0, x1, y1) in rects:
            markers |= option_markers_in(info, x0, y0, x1, y1)

        img = render_page(page)
        crops = [crop_pt(img, *r) for r in rects]
        crop = stitch(crops)
        if crop is None:
            continue
        qid += 1
        ans = answers.get((q["topic"], q["test"], q["q_in_test"]), "")
        fname = f"TU2-TURKCE-Q{qid:04d}.png"
        crop.save(OUT_DIR / fname, format="PNG", dpi=(DPI, DPI))

        if len(markers) in (2, 3):
            incomplete.append((fname, sorted(markers)))

        out_questions.append({
            "id": f"TU2-TURKCE-Q{qid:04d}",
            "topic": q["topic"], "topicFull": q.get("topicFull"),
            "test": q["test"], "q_in_test": q["q_in_test"],
            "page": pnum, "column": q["col"], "cropMode": mode,
            "file": fname,
            "visual": {"publicPath": f"/turkce/{fname}"},
            "clipRectsPt": [{"x0": round(x0, 1), "y0": round(y0, 1),
                             "x1": round(x1, 1), "y1": round(y1, 1)} for (x0, y0, x1, y1) in rects],
            "renderDpi": DPI, "representation": "IMAGE_BACKED",
            "answer": ans, "answerSource": "UNIT_KEY" if ans else "NEEDS_REVIEW",
            "status": "NEEDS_REVIEW", "published": False,
            "examYear": 2023, "sourceBook": "tu2_turkce_2023",
        })

    modes = {}
    for q in out_questions:
        modes[q["cropMode"]] = modes.get(q["cropMode"], 0) + 1
    print(f"\nKırpılan: {len(out_questions)}  mod dağılımı: {modes}")
    print(f"Şık bütünlüğü şüpheli (2-3 şık): {len(incomplete)}")
    for f, m in incomplete[:15]:
        print(f"   {f} -> {m}")

    manifest = {
        "book": "tu2_turkce_2023", "subject": "turkce",
        "source": str(SRC), "source_sha256": sha256(SRC), "year": 2023,
        "layout": {"columns": 2, "divider_x_pt": DIVIDER_DEFAULT,
                   "left_margin_pt": MARGIN_PT, "top_cut_pt": TOP_CUT,
                   "bottom_cut_pt": BOTTOM_CUT},
        "questions": out_questions,
        "summary": {"questionsExtracted": len(out_questions),
                    "answersMatched": sum(1 for q in out_questions if q["answer"]),
                    "expectedFromKey": sum(expected.values()),
                    "testMismatches": len(mism),
                    "optionIncomplete": len(incomplete),
                    "cropModes": modes},
    }
    (OUT_DIR / "manifest_tu2.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ans_dump = {f"{k[0]}|TEST-{k[1]}|{k[2]}": v for k, v in answers.items()}
    (OUT_DIR / "answers_tu2.json").write_text(
        json.dumps(ans_dump, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nManifest: {OUT_DIR / 'manifest_tu2.json'}")
    return 0 if (not mism and not incomplete) else 1


if __name__ == "__main__":
    sys.exit(main())