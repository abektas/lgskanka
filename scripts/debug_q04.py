import sys
sys.path.insert(0, "/home/selam/roller/web/lgs-ai-coach/scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("fix27", "/home/selam/roller/web/lgs-ai-coach/scripts/fix_27_questions.py")
fix27 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix27)

import pdfplumber
pdf_path = fix27.find_pdf("2024", "turkce")
print("PDF:", pdf_path)
with pdfplumber.open(pdf_path) as pdf:
    pg = pdf.pages[9]
    items, words = fix27.page_items(pg)
    W, H = float(pg.width), float(pg.height)
    divider = fix27.detect_divider(items, W)
    print("divider:", divider, "W:", W)
    anchors = []
    for w in words:
        tx = w.get("text","").strip()
        top = float(w["top"])
        if fix27.ANCHOR_RE.match(tx) and top >= 75:
            anchors.append({"q": int(tx[:-1]), "x": float(w["x0"]), "top": top})
    anchors.sort(key=lambda a: a["top"])
    print("anchors:", [(a["q"], round(a["x"],1), round(a["top"],1)) for a in anchors])
    anchor = [a for a in anchors if a["q"] == 18][0]
    band = (0.0, divider) if divider else (0.0, W)
    print("band:", band, "anchor:", anchor)
    later = [a for a in anchors if a["top"] > anchor["top"] + 6 and band[0] <= a["x"] < band[1]]
    next_anchor = min(later, key=lambda a: a["top"]) if later else None
    print("next_anchor:", next_anchor)
    own = []
    for it in items:
        cx = (it["x0"]+it["x1"])/2
        if not (band[0] <= cx < band[1]): continue
        cy = (it["top"]+it["bottom"])/2
        if cy < anchor["top"]-6: continue
        if next_anchor and cy >= next_anchor["top"]: continue
        own.append(it)
    own_norm = fix27.norm_tr(" ".join(it["text"] for it in own if it["kind"]=="text"))
    print("OWN NORM:", own_norm[:600])
    stem = fix27.STEMS.get("MEB-LGS-2024-TURKCE-Q18","")
    print("STEM:", stem[:200])
    print("stem_match:", fix27.stem_score(stem, own_norm))