#!/usr/bin/env python3
"""
2015 LGS Extractor v2 — içeriğe dayalı (content-bbox) kırpma.
Nüli QBANK kuralları:
  - Anchor: soru numarası "N." (N<=20), NÜKTEDAN SONRAKİ boşluk da sayılır.
  - Pencere: anchor_top-20 .. sonraki_anchor_top-20 (aynı sütun/sayfa).
  - İçerik bbox: penceredeki TÜM sözcükler + önemli çizimler (path/image >=30x25).
  - Kırpma = içerik bbox + 20 pt DÖRT YANDAN. Sabit offset YOK.
  - Alt sınır: D şıkkı + tablo dahil; uyarı satırı ("geçiniz"/"bitti") tavan yapar.
  - Üst sınır: talimat bloğu / üstteki soru; şıklar anchor ÜSTÜNDEyse (N.'den önce
    gelen şerit) pencere onları da kapsar.
"""
import json, hashlib, re, sys
from pathlib import Path
import fitz
from PIL import Image
import pdfplumber

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")
OUTPUT_DIR = REPO / "lgs_18_26"
DPI = 300
MARGIN = 20.0
PAGE_W, PAGE_H = 552.756, 779.528
COL_CENTER = PAGE_W / 2

# Ders -> (pdf, sayfa başlangıcı, sayfa bitişi, soru sayısı)
SUBJECTS = [
    ("turkce",          "2015 Sözel.pdf",  3, 10, 20),
    ("inkilap-tarihi",  "2015 Sözel.pdf", 11, 14, 10),
    ("din-kulturu",     "2015 Sözel.pdf", 15, 17, 10),
    ("ingilizce",       "2015 Sözel.pdf", 18, 22, 10),
    ("matematik",       "2015 Sayısal.pdf", 3, 11, 20),
    ("fen-bilimleri",   "2015 Sayısal.pdf", 12, 21, 20),
]

QNUM_RE = re.compile(r"^\s*(\d{1,2})\.\s*$")  # "N." veya "N. "
OPTION_RE = re.compile(r"^\s*([A-E])\)\s*$")
WARN_WORDS = {"geçiniz", "geçiniz.", "bitti", "bitti.", "testi", "testine", "test"}

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()

def parse_answer_key():
    """Cevap anahtarı: sayfa1=4 sütun (turkce,inkilap,din,ingilizce), sayfa2=2 sütun (mat,fen)."""
    ak = {s: {} for s in ["turkce","inkilap-tarihi","din-kulturu","ingilizce","matematik","fen-bilimleri"]}
    cfg = {
        0: [("turkce",50,140),("inkilap-tarihi",165,245),("din-kulturu",285,365),("ingilizce",405,490)],
        1: [("matematik",145,225),("fen-bilimleri",340,420)],
    }
    with pdfplumber.open(INPUT_DIR / "2015 Cevap Anahtarı.pdf") as pdf:
        for pi, page in enumerate(pdf.pages):
            words = page.extract_words() or []
            rows = {}
            for w in words:
                rows.setdefault(round(float(w["top"])), []).append(w)
            for top in sorted(rows):
                ws = sorted(rows[top], key=lambda w: float(w["x0"]))
                for subj, xmin, xmax in cfg.get(pi, []):
                    cw = [w for w in ws if xmin <= float(w["x0"]) <= xmax]
                    for i, w in enumerate(cw):
                        m = re.match(r"^(\d{1,2})\.$", str(w.get("text","")).strip())
                        if m and i+1 < len(cw):
                            let = str(cw[i+1].get("text","")).strip().upper()
                            if let in "ABCDE" and len(let) == 1:
                                ak[subj][int(m.group(1))] = let
    return ak

def anchor_words(page):
    """Soru numarası adayları: N. kalıbı, ama başlıktaki '7.' ve satır içi rakamlar elenir."""
    out = []
    for w in page.extract_words() or []:
        t = str(w.get("text", ""))
        m = QNUM_RE.match(t)
        if not m:
            continue
        x0, top = float(w["x0"]), float(w["top"])
        if top < 75:  # başlık "7. DENEME"
            continue
        # Sol sütun x0<=100, sağ sütun x0≈283±25; ama satır içi (x0>=52 sol, >=310 sağ) ele
        left_ok = 25 <= x0 <= 50
        right_ok = 270 <= x0 <= 300
        if not (left_ok or right_ok):
            continue
        out.append({"n": int(m.group(1)), "x0": x0, "top": top,
                    "col": "L" if left_ok else "R", "bot": float(w["bottom"])})
    return out

def content_bbox(page, y0, y1, x_lo, x_hi):
    """[y0,y1]x[x_lo,x_hi] penceresindeki içerik bbox'ı (sözcük + önemli çizim)."""
    xs0, ys0, xs1, ys1 = 1e9, 1e9, -1e9, -1e9
    for w in page.extract_words() or []:
        wx0, wx1 = float(w["x0"]), float(w["x1"])
        wt, wb = float(w["top"]), float(w["bottom"])
        if wb < y0 or wt > y1 or wx1 < x_lo or wx0 > x_hi:
            continue
        xs0, ys0 = min(xs0, wx0), min(ys0, wt)
        xs1, ys1 = max(xs1, wx1), max(ys1, wb)
    for objs in (page.lines, page.rects, page.curves, page.images):
        for o in objs or []:
            b = o if isinstance(o, dict) else {}
            try:
                ox0, oy0, ox1, oy1 = float(b.get("x0",0)), float(b.get("top",b.get("y0",0))), float(b.get("x1",0)), float(b.get("bottom",b.get("y1",0)))
            except Exception:
                continue
            w_, h_ = ox1-ox0, oy1-oy0
            if w_ < 30 or h_ < 25:  # küçük süslemeler elenir
                continue
            if oy1 < y0 or oy0 > y1 or ox1 < x_lo or ox0 > x_hi:
                continue
            # sayfa çerçevesi elenir
            if w_ > PAGE_W*0.92 and h_ > PAGE_H*0.92:
                continue
            xs0, ys0 = min(xs0, ox0), min(ys0, oy0)
            xs1, ys1 = max(xs1, ox1), max(ys1, oy1)
    if xs1 < xs0:
        return None
    return (xs0, ys0, xs1, ys1)

def extract_subject(pdf_path, slug, p_start, p_end, expected, ak):
    questions = []
    done = set()
    with pdfplumber.open(pdf_path) as pdf:
        doc = fitz.open(str(pdf_path))
        for pidx in range(p_start-1, min(p_end, len(pdf.pages))):
            page = pdf.pages[pidx]
            pn = pidx + 1
            anchors = [a for a in anchor_words(page) if a["n"] not in done and 1 <= a["n"] <= expected]
            if not anchors:
                continue
            # Sütun grupları
            L = sorted([a for a in anchors if a["col"]=="L"], key=lambda a: a["top"])
            R = sorted([a for a in anchors if a["col"]=="R"], key=lambda a: a["top"])
            # Uyarı satırları alt sınır
            warn_tops = []
            for w in page.extract_words() or []:
                t = str(w.get("text","")).strip().lower().rstrip(".")
                if t in WARN_WORDS and float(w["top"]) > 700:
                    warn_tops.append(float(w["top"]))
            page_cap = (min(warn_tops) - 2) if warn_tops else PAGE_H - 15

            groups = []
            if L: groups.append(("L", L, 12.0, COL_CENTER - 2))
            if R: groups.append(("R", R, COL_CENTER + 2, PAGE_W - 12))

            for col, alist, x_lo, x_hi in groups:
                for i, a in enumerate(alist):
                    if a["n"] in done:
                        continue
                    nxt = alist[i+1]["top"] if i+1 < len(alist) else None
                    win_top = a["top"] - MARGIN
                    win_bot = (nxt - 4) if nxt else page_cap
                    bb = content_bbox(page, win_top, win_bot, x_lo, x_hi)
                    if not bb:
                        continue
                    cx0, cy0, cx1, cy1 = bb
                    # D ŞIKKI + tablo: içerik bbox'ı zaten kapsıyor; ama pencere
                    # dar kesilmişse (D altta) dikey uzatma yap:
                    if nxt is None:
                        cy1 = max(cy1, min(page_cap, cy1 + 80))
                    y0 = max(0.0, cy0 - MARGIN)
                    y1 = min(page_cap, cy1 + MARGIN)
                    x0 = max(0.0, cx0 - MARGIN)
                    x1 = min(PAGE_W, cx1 + MARGIN)
                    if y1 - y0 < 40:
                        continue
                    pg = doc[pidx]
                    mat = fitz.Matrix(DPI/72, DPI/72)
                    pix = pg.get_pixmap(matrix=mat)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    sx, sy = img.width/PAGE_W, img.height/PAGE_H
                    box = (round(x0*sx), round(y0*sy), round(x1*sx), round(y1*sy))
                    crop = img.crop(box)
                    out = OUTPUT_DIR / slug / f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}.png"
                    crop.save(out, "PNG")
                    ans = ak.get(slug, {}).get(a["n"])
                    (OUTPUT_DIR / slug / f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}.answer.txt").write_text(ans or "")
                    print(f"  Q{a['n']:02d} p{pn}{col} h={y1-y0:.0f}pt box=({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})")
                    questions.append({
                        "id": f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}",
                        "questionNumber": a["n"], "page": pn, "column": col,
                        "representation": "IMAGE_BACKED",
                        "file": f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}.png",
                        "visual": {
                            "publicPath": f"/exams/2015-{slug}-q{a['n']:02d}.png",
                            "clipRectPt": {"x0": round(x0,1), "y0": round(y0,1), "x1": round(x1,1), "y1": round(y1,1)},
                            "renderDpi": DPI, "authority": "ORIGINAL_MEB_PDF",
                            "reconstructedFromOcr": False, "assetSha256": sha256(out),
                        },
                        "answer": ans, "status": "NEEDS_REVIEW", "published": True, "subject": slug,
                    })
                    done.add(a["n"])
        doc.close()
    return questions

def main():
    ak = parse_answer_key()
    for s, v in ak.items():
        print(f"cevap {s}: {len(v)}/{20 if s in ('turkce','matematik','fen-bilimleri') else 10}")
    all_q = {}
    for slug, pdfn, ps, pe, exp in SUBJECTS:
        print(f"\n=== {slug} ===")
        (OUTPUT_DIR/slug).mkdir(parents=True, exist_ok=True)
        qs = extract_subject(INPUT_DIR/pdfn, slug, ps, pe, exp, ak)
        all_q[slug] = qs
        man = {"manifestVersion":"1.0","status":"NEEDS_REVIEW","published":True,
               "source":{"sourceId":"2015-DENEME","sourceType":"MEB_EXAM","subject":slug,"period":"2014-2015"},
               "questions":qs,
               "answerKeyCandidates":{str(q["questionNumber"]):q["answer"] for q in qs if q["answer"]},
               "summary":{"questionsExtracted":len(qs),"expectedQuestions":exp}}
        (OUTPUT_DIR/slug/"manifest_2015.json").write_text(json.dumps(man, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(f"  -> {len(qs)}/{exp} soru, cevap {sum(1 for q in qs if q['answer'])}/{len(qs)}")
    # public/exams kopyalama
    import shutil
    dst = REPO/"public"/"exams"; dst.mkdir(parents=True, exist_ok=True)
    for slug, qs in all_q.items():
        for q in qs:
            src = OUTPUT_DIR/slug/f"MEB-LGS-2015-{slug.upper()}-Q{q['questionNumber']:02d}.png"
            if src.exists():
                shutil.copy2(src, dst/f"2015-{slug}-q{q['questionNumber']:02d}.png")
    print("\nTamamlandı.")

if __name__ == "__main__":
    main()