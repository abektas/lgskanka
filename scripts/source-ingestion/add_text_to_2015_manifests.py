#!/usr/bin/env python3
"""Add questionText to 2015 manifests by extracting text from PDF crop regions."""
import json, re
from pathlib import Path
import pdfplumber

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")

SUBJECT_PDF = {
    "turkce": "2015 Sözel.pdf",
    "inkilap-tarihi": "2015 Sözel.pdf",
    "din-kulturu": "2015 Sözel.pdf",
    "ingilizce": "2015 Sözel.pdf",
    "matematik": "2015 Sayısal.pdf",
    "fen-bilimleri": "2015 Sayısal.pdf",
}

for subj in ["turkce", "matematik", "fen-bilimleri", "ingilizce", "din-kulturu", "inkilap-tarihi"]:
    pdf_name = SUBJECT_PDF[subj]
    pdf_path = INPUT_DIR / pdf_name
    manifest_path = REPO / "lgs_18_26" / subj / "manifest_2015.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    with pdfplumber.open(pdf_path) as pdf:
        for q in manifest["questions"]:
            cr = q["visual"]["clipRectPt"]
            page = pdf.pages[q["page"] - 1]
            words = page.extract_words() or []
            crop_words = []
            for w in words:
                if cr["x0"] - 5 <= float(w["x0"]) <= cr["x1"] + 5 and cr["y0"] - 5 <= float(w["top"]) <= cr["y1"] + 5:
                    crop_words.append(w["text"])
            q["questionText"] = " ".join(crop_words)
            q["hasFigure"] = False
            q["topic"] = subj
            q["topicFull"] = subj
    
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{subj}: {len(manifest['questions'])} soru, text eklendi")

print("Tamamlandı!")