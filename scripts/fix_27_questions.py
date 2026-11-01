#!/usr/bin/env python3
"""27 bozuk LGS sinav sorusunu kaynak PDF'lerinden yeniden kirpar.

Yontem (lgs-pdf-crop-extraction becerisi - crop correction workflow):
- Soru numarasi ancorasi (N.) ile sorunun penceresi bulunur (kendi ancorasindan
  sonraki sorunun ankorasina kadar, ayni sutunda).
- Pencere icindeki TUM murekkep ogeleri (metin + onemli sekiller) toplanir;
  sayfa cercevesi, ince cizgiler, sayfa numarasi ve uyari satirlari atlanir.
- Sinir = icerik dis kutusu + 20pt (piksel duzeyinde trim + 83px).
- Tam sayfa 300 DPI render edilir, PIL ile kirpilir (pdfium crop= guvensiz).
- Kontroller: kendi numarasi iceride, A-B-C-D isaretleri iceride,
  sonraki sorunun ankorasi DISARIDA (sizma yok), yukseklik > 100pt,
  soru metninin pencere icinde varligi.

Cikti: _fix_27/public/exams/<ay>/<ders>/QNN.png (kurulum ayri adimda).
"""
import json
import os
import re
import sys
import unicodedata

import pdfplumber
import fitz
from PIL import Image

BASE = "/home/selam/roller/web/lgs-ai-coach"
SRC_ROOT = "/home/selam/roller/web/kaynak dosyalar/Lgs_soruları"
STAGING = os.path.join(BASE, "_fix_27")
REPORT_PATH = os.path.join(STAGING, "fix_report.json")

DPI = 300
SCALE = DPI / 72.0
MARGIN_PT = 20.0
MARGIN_PX = int(round(MARGIN_PT * SCALE))  # 83 px @300dpi

ANCHOR_RE = re.compile(r"^[0-9]{1,2}[.]$")
OPTION_MARKS = ("A)", "B)", "C)", "D)")

TARGETS = [
    {"rel": "public/exams/00_seviye_tespit/fen-bilimleri/Q04.png", "id": "MEB-LGS-2016-FEN-BILIMLERI-Q08", "year": "2016", "q": 8, "page": 15, "column": "right"},
    {"rel": "public/exams/02_ay/fen-bilimleri/Q11.png", "id": "MEB-LGS-2026-FEN-Q11", "year": "2026", "q": 11, "page": 11, "column": None},
    {"rel": "public/exams/02_ay/fen-bilimleri/Q12.png", "id": "MEB-LGS-2026-FEN-Q12", "year": "2026", "q": 12, "page": 12, "column": None},
    {"rel": "public/exams/02_ay/turkce/Q17.png", "id": "MEB-LGS-2019-TURKCE-Q07", "year": "2019", "q": 7, "page": 4, "column": "single"},
    {"rel": "public/exams/03_ay/fen-bilimleri/Q06.png", "id": "MEB-LGS-2016-FEN-BILIMLERI-Q07", "year": "2016", "q": 7, "page": 15, "column": "left"},
    {"rel": "public/exams/06_ay/inkilap-tarihi/Q09.png", "id": "MEB-LGS-2017-INKILAP-TARIHI-Q08", "year": "2017", "q": 8, "page": 13, "column": "right"},
    {"rel": "public/exams/06_ay/matematik/Q02.png", "id": "MEB-LGS-2018-MATEMATIK-Q07", "year": "2018", "q": 7, "page": 3, "column": "single"},
    {"rel": "public/exams/06_ay/turkce/Q04.png", "id": "MEB-LGS-2024-TURKCE-Q18", "year": "2024", "q": 18, "page": 10, "column": "left"},
    {"rel": "public/exams/07_ay/fen-bilimleri/Q18.png", "id": "MEB-LGS-2026-FEN-Q01", "year": "2026", "q": 1, "page": 1, "column": None},
    {"rel": "public/exams/07_ay/ingilizce/Q04.png", "id": "MEB-LGS-2022-INGILIZCE-Q09", "year": "2022", "q": 9, "page": 4, "column": "single"},
    {"rel": "public/exams/07_ay/ingilizce/Q05.png", "id": "MEB-LGS-2022-INGILIZCE-Q10", "year": "2022", "q": 10, "page": 4, "column": "single"},
    {"rel": "public/exams/07_ay/turkce/Q08.png", "id": "MEB-LGS-2026-TURKCE-Q20", "year": "2026", "q": 20, "page": 20, "column": None},
    {"rel": "public/exams/08_ay/fen-bilimleri/Q02.png", "id": "MEB-LGS-2026-FEN-Q13", "year": "2026", "q": 13, "page": 13, "column": None},
    {"rel": "public/exams/08_ay/fen-bilimleri/Q05.png", "id": "MEB-LGS-2026-FEN-Q20", "year": "2026", "q": 20, "page": 20, "column": None},
    {"rel": "public/exams/08_ay/ingilizce/Q04.png", "id": "MEB-LGS-2023-INGILIZCE-Q09", "year": "2023", "q": 9, "page": 5, "column": "left"},
    {"rel": "public/exams/08_ay/turkce/Q05.png", "id": "MEB-LGS-2019-TURKCE-Q04", "year": "2019", "q": 4, "page": 2, "column": "single"},
    {"rel": "public/exams/09_ay/din-kulturu/Q06.png", "id": "MEB-LGS-2018-DIN-KULTURU-Q09", "year": "2018", "q": 9, "page": 4, "column": "left"},
    {"rel": "public/exams/09_ay/fen-bilimleri/Q11.png", "id": "MEB-LGS-2026-FEN-Q02", "year": "2026", "q": 2, "page": 2, "column": None},
    {"rel": "public/exams/09_ay/fen-bilimleri/Q12.png", "id": "MEB-LGS-2026-FEN-Q03", "year": "2026", "q": 3, "page": 3, "column": None},
    {"rel": "public/exams/09_ay/turkce/Q01.png", "id": "MEB-LGS-2022-TURKCE-Q15", "year": "2022", "q": 15, "page": 7, "column": "single"},
    {"rel": "public/exams/09_ay/turkce/Q02.png", "id": "MEB-LGS-2022-TURKCE-Q16", "year": "2022", "q": 16, "page": 7, "column": "single"},
    {"rel": "public/exams/09_ay/turkce/Q18.png", "id": "MEB-LGS-2026-TURKCE-Q16", "year": "2026", "q": 16, "page": 16, "column": None},
    {"rel": "public/exams/10_ay/fen-bilimleri/Q07.png", "id": "MEB-LGS-2017-FEN-BILIMLERI-Q18", "year": "2017", "q": 18, "page": 18, "column": "single"},
    {"rel": "public/exams/10_ay/ingilizce/Q08.png", "id": "MEB-LGS-2026-INGILIZCE-Q03", "year": "2026", "q": 3, "page": 3, "column": None},
    {"rel": "public/exams/10_ay/turkce/Q05.png", "id": "MEB-LGS-2017-TURKCE-Q07", "year": "2017", "q": 7, "page": 4, "column": "right"},
    {"rel": "public/exams/11_ay/ingilizce/Q03.png", "id": "MEB-LGS-2026-INGILIZCE-Q08", "year": "2026", "q": 8, "page": 8, "column": None},
    {"rel": "public/exams/11_ay/matematik/Q06.png", "id": "MEB-LGS-2019-MATEMATIK-Q19", "year": "2019", "q": 19, "page": 14, "column": "single"},
]

SUBJ_PDF_NAME = {
    "turkce": ["Türkçe"],
    "matematik": ["Matematik"],
    "fen-bilimleri": ["Fen Bilimleri"],
    "ingilizce": ["İngilizce"],
    "din-kulturu": ["Din Kültürü"],
    "inkilap-tarihi": ["İnkılap Tarihi", "TC İnkılap Tarihi"],
}
YEAR_DIR = {
    "2015": "Lgs_2015", "2016": "lgs_2016", "2017": "lgs_2017",
    "2018": "Lgs_2018", "2019": "Lgs_2019", "2020": "Lgs_2020",
    "2021": "Lgs_2021", "2022": "Lgs_2022", "2023": "Lgs_2023",
    "2024": "Lgs-2024", "2025": "Lgs_2025", "2026": "Lgs_2026",
}

# id -> questionText (tum yil manifestlerinden birikir)
STEMS = {}
STEM_PAGE_SCORES = {}

STOPWORDS = {
    "ve", "ile", "bir", "için", "bu", "şu", "o", "de", "da", "ki",
    "çok", "az", "böyle", "şöyle", "her", "hiç", "sadece", "ancak",
    "fakat", "ama", "veya", "ya", "ise", "di", "mi", "mı", "mu", "mü",
    "the", "and", "or", "of", "to", "in", "a", "an", "is", "are",
    "was", "were", "with", "for", "on", "at", "by", "from", "as",
    "it", "its", "they", "them", "var", "yok", "olan", "olanlar",
}
ARTIFACT_TOKENS = {
    "table", "thead", "tbody", "tr", "td", "th", "colspan", "rowspan",
    "img", "alt", "div", "span", "br", "strong", "em", "nbsp", "mdash",
}


def norm_tr(s):
    s = s.replace("İ", "i").replace("I", "i").replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def stem_tokens(text):
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = norm_tr(t)
    toks = [w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 1]
    return [w for w in toks if w not in ARTIFACT_TOKENS]


def stem_score(stem, page_text_norm):
    toks = stem_tokens(stem)[:18]
    if not toks:
        return 0.0
    page_toks = set(re.findall(r"[a-z0-9]+", page_text_norm))
    hit = sum(1 for t in toks if t in page_toks)
    return hit / len(toks)


def load_stems():
    import glob
    n = 0
    for mp in glob.glob(os.path.join(BASE, "lgs_18_26", "*", "manifest_*.json")):
        try:
            man = json.load(open(mp, encoding="utf-8"))
        except Exception:
            continue
        for q in man.get("questions", []):
            qid = q.get("id")
            qt = q.get("questionText") or q.get("question_text") or ""
            if qid and qt:
                STEMS[qid] = qt
                n += 1
    return n


def find_pdf(year, subject):
    yd = YEAR_DIR[year]
    base_dir = None
    for d in os.listdir(SRC_ROOT):
        if norm_tr(d) == norm_tr(yd):
            base_dir = os.path.join(SRC_ROOT, d)
            break
    if base_dir is None:
        raise FileNotFoundError("yil dizini yok: " + yd)
    y = int(year)
    if y <= 2017 or y == 2026:
        if y == 2026:
            bundle = "sayisal" if subject in ("fen-bilimleri", "matematik") else "sozel"
            cand = "2026" + bundle + ".pdf"
        else:
            bundle = "Sayısal" if subject in ("fen-bilimleri", "matematik") else "Sözel"
            cand = str(year) + " " + bundle + ".pdf"
        for f in os.listdir(base_dir):
            if norm_tr(f) == norm_tr(cand):
                return os.path.join(base_dir, f)
        raise FileNotFoundError(cand + " yok: " + base_dir)
    names = SUBJ_PDF_NAME[subject]
    for n in names:
        for f in os.listdir(base_dir):
            fn = norm_tr(f)
            if fn.endswith(".pdf") and norm_tr(n) in fn and "cevap" not in fn:
                return os.path.join(base_dir, f)
    raise FileNotFoundError(year + " " + subject + " PDF yok: " + base_dir)


def page_items(page):
    """Sayfadaki murekkep ogeleri: metin satirlari + onemli sekiller."""
    items = []
    W = float(page.width)
    H = float(page.height)
    words = page.extract_words() or []
    rects = page.rects or []
    curves = page.curves or []
    images = page.images or []

    for w in words:
        t = w.get("text", "")
        top = float(w["top"])
        if ANCHOR_RE.match(t.strip()) and top < 75:
            continue  # fantom baslik numarasi
        if re.fullmatch(r"[0-9]+", t.strip()) and top > 720:
            continue  # sayfa numarasi
        items.append({
            "kind": "text", "text": t,
            "x0": float(w["x0"]), "x1": float(w["x1"]),
            "top": top, "bottom": float(w["bottom"]),
        })

    by_line = {}
    for it in items:
        key = round(it["top"] / 3.0)
        by_line.setdefault(key, []).append(it)
    for key, group in by_line.items():
        line_text = " ".join(g["text"] for g in group)
        words_norm = [norm_tr(wd) for wd in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", line_text)]
        words_norm = [w for w in words_norm if w]
        if words_norm and all(w in {"diger", "sayfaya", "geciniz", "test", "bitti", "bos",
                                    "birakabilirsiniz", "sinav", "sonlandiriniz", "sayfa"}
                              for w in words_norm):
            for g in group:
                g["skip"] = True
        words_norm2 = [norm_tr(wd) for wd in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", line_text)]
        if words_norm2 and all(w in {"diger", "sayfaya", "geciniz", "test", "bitti", "bos",
                                     "birakabilirsiniz", "sinav", "sonlandiriniz", "sayfa",
                                     "sinifi", "sorulari", "cevaplayiniz"} for w in words_norm2):
            for g in group:
                g["skip"] = True

    def add_shape(bx0, bx1, btop, bbottom):
        w = bx1 - bx0
        h = bbottom - btop
        if w <= 3 or h <= 3:
            return
        if w >= 0.85 * W and h >= 0.5 * H:
            return
        if w < 30 or h < 25:
            return
        items.append({
            "kind": "shape", "text": "",
            "x0": bx0, "x1": bx1, "top": btop, "bottom": bbottom,
        })

    for r in rects:
        add_shape(float(r["x0"]), float(r["x1"]), float(r["top"]), float(r["bottom"]))
    for c in curves:
        add_shape(float(c["x0"]), float(c["x1"]), float(c["top"]), float(c["bottom"]))
    for im in images:
        add_shape(float(im["x0"]), float(im["x1"]), float(im["top"]), float(im["bottom"]))

    return [it for it in items if not it.get("skip")], words


def detect_divider(items, W):
    """Iki sutunlu sayfada sutun ayrigini: SADECE metin kelimelerine gore."""
    text_items = [it for it in items if it["kind"] == "text"]
    if not text_items:
        return None
    mid = W / 2.0
    left_text = [it for it in text_items if it["x0"] < mid]
    right_text = [it for it in text_items if it["x0"] >= mid]
    if not left_text or not right_text:
        return None
    left_max = max(it["x1"] for it in left_text)
    right_min = min(it["x0"] for it in right_text)
    if right_min - left_max < 12:
        return None
    return (left_max + right_min) / 2.0


def window_score(anchor, top1, words, stem_toks):
    """Ancora penceresindeki benzersiz kelime sayisi."""
    top0 = anchor["top"]
    hits = 0
    for w in words:
        t = norm_tr(w.get("text", ""))
        if t in stem_toks and top0 - 2 <= float(w["top"]) < top1:
            hits += 1
    return hits


def extract_target(t):
    pdf_path = find_pdf(t["year"], t["rel"].split("/")[3])
    result = {"rel": t["rel"], "id": t["id"], "pdf": pdf_path, "page": t["page"]}
    stem = STEMS.get(t["id"], "")

    with pdfplumber.open(pdf_path) as pdf:
        # Soru metniyle dogru sayfayi bul (2026 manifest sayfa no'yu yanlis veriyor)
        page_idx = t["page"] - 1
        if stem:
            scores = []
            for i, pg in enumerate(pdf.pages):
                txt = norm_tr(pg.extract_text() or "")
                scores.append((stem_score(stem, txt), i))
            scores.sort(reverse=True)
            best_score, best_idx = scores[0]
            result["stem_page_score"] = round(best_score, 2)
            if best_score > 0.05 and best_idx != page_idx:
                result["page_corrected"] = [t["page"], best_idx + 1]
                page_idx = best_idx
            elif best_score <= 0.05:
                result["error"] = "metin eslesmesi zayif: " + str(round(best_score, 2))
                return result

        if page_idx >= len(pdf.pages):
            result["error"] = "sayfa PDF'te yok"
            return result
        page = pdf.pages[page_idx]
        result["page"] = page_idx + 1
        W, H = float(page.width), float(page.height)
        items, words = page_items(page)

        # ancoralar
        anchors = []
        for w in words:
            tx = w.get("text", "").strip()
            top = float(w["top"])
            if ANCHOR_RE.match(tx) and top >= 75:
                anchors.append({"q": int(tx[:-1]), "x": float(w["x0"]), "top": top})
        anchors.sort(key=lambda a: a["top"])

        divider = detect_divider(items, W)

        # sutun bandi (once band icin divider gerekli)
        band = (0.0, W)
        if divider is not None:
            if t["column"] == "right":
                band = (divider, W)
            elif t["column"] == "left":
                band = (0.0, divider)
            elif t["column"] is None:
                # ipucu yoksa: en cok stem kelimesi iceren tarafi sec
                pass

        # hedef ankorayi bul — ancoralarin penceresinde soru metninin en cok
        # benzersiz kelimesi bulunana kadar ariyoruz (ortak kelimeler sayilmaz)
        cand = [a for a in anchors if a["q"] == t["q"]]
        if not cand:
            result["error"] = "ancora bulunamadi: q=" + str(t["q"])
            result["anchors_on_page"] = [a["q"] for a in anchors]
            return result

        stem_toks = set(stem_tokens(stem)) - STOPWORDS
        stems_in_windows = []
        for a in cand:
            if band[0] <= a["x"] < band[1] or t["column"] is None:
                later = [aa for aa in anchors
                         if aa["top"] > a["top"] + 6 and band[0] <= aa["x"] < band[1]]
                top1 = min([aa["top"] for aa in later], default=float("inf"))
                hits = window_score(a, top1, words, stem_toks)
                stems_in_windows.append((hits, a["top"], a))
        if not stems_in_windows:
            stems_in_windows = [(0, a["top"], a) for a in cand]
        stems_in_windows.sort(key=lambda z: (-z[0], z[1]))
        anchor = stems_in_windows[0][2]
        if stems_in_windows[0][0] == 0:
            result["anchor_warning"] = "stem kelimesi pencerede bulunamadi"

        if divider is not None and t["column"] is None:
            band = (divider, W) if anchor["x"] >= divider else (0.0, divider)

        # bir sonraki ankor (ayni sutunda)
        later = [a for a in anchors if a["top"] > anchor["top"] + 6 and band[0] <= a["x"] < band[1]]
        next_anchor = min(later, key=lambda a: a["top"]) if later else None

        # oge atama: anchor penceresi [anchor.top - 6, next_anchor.top)
        own = []
        for it in items:
            cx = (it["x0"] + it["x1"]) / 2.0
            if not (band[0] <= cx < band[1]):
                continue
            cy = (it["top"] + it["bottom"]) / 2.0
            if next_anchor and cy >= next_anchor["top"]:
                continue
            if cy >= anchor["top"] - 6:
                own.append(it)

        if not own:
            result["error"] = "kendi ogeleri bulunamadi"
            return result

        # sinirlar: icerik dis kutusu + 20pt
        x0 = min(it["x0"] for it in own) - MARGIN_PT
        x1 = max(it["x1"] for it in own) + MARGIN_PT
        y0 = max(70.0, min(it["top"] for it in own) - MARGIN_PT)
        y1 = max(it["bottom"] for it in own) + MARGIN_PT

        # alt uyari cap'i
        for it in items:
            if it["kind"] == "text" and it["top"] > y1 - MARGIN_PT:
                if is_warning_line(it["text"]):
                    y1 = min(y1, it["top"] - 2)
        # sonraki ankor cap'i (sizma onleme)
        if next_anchor and next_anchor["top"] < y1:
            y1 = next_anchor["top"] - 2

        # sutun yan cap'lari
        if divider is not None:
            all_left = all(it["x1"] <= divider for it in own)
            all_right = all(it["x0"] >= divider for it in own)
            if all_left:
                x1 = min(x1, divider - 3)
            elif all_right:
                x0 = max(x0, divider + 4)
            else:
                x0 = max(x0, 20.0)
                x1 = min(x1, W - 20.0)
        else:
            x0 = max(x0, 10.0)
            x1 = min(x1, W - 10.0)
        y1 = min(y1, H - 5.0)

        # ---- kontroller ----
        opt_text = set()
        opt_shape = 0
        for it in own:
            if it["kind"] == "text":
                tx = it["text"].strip()
                for m in OPTION_MARKS:
                    if tx == m or tx.startswith(m + " ") or tx.startswith(m + "\t"):
                        opt_text.add(m)
            else:
                if 20 <= (it["bottom"] - it["top"]) <= 120 and (it["x1"] - it["x0"]) <= 160:
                    opt_shape += 1
        own_numbers = [it for it in own if it["kind"] == "text" and ANCHOR_RE.match(it["text"].strip())]
        own_norm = norm_tr(" ".join(it["text"] for it in own if it["kind"] == "text"))
        result["check"] = {
            "own_number_in": any(abs(it["top"] - anchor["top"]) < 3 for it in own_numbers),
            "options_text": sorted(opt_text),
            "option_like_shapes": opt_shape,
            "next_anchor_leak": bool(next_anchor and y1 > next_anchor["top"]),
            "stem_match": round(stem_score(stem, own_norm), 2) if stem else None,
        }

        # ---- render + kirp ----
        doc = fitz.open(pdf_path)
        pg = doc[page_idx]
        pix = pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()

        box = (
            int(round(x0 * SCALE)), int(round(y0 * SCALE)),
            int(round(x1 * SCALE)), int(round(y1 * SCALE)),
        )
        box = (max(0, box[0]), max(0, box[1]), min(img.width, box[2]), min(img.height, box[3]))
        crop = img.crop(box)
        crop = trim_ink(crop)

        out_rel = t["rel"]
        out_path = os.path.join(STAGING, out_rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        crop.save(out_path)
        result["out"] = out_path
        result["new_clip"] = {"x0": round(x0, 1), "y0": round(y0, 1), "x1": round(x1, 1), "y1": round(y1, 1)}
        result["size"] = [crop.width, crop.height]
        result["height_pt"] = round(crop.height / SCALE, 1)
        return result


def is_warning_line(text):
    words = [norm_tr(w) for w in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", text)]
    words = [w for w in words if w]
    if not words:
        return False
    return all(w in {"diger", "sayfaya", "geciniz", "test", "bitti", "bos",
                     "birakabilirsiniz", "sinav", "sonlandiriniz", "sayfa"} for w in words)


def trim_ink(img):
    """Murekkep satir/sutunlarini bul, 83px (20pt) marjla yeniden kirp.
    Tam genislikte ince cizgiler (kural/cizgi satirlari) yoksayilir."""
    gray = img.convert("L")
    w, h = gray.size
    px = gray.load()
    step = 2
    rows = []
    for y in range(0, h, step):
        dark = 0
        for x in range(0, w, 4):
            if px[x, y] < 248:
                dark += 1
        rows.append((y, dark))
    cols = []
    for x in range(0, w, step):
        dark = 0
        for y in range(0, h, 4):
            if px[x, y] < 248:
                dark += 1
        cols.append((x, dark))

    def ink_bound(seq, stepv):
        inked = [p for p, c in seq if c > 0 and c * 4 < 0.9 * stepv]
        if not inked:
            inked = [p for p, c in seq if c > 0]
        if not inked:
            return 0, (seq[-1][0] if seq else 0)
        return min(inked), max(inked)

    ry0, ry1 = ink_bound(rows, w)
    rx0, rx1 = ink_bound(cols, h)
    ry1 += step
    rx1 += step
    box = (
        max(0, rx0 - MARGIN_PX),
        max(0, ry0 - MARGIN_PX),
        min(w, rx1 + MARGIN_PX),
        min(h, ry1 + MARGIN_PX),
    )
    return img.crop(box)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(STAGING, exist_ok=True)
    n = load_stems()
    print("yuklenen soru metni:", n, flush=True)
    report = []
    for t in TARGETS:
        if only and only not in t["rel"]:
            continue
        try:
            r = extract_target(t)
        except Exception as e:
            r = {"rel": t["rel"], "id": t["id"], "error": repr(e)[:300]}
        report.append(r)
        status = r.get("error") or json.dumps(r.get("check", {}), ensure_ascii=False)
        print(t["rel"], "->", status, flush=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    ok = sum(1 for r in report if not r.get("error"))
    print("TAMAM:", ok, "/", len(report), "->", REPORT_PATH)


if __name__ == "__main__":
    main()