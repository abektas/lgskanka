#!/usr/bin/env python3
"""Extract official MEB 8th-grade curriculum outcomes from the TTKB PDFs.

Sources (mufredat.meb.gov.tr, the official TTKB curriculum portal):
  matematik  MATEMATİK DERSİ ÖĞRETİM PROGRAMI (1-8) 2018
  fen        FEN BİLİMLERİ DERSİ ÖĞRETİM PROGRAMI (3-8) 2018
  turkce     TÜRKÇE DERSİ ÖĞRETİM PROGRAMI (1-8) 2019
  inkilap    T.C. İNKILAP TARİHİ VE ATATÜRKÇÜLÜK (8) 2018
  ingilizce  İNGİLİZCE DERSİ ÖĞRETİM PROGRAMI (2-8) 2018
  din        DİN KÜLTÜRÜ VE AHLAK BİLGİSİ (4-8) 2018

Why 2018: LGS is sat in grade 8, and grade 8 is NOT part of the Türkiye Yüzyılı
Maarif Modeli rollout (grades 4, 8 and 12 stay on the previous curriculum), so
every LGS paper 2018-2026 is drawn from the 2018 programs. This registry is the
authoritative source for CURRENT_TYMM-mapped outcome codes; nothing here is
AI-generated or inferred.

Output: data/curriculum/meb-2018-grade8-outcomes.json
"""
from __future__ import annotations
import json, re, hashlib, sys
from pathlib import Path
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/lgs-ai-coach/data/curriculum/source")
OUT = Path("/home/selam/roller/web/lgs-ai-coach/data/curriculum/meb-2018-grade8-outcomes.json")

# (subject key, subject display, program year, file, code regex, official source URL)
SPECS = [
    ("matematik", "Matematik", 2018, "matematik-2018.pdf", r"M\.8\.\d+\.\d+\.\d+",
     "https://mufredat.meb.gov.tr/Dosyalar/201813017165445-MATEMAT%C4%B0K%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI%202018v.pdf"),
    ("fen", "Fen Bilimleri", 2018, "fen-bilimleri-2018.pdf", r"F\.8\.\d+\.\d+\.\d+",
     "https://mufredat.meb.gov.tr/Dosyalar/201812312311937-FEN%20B%C4%B0L%C4%B0MLER%C4%B0%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI2018.pdf"),
    ("turkce", "Türkçe", 2019, "turkce-2019.pdf", r"T\.8\.\d+\.\d+",
     "https://mufredat.meb.gov.tr/Dosyalar/20195716392253-02-T%C3%BCrk%C3%A7e%20%C3%96%C4%9Fretim%20Program%C4%B1%202019.pdf"),
    ("inkilap", "T.C. İnkılap Tarihi ve Atatürkçülük", 2018, "inkilap-tarihi-2018.pdf", r"İTA\.8\.\d+\.\d+",
     "https://mufredat.meb.gov.tr/Dosyalar/201812104016155-%C4%B0NKILAP%20TAR%C4%B0H%C4%B0%20VE%20ATAT%C3%9CRK%C3%87%C3%9CL%C3%9CK%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI.pdf"),
    ("ingilizce", "İngilizce", 2018, "ingilizce-2018.pdf", r"E8\.\d+\.[A-Z]{1,2}\d+",
     "https://mufredat.meb.gov.tr/Dosyalar/201812411191321-%C4%B0NG%C4%B0L%C4%B0ZCE%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI%20Klas%C3%B6r%C3%BC.pdf"),
    ("din", "Din Kültürü ve Ahlak Bilgisi", 2018, "din-kulturu-2018.pdf", r"8\.\d+\.\d+",
     "https://dogm.meb.gov.tr/meb_iys_dosyalar/2019_02/25182918_DKAB_4-8_9-12_Ogretim_Programi_Turkce.pdf"),
]

# unit (öğrenme alanı / ünite) names per subject, keyed by the 2nd code segment
UNITS = {
    "matematik": {"1": "Sayılar ve İşlemler", "2": "Cebir", "3": "Geometri ve Ölçme",
                  "4": "Veri İşleme", "5": "Olasılık"},
    "fen": {"1": "Dünya ve Evren", "2": "Canlılar ve Yaşam", "3": "Fiziksel Olaylar",
            "4": "Madde ve Doğası"},
    "turkce": {"1": "Sözlü İletişim", "2": "Okuma", "3": "Yazma"},
    "inkilap": {"1": "Bir Kahraman Doğuyor", "2": "Millî Uyanış", "3": "Millî Bir Destan",
                "4": "Atatürkçülük ve Çağdaşlaşan Türkiye", "5": "Demokratikleşme Çabaları",
                "6": "Atatürk Dönemi Türk Dış Politikası", "7": "Atatürk'ün Ölümü ve Sonrası"},
    "ingilizce": {},   # units are thematic (Friendship, Teen Life, ...); read from the text
    "din": {"1": "Kader ve Kaza", "2": "Zekât ve Sadaka", "3": "Din ve Hayat",
            "4": "Hz. Muhammed'in Örnekliği", "5": "Kur'an-ı Kerim ve Özellikleri"},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _is_topic_heading(s: str) -> bool:
    """True for a bare topic heading like 'M.8.1.2. Üslü İfadeler' (no sentence)."""
    if not re.match(r"^[A-Za-zÇĞİÖŞÜçğıöşü]*\.?\d+(\.\d+)*\.\s+\S", s):
        return False
    # a real outcome/explanation is a full sentence ending with '.'
    return not s.rstrip().endswith(".")


def _despace(s: str) -> str:
    """Collapse the 'B i r' letter-spaced artefact some MEB PDFs emit."""
    if not s:
        return s
    # a run of 6+ single chars separated by single spaces is letter-spacing
    if re.search(r"(?:\S \S \S \S \S \S)", s):
        s = re.sub(r"(?<=\S) (?=\S)", "", s) if s.count(" ") > len(s) / 2 else s
    return s


def extract_outcomes(pdf_path: Path, pattern: str):
    """Return [(code, text, explanation)] in document order.

    An outcome line wraps across PDF lines, and its explanation starts right
    after the sentence-ending period. So: append wrapped lines to the outcome
    text until one ends with '.', then treat everything up to the next outcome
    code (or a 'Terimler/kavramlar' line) as the explanation.
    """
    doc = pdfium.PdfDocument(str(pdf_path))
    full = "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    doc.close()
    lines = [l.strip() for l in full.replace("\r", "").split("\n")]
    rx = re.compile(r"^(" + pattern + r")\.?\s*(.*)$")
    # a 'Terimler veya kavramlar' line starts a non-outcome block; a bare
    # 'N.N. Title' heading (only in subjects whose codes are shorter than 4 segs)
    terms = lambda s: s.lower().startswith(("terimler veya kavramlar",
                                            "terim ve kavramlar"))
    out = []
    i = 0
    while i < len(lines):
        m = rx.match(lines[i])
        if not (m and m.group(2).strip()):
            i += 1
            continue
        code = m.group(1)
        text_parts = [m.group(2).strip()]
        j = i + 1
        while not text_parts[-1].endswith(".") and j < len(lines) and lines[j] \
                and not rx.match(lines[j]) and not terms(lines[j]):
            text_parts.append(lines[j]); j += 1
        expl = []
        while j < len(lines) and lines[j] and not rx.match(lines[j]) \
                and not terms(lines[j]):
            ln = lines[j]
            # skip topic headings and short table/column labels (e.g. 'Writing')
            if not _is_topic_heading(ln) and len(ln.split()) >= 3:
                expl.append(ln)
            j += 1
        out.append((code, _despace(" ".join(text_parts)),
                    _despace(" ".join(expl))))
        i = j
    # de-duplicate while keeping order
    seen, uniq = set(), []
    for c, t, e in out:
        if c not in seen:
            seen.add(c); uniq.append((c, t, e))
    return uniq


def main():
    registry = {
        "schemaVersion": "1.0",
        "framework": "CURRENT_TYMM",
        "note": ("Official MEB/TTKB 8th-grade learning outcomes for the programs in force for "
                 "LGS 2018-2026. Grade 8 is not part of the Maarif Modeli rollout, so the 2018 "
                 "(and 2019 Turkish) programs apply. Codes and text are copied verbatim from the "
                 "TTKB PDFs; nothing is inferred."),
        "sourcePortal": "https://mufredat.meb.gov.tr",
        "subjects": {},
    }
    for key, disp, year, fname, pattern, url in SPECS:
        p = SRC / fname
        if not p.exists() or p.stat().st_size < 50000:
            print(f"  ATLANDI (yok/bozuk): {key} <- {fname}", file=sys.stderr)
            continue
        outs = extract_outcomes(p, pattern)
        # the unit/öğrenme-alanı number is the segment AFTER the grade marker,
        # which differs per subject: M.8.1... -> idx 2, E8.1... -> idx 1, 8.1... -> idx 1
        unit_idx = {"matematik": 2, "fen": 2, "turkce": 2, "inkilap": 2,
                    "ingilizce": 1, "din": 1}[key]
        units = {}
        for code, text, expl in outs:
            seg = code.split(".")
            unit_no = seg[unit_idx] if len(seg) > unit_idx else "?"
            units.setdefault(unit_no, []).append({
                "code": code, "text": text,
                "explanation": expl or None,
            })
        registry["subjects"][key] = {
            "subject": disp, "programYear": year,
            "sourceFile": fname, "sourceUrl": url, "sha256": sha256(p),
            "outcomeCount": len(outs),
            "unitNames": UNITS.get(key, {}),
            "unitOutcomeCounts": {u: len(v) for u, v in sorted(units.items(),
                                                              key=lambda kv: (len(kv[0]), kv[0]))},
            "outcomes": [{"code": c, "text": t, "explanation": e or None}
                         for c, t, e in outs],
        }
        print(f"  {key:10} {disp:38} {len(outs):3} kazanım")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(s["outcomeCount"] for s in registry["subjects"].values())
    print(f"\nToplam {total} kazanım, {len(registry['subjects'])} ders -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
