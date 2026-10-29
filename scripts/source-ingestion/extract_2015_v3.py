#!/usr/bin/env python3
"""
2015 LGS Extractor v3 — içerik-atama (nearest-anchor) tabanlı kırpma.
Nüli QBANK kriterleri:
  - Anchor: soru numarası "N." (sayfa üstü >=75, sol x0∈[25,50], sağ x0∈[270,300]).
    Başlıktaki "7. DENEME", tablo numaraları, şekil etiketleri otomatik elenir.
  - HER içerik öğesi (sözcük + >=30x25 çizim) en yakın üstteki anchor'a atanır:
      * sol bölge öğesi -> en yakın SOL anchor
      * sağ bölge öğesi -> en yakın SAĞ anchor
      * iki bölgeyi de kapsayan öğe (D şeridi, tam genişlik şekil) -> en yakın anchor
  - Kırpma = atanan içerik bbox + 20pt DÖRT YANDAN (soru numarası, kök, şekiller,
    tablo ve A-D şıkları dahil). Sabit sayfa/sütun offset'i YOK.
  - Çarpışma tavanları: sonraki anchor, uyarı satırı ("geçiniz"/"bitti").
"""
import json, hashlib, re, sys
from pathlib import Path
import fitz
from PIL import Image
import pdfplumber

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/Lgs_2015")
OUTPUT_DIR = REPO / "lgs_18_26"
DPI = 300
MARGIN = 20.0
PAGE_W, PAGE_H = 552.756, 779.528
COL = PAGE_W / 2

SUBJECTS = [
    ("turkce",         "2015 Sözel.pdf",   3, 10, 20),
    ("inkilap-tarihi", "2015 Sözel.pdf",  11, 14, 10),
    ("din-kulturu",    "2015 Sözel.pdf",  15, 17, 10),
    ("ingilizce",      "2015 Sözel.pdf",  18, 22, 10),
    ("matematik",      "2015 Sayısal.pdf", 3, 11, 20),
    ("fen-bilimleri",  "2015 Sayısal.pdf", 12, 21, 20),
]

QNUM_RE = re.compile(r"^\s*(\d{1,2})\.\s*$")
OPT_RE = re.compile(r"^\s*([A-D])\)\s*$")
WARN = {"geçiniz", "geçiniz.", "bitti", "bitti.", "testi", "testine", "test", "testi."}

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(1 << 20):
            h.update(c)
    return h.hexdigest()

def parse_answer_key():
    ak = {s: {} for s in ["turkce","inkilap-tarihi","din-kulturu","ingilizce","matematik","fen-bilimleri"]}
    cfg = {0: [("turkce",50,140),("inkilap-tarihi",165,245),("din-kulturu",285,365),("ingilizce",405,490)],
           1: [("matematik",145,225),("fen-bilimleri",340,420)]}
    with pdfplumber.open(INPUT_DIR / "2015 Cevap Anahtarı.pdf") as pdf:
        for pi, page in enumerate(pdf.pages):
            rows = {}
            for w in page.extract_words() or []:
                rows.setdefault(round(float(w["top"])), []).append(w)
            for ws in rows.values():
                ws.sort(key=lambda w: float(w["x0"]))
                for subj, xmin, xmax in cfg.get(pi, []):
                    cw = [w for w in ws if xmin <= float(w["x0"]) <= xmax]
                    for i, w in enumerate(cw):
                        m = re.match(r"^(\d{1,2})\.$", str(w.get("text","")).strip())
                        if m and i+1 < len(cw):
                            let = str(cw[i+1].get("text","")).strip().upper()
                            if let in "ABCDE" and len(let) == 1:
                                ak[subj][int(m.group(1))] = let
    return ak

def norm_tr(t):
    """Türkçe İ/I tuzağı: 'TESTİ'.lower() 'testi̇' verir; birleşik noktayı temizle."""
    return (t.replace("\u0130", "i").replace("\u0131", "i")
             .replace("I", "i").replace("İ", "i")).lower()

def ink_shrink(img, sc, x0, top, x1, bot):
    """Cizim bbox'unun GERCEK murekkep sinirina daralt (gorunmeyen bbox sismesi
    tuzağı). Gorunmeyen cizim icin None doner."""
    W, H = img.size
    box = (max(0, int(x0 * sc)), max(0, int(top * sc)),
           min(W, int(x1 * sc) + 1), min(H, int(bot * sc) + 1))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    reg = img.crop(box).convert("L")
    bb = reg.point(lambda v: 255 if v < 248 else 0).getbbox()
    if bb is None:
        return None
    return ((box[0] + bb[0]) / sc, (box[1] + bb[1]) / sc,
            (box[0] + bb[2]) / sc, (box[1] + bb[3]) / sc)

def trim_ink(img, bx0, by0, bx1, by1):
    """Piksel duzeyinde 20pt kurali. Icerik = item bbox ±4pt icindeki gercek
    murekkep; kunye/cerceve/sayfa numarasi gibi kenar mobilyasi HARIC tutulur.
    Kural cizgileri yok sayilir. Donus: (img, (L,T,R,B))."""
    g = img.convert("L")
    w, h = g.size
    px = g.load()
    st = 2
    rx0, ry0 = max(0, int(bx0) - 16), max(0, int(by0) - 16)
    rx1, ry1 = min(w, int(bx1) + 16), min(h, int(by1) + 16)
    rowc = [0] * h
    colc = [0] * w
    for y in range(ry0, ry1):
        for x in range(rx0, rx1, st):
            if px[x, y] < 248:
                rowc[y] += 1
                colc[x] += 1
    rmax = (rx1 - rx0) // st
    cmax = (ry1 - ry0)

    def clusters(idxs):
        out = []
        for i in idxs:
            if out and i - out[-1][-1] <= 1:
                out[-1].append(i)
            else:
                out.append([i])
        return out

    rule_rows = set()
    for cl in clusters([y for y, c in enumerate(rowc) if c >= 0.9 * rmax]):
        if len(cl) <= 30:
            rule_rows.update(cl)
    rule_cols = set()
    for cl in clusters([x for x, c in enumerate(colc) if c >= 0.9 * cmax]):
        if len(cl) <= 30:
            rule_cols.update(cl)

    rows = [y for y, c in enumerate(rowc) if c >= 20 and y not in rule_rows]
    cols = [x for x, c in enumerate(colc) if c >= 20 and x not in rule_cols]
    if not rows or not cols:
        return img, (0, 0, w, h)
    M = 83
    L = max(0, cols[0] - M)
    T = max(0, rows[0] - M)
    R = min(w, cols[-1] + 1 + M)
    B = min(h, rows[-1] + 1 + M)
    return img.crop((L, T, R, B)), (L, T, R, B)

def merge_drawings(objs, tol=4.0):
    """Yakın çizim parçalarını (tablo hücre çizgileri, tik işaretleri) tek görsel
    birime birleştir. Tek başına 19x0pt veya 0x17pt olan hücre çizgileri 30x25pt
    filtresinden geçemez; birleşince gerçek görsel boyutu ortaya çıkar."""
    parts = []
    for o in objs or []:
        try:
            x0, x1 = float(o["x0"]), float(o["x1"])
            top, bot = float(o["top"]), float(o["bottom"])
        except Exception:
            continue
        if x1 < x0:
            x0, x1 = x1, x0
        if bot < top:
            top, bot = bot, top
        parts.append((x0, top, x1, bot))
    if not parts:
        return []

    # Grid tabanlı kümeleme (Union-Find)
    cell = max(tol * 2, 24.0)
    buckets = {}
    for i, (x0, y0, x1, y1) in enumerate(parts):
        for gx in range(int(x0 // cell), int(x1 // cell) + 1):
            for gy in range(int(y0 // cell), int(y1 // cell) + 1):
                buckets.setdefault((gx, gy), []).append(i)

    parent = list(range(len(parts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for idxs in buckets.values():
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                a, b = idxs[i], idxs[j]
                ax0, ay0, ax1, ay1 = parts[a]
                bx0, by0, bx1, by1 = parts[b]
                if (ax0 <= bx1 + tol and ax1 >= bx0 - tol and
                        ay0 <= by1 + tol and ay1 >= by0 - tol):
                    union(a, b)

    groups = {}
    for i in range(len(parts)):
        groups.setdefault(find(i), []).append(parts[i])

    out = []
    for items in groups.values():
        out.append({
            "x0": min(it[0] for it in items),
            "top": min(it[1] for it in items),
            "x1": max(it[2] for it in items),
            "bottom": max(it[3] for it in items),
            "_parts": len(items),
        })
    return out


def page_items(page, vimg=None, vsc=1.0):
    """Sözcük + önemli çizimler; başlık(<=75) ve footer bandını ele."""
    items = []
    warn_tops = []
    for w in page.extract_words() or []:
        t = norm_tr(str(w.get("text",""))).strip().rstrip(".")
        if t in WARN and float(w["top"]) > 700:
            warn_tops.append(float(w["top"]))
        if "geçiniz" in norm_tr(str(w.get("text",""))) and float(w["top"]) > 700:
            warn_tops.append(float(w["top"]))
    footer_cap = (min(warn_tops) - 2) if warn_tops else PAGE_H - 15
    header_bottom = max((float(w["bottom"]) for w in page.extract_words() or []
                         if float(w["top"]) < 75), default=0.0) + 2.0

    for w in page.extract_words() or []:
        x0, x1 = float(w["x0"]), float(w["x1"])
        top, bot = float(w["top"]), float(w["bottom"])
        if top < 75 or top >= footer_cap:
            continue
        t = str(w.get("text", "")).strip()
        if t.isdigit() and top > 720:  # sayfa numarasi
            continue
        items.append({"x0": x0, "x1": x1, "top": top, "bot": bot,
                      "text": str(w.get("text","")), "opt": bool(OPT_RE.match(str(w.get("text",""))))})
    for objs in (page.lines, page.rects, page.curves, page.images):
        for m in merge_drawings(objs):
            x0, x1 = m["x0"], m["x1"]
            top, bot = m["top"], m["bottom"]
            if x1 - x0 < 30 or bot - top < 25:
                continue
            if x1 - x0 > PAGE_W * 0.92 and bot - top > PAGE_H * 0.92:
                continue
            if top < 75 or top >= footer_cap:
                continue
            if vimg is not None:
                bb = ink_shrink(vimg, vsc, x0, top, x1, bot)
                if bb is None:
                    continue
                x0, top, x1, bot = bb
                if x1 - x0 < 8 or bot - top < 8:
                    continue
            items.append({"x0": x0, "x1": x1, "top": top, "bot": bot, "text": "", "opt": False})
    return items, footer_cap, header_bottom

def find_anchors(page):
    out, seen = [], set()
    for w in page.extract_words() or []:
        m = QNUM_RE.match(str(w.get("text","")))
        if not m:
            continue
        x0, top = float(w["x0"]), float(w["top"])
        if top < 75:
            continue
        left_ok = 25 <= x0 <= 50
        right_ok = 270 <= x0 <= 300
        if not (left_ok or right_ok):
            continue
        n = int(m.group(1))
        key = (n, "L" if left_ok else "R")
        if key in seen:
            continue
        seen.add(key)
        out.append({"n": n, "x0": x0, "top": top, "col": "L" if left_ok else "R"})
    return out

def find_anchors_fitz(fz_page):
    """PyMuPDF ile anchor tespiti. pdfplumber, matematik formülüyle iç içe
    geçen soru numaralarını birleştirir ('18.' + '√405' -> '1384.0') ve anchor
    kaçırır; fitz metin parçalarını doğru ayırır. Koordinatlar fitz line-box."""
    out = []
    for w in fz_page.get_text("words"):
        x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
        m = QNUM_RE.match(txt)
        if not m:
            continue
        if y0 < 75:
            continue
        left_ok = 25 <= x0 <= 50
        right_ok = 270 <= x0 <= 300
        if not (left_ok or right_ok):
            continue
        out.append({"n": int(m.group(1)), "x0": x0, "top": y0,
                    "col": "L" if left_ok else "R"})
    return out


def find_anchors_merged(page, fz_page):
    """pdfplumber + PyMuPDF anchor birleşimi.

    pdfplumber glyph-top, fitz line-box kullanır; ofset her sayfada medyanla
    kalibre edilir (ortak bulunan anchor çiftlerinden).
    Aynı soru numarası iki sütunda çıkarsa (pdfplumber yanlış sütun atarsa)
    fitz anchor'ı tercih edilir (fitz word-level column doğru)."""
    pp = find_anchors(page)
    fz = find_anchors_fitz(fz_page)
    offs = []
    for a in pp:
        for b in fz:
            if a["n"] == b["n"] and a["col"] == b["col"] and abs(a["x0"] - b["x0"]) < 6:
                offs.append(a["top"] - b["top"])
                break
    off = sorted(offs)[len(offs) // 2] if offs else 0.0
    # Önce fitz anchor'larını baz al (doğru sütun). Sonra pdfplumber'dan
    # sadece fitz'ta O SORU NUMARASI YOKSA ekle (aynı n farklı col atlanır).
    merged = {}  # key: n -> anchor (fitz column wins)
    for b in fz:
        nb = dict(b)
        nb["top"] = b["top"] + off
        merged[b["n"]] = nb
    for a in pp:
        if a["n"] not in merged:
            merged[a["n"]] = dict(a)
    # Convert back to list of dicts with col preserved
    anchors = list(merged.values())
    return sorted(anchors, key=lambda a: (a["col"], a["top"]))


def assign_items(items, anchors):
    """Her öğeyi en yakın üstteki anchor'a ata. Tam genişlik soru kuralı:
    global-en-yakın anchor (herhangi sütun) bölge-anchor'undan DAHA YAKINSA ve o
    sorunun grubunda bu y bandında bölgeyi aşan (spanning) öğe varsa global
    anchor kazanır — ör. Matematik Q14 vinç figürü sağ parçaları."""
    groups = {i: [] for i in range(len(anchors))}
    unassigned = []
    items = sorted(items, key=lambda it: it["top"])  # y sırası: spanning önce birikir
    L = [i for i, a in enumerate(anchors) if a["col"] == "L"]
    R = [i for i, a in enumerate(anchors) if a["col"] == "R"]

    def nearest(cand_idx, y):
        c = [i for i in cand_idx if anchors[i]["top"] <= y + 4]
        return max(c, key=lambda i: anchors[i]["top"]) if c else None

    # 1. geçiş: spanning öğeler + bölge öğeleri
    for it in items:
        y = it["top"]
        spans = it["x0"] < COL and it["x1"] > COL
        g = nearest(range(len(anchors)), y)
        if spans:
            if g is not None:
                groups[g].append(it)
            else:
                unassigned.append(it)
            continue
        if it["x1"] <= COL:
            r = nearest(L, y)
        else:
            r = nearest(R, y)
        if r is None:
            unassigned.append(it)
            continue
        # çakışma: global en yakın, bölge en yakınından daha yakınsa ve global
        # anchor'un grubunda bu y bandında spanning öğe varsa -> global kazanır.
        # SADECE figür parçaları için: metin (şık A-D, soru kökü) daima kendi
        # sütununun anchor'una aittir — aksi halde komşu sorunun şıkları yanlış
        # atanır (ör. MEBİ LGS-2 Sayısal s5: Q5'in geniş figürü Q7 şıklarını çeker).
        if g is not None and g != r and anchors[g]["top"] > anchors[r]["top"] and not it["text"]:
            gy = it["top"]
            if any(s["x0"] < COL and s["x1"] > COL and
                   s["top"] <= gy + 30 and s["bot"] >= gy - 30
                   for s in groups[g]):
                groups[g].append(it)
                continue
        groups[r].append(it)

    # 3. onarım: A (üst anchor'u aşağıda olan tam genişlik soru) komşu sütun
    #    parçalarını geri alsın — ama B'nin kendi içerik zinciri (40pt yakınlık)
    #    devam ediyorsa dokunma (ör. fen Q3'ün D şıkkı).
    for _ in range(3):
        moved = False
        for ai in range(len(anchors)):
            A = anchors[ai]
            if not any(s["x0"] < COL - 2 and s["x1"] > COL + 2 and s["top"] >= A["top"] - 2
                       for s in groups[ai]):
                continue
            for bi in range(len(anchors)):
                B = anchors[bi]
                if B["top"] >= A["top"] - 30:
                    continue
                for it in list(groups[bi]):
                    if it["top"] < A["top"] - 2:
                        continue
                    if any(s["x0"] < COL and s["x1"] > COL and
                           s["top"] <= it["top"] + 30 and s["bot"] >= it["top"] - 30
                           for s in groups[ai]):
                        # B'nin kendi zinciri bu y bandında sürüyor mu?
                        near = [o for o in groups[bi] if o is not it and abs(o["top"] - it["top"]) <= 40]
                        if not near:
                            groups[bi].remove(it)
                            groups[ai].append(it)
                            moved = True
        if not moved:
            break

    # 4. satır birleştirme: merkezden geçen metin satırı TEK soruya aittir.
    #    Satır = y bandı (<8pt fark) + x boşluğu <30pt kelime zinciri.
    #    Merkezi aşan satırda tüm kelimeler, sol uçtaki anchor'un grubuna gider.
    words_only = [(bi, it) for bi in range(len(anchors)) for it in groups[bi] if it["text"]]
    words_only.sort(key=lambda p: (p[1]["top"], p[1]["x0"]))
    used = set()
    for idx, (bi, it) in enumerate(words_only):
        if id(it) in used:
            continue
        cluster = [(bi, it)]
        used.add(id(it))
        changed = True
        while changed:
            changed = False
            for bj, o in words_only:
                if id(o) in used:
                    continue
                for _, c in cluster:
                    if abs(o["top"] - c["top"]) < 8 and min(abs(o["x0"] - c["x1"]), abs(c["x0"] - o["x1"])) < 12:
                        cluster.append((bj, o))
                        used.add(id(o))
                        changed = True
                        break
        cx0 = min(w[1]["x0"] for w in cluster)
        cx1 = max(w[1]["x1"] for w in cluster)
        if cx0 < COL - 2 and cx1 > COL + 2 and len({w[0] for w in cluster}) > 1:
            left_word = min(cluster, key=lambda w: w[1]["x0"])
            lw = left_word[1]
            y = lw["top"]
            if lw["x1"] <= COL and L:
                target = nearest(L, y)
            else:
                target = nearest(range(len(anchors)), y)
            if target is not None:
                for bj, o in cluster:
                    if bj != target and o in groups[bj]:
                        groups[bj].remove(o)
                        groups[target].append(o)

    # anchor üstünde kalan öğeler (stimulus / anchor üstü şıklar) ve
    # anchor'siz bölgede kalanlar (ör. tek sütunlu sayfada sağdaki D şeridi)
    for it in unassigned:
        y_mid = (it["top"] + it["bot"]) / 2
        g = nearest(range(len(anchors)), y_mid)
        if g is not None:
            # anchor altı içerik: en yakın ÜSTTEKİ anchor'un sorusuna aittir
            groups[g].append(it)
            continue
        if it["x1"] <= COL and L:
            first = min(L, key=lambda i: anchors[i]["top"])
        elif it["x0"] >= COL and R:
            first = min(R, key=lambda i: anchors[i]["top"])
        elif anchors:
            first = min(range(len(anchors)), key=lambda i: anchors[i]["top"])
        else:
            continue
        if anchors[first]["top"] - y_mid <= 320:
            groups[first].append(it)
    return groups

def extract_subject(pdf_path, slug, p_start, p_end, expected, ak, outdir, only=None):
    questions, done = [], set()
    with pdfplumber.open(pdf_path) as pdf:
        doc = fitz.open(str(pdf_path))
        for pidx in range(p_start - 1, min(p_end, len(pdf.pages))):
            page = pdf.pages[pidx]
            pn = pidx + 1
            pg = doc[pidx]
            anchors = [a for a in find_anchors_merged(page, pg)
                       if 1 <= a["n"] <= expected and a["n"] not in done]
            if not anchors:
                continue
            vpix = pg.get_pixmap(matrix=fitz.Matrix(100/72, 100/72))
            vimg = Image.frombytes("RGB", (vpix.width, vpix.height), vpix.samples).convert("L")
            items, footer_cap, header_bottom = page_items(page, vimg, 100/72)
            groups = assign_items(items, anchors)

            # çarpışma tavanları: aynı bölgedeki sonraki anchor
            next_top = {}
            for col in ("L", "R"):
                col_anchor_idx = [i for i, a in enumerate(anchors) if a["col"] == col]
                col_anchor_idx.sort(key=lambda i: anchors[i]["top"])
                for j, i in enumerate(col_anchor_idx):
                    next_top[i] = anchors[col_anchor_idx[j+1]]["top"] if j+1 < len(col_anchor_idx) else None

            for i, a in enumerate(anchors):
                if a["n"] in done or not groups[i]:
                    continue
                if only is not None and a["n"] not in only:
                    continue
                gx0 = min(it["x0"] for it in groups[i])
                gy0 = min(it["top"] for it in groups[i])
                gx1 = max(it["x1"] for it in groups[i])
                gy1 = max(it["bot"] for it in groups[i])
                y0 = max(0.0, gy0 - MARGIN)
                y0 = max(y0, min(header_bottom, gy0 - 1))
                y1 = gy1 + MARGIN
                nt = next_top.get(i)
                if nt is not None:
                    y1 = min(y1, nt - 4)
                y1 = min(y1, footer_cap)
                x0 = max(0.0, gx0 - MARGIN)
                x1 = min(PAGE_W, gx1 + MARGIN)
                if all(it["x1"] <= COL for it in groups[i]):
                    x1 = min(x1, max(COL - 3, gx1))
                elif all(it["x0"] >= COL for it in groups[i]):
                    x0 = max(x0, min(COL + 4, gx0))
                if y1 - y0 < 40 or x1 - x0 < 40:
                    print(f"  SKIP Q{a['n']} (küçük bbox)")
                    continue
                pg = doc[pidx]
                pix = pg.get_pixmap(matrix=fitz.Matrix(DPI/72, DPI/72))
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                sx, sy = img.width/PAGE_W, img.height/PAGE_H
                crop = img.crop((round(x0*sx), round(y0*sy), round(x1*sx), round(y1*sy)))
                crop, (Lpx, Tpx, Rpx, Bpx) = trim_ink(crop,
                        (gx0-x0)*sx, (gy0-y0)*sy, (gx1-x0)*sx, (gy1-y0)*sy)
                x0, y0 = x0 + Lpx/sx, y0 + Tpx/sy
                x1, y1 = x0 + (Rpx - Lpx)/sx, y0 + (Bpx - Tpx)/sy
                out = outdir / slug / f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}.png"
                crop.save(out, "PNG")
                ans = ak.get(slug, {}).get(a["n"])
                (outdir / slug / f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}.answer.txt").write_text(ans or "")
                text_words = sorted([it for it in groups[i] if it["text"]],
                                    key=lambda it: (round(it["top"]), it["x0"]))
                qtext = " ".join(it["text"] for it in text_words)
                has_fig = any(not it["text"] for it in groups[i])
                print(f"  Q{a['n']:02d} p{pn}{a['col']} h={y1-y0:.0f}pt w={x1-x0:.0f}pt bbox=({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) fig={has_fig}")
                questions.append({
                    "id": f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}",
                    "questionNumber": a["n"], "page": pn, "column": a["col"],
                    "representation": "IMAGE_BACKED",
                    "file": f"MEB-LGS-2015-{slug.upper()}-Q{a['n']:02d}.png",
                    "questionText": qtext, "hasFigure": has_fig,
                    "topic": slug, "topicFull": slug,
                    "visual": {
                        "publicPath": f"/exams/2015-{slug}-q{a['n']:02d}.png",
                        "clipRectPt": {"x0": round(x0,1), "y0": round(y0,1),
                                       "x1": round(x1,1), "y1": round(y1,1)},
                        "renderDpi": DPI, "authority": "ORIGINAL_MEB_PDF",
                        "reconstructedFromOcr": False, "assetSha256": sha256(out),
                    },
                    "answer": ans, "status": "NEEDS_REVIEW", "published": True, "subject": slug,
                })
                done.add(a["n"])
        doc.close()
    return questions

PILOT_QUESTIONS = {
    "turkce": {1, 10, 12, 20},
    "inkilap-tarihi": {1, 5, 10},
    "din-kulturu": {1, 5, 10},
    "ingilizce": {1, 5, 10},
    "matematik": {1, 11, 13, 14},
    "fen-bilimleri": {1, 3, 20},
}

def main():
    pilot = "--pilot" in sys.argv
    outdir = REPO / "_pilot_2015" if pilot else OUTPUT_DIR
    ak = parse_answer_key()
    for s, v in ak.items():
        print(f"cevap {s}: {len(v)}")
    all_q = {}
    for slug, pdfn, ps, pe, exp in SUBJECTS:
        only = PILOT_QUESTIONS.get(slug) if pilot else None
        print(f"\n=== {slug} ===")
        (outdir / slug).mkdir(parents=True, exist_ok=True)
        qs = extract_subject(INPUT_DIR / pdfn, slug, ps, pe, exp, ak, outdir, only)
        all_q[slug] = qs
        man = {"manifestVersion": "1.0", "status": "NEEDS_REVIEW", "published": True,
               "source": {"sourceId": "2015-DENEME", "sourceType": "MEB_EXAM",
                          "subject": slug, "period": "2014-2015"},
               "questions": qs,
               "answerKeyCandidates": {str(q["questionNumber"]): q["answer"] for q in qs if q["answer"]},
               "summary": {"questionsExtracted": len(qs), "expectedQuestions": exp}}
        man_name = "manifest_2015.json" if pilot else "manifest_2015.json"
        (outdir / slug / man_name).write_text(
            json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (outdir / slug / "answers_2015.json").write_text(
            json.dumps({str(n): l for n, l in sorted(ak.get(slug, {}).items())},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with open(outdir / slug / "analysis_2015.jsonl", "w", encoding="utf-8") as f:
            for q in qs:
                f.write(json.dumps({
                    "id": q["id"], "questionNumber": q["questionNumber"],
                    "page": q["page"], "column": q["column"],
                    "questionText": q["questionText"],
                    "questionTextSource": "PDF_TEXT_LAYER",
                    "hasFigure": q["hasFigure"],
                    "representation": q["representation"],
                    "answer": q["answer"],
                    "answerSource": "MEB_CEVAP_ANAHTARI_2015",
                    "visual": q["visual"],
                    "analysisStatus": "PENDING",
                    "warnings": [],
                }, ensure_ascii=False) + "\n")
        eksik = [q["questionNumber"] for q in qs if not q["answer"]]
        print(f"  -> {len(qs)}/{exp} soru, cevapsız: {eksik or 'yok'}")
    if pilot:
        print(f"\nPilot bitti: {outdir}")
        return
    import shutil
    dst = REPO / "public" / "exams"
    dst.mkdir(parents=True, exist_ok=True)
    for slug, qs in all_q.items():
        for q in qs:
            src = OUTPUT_DIR / slug / f"MEB-LGS-2015-{slug.upper()}-Q{q['questionNumber']:02d}.png"
            if src.exists():
                shutil.copy2(src, dst / f"2015-{slug}-q{q['questionNumber']:02d}.png")
    print("\nTamamlandı.")

if __name__ == "__main__":
    main()