#!/usr/bin/env python3
"""cal23 multi-subject extractor: İnkılap + Din + İngilizce with unit info.

Page map (verified via pdftotext):
  İnkılap Tarihi:    P7-95,   key P96
  Din Kültürü:       P97-175,  key P176
  İngilizce:         P177-328, key P329
  Merkezî Sınavlar:  P331-418 (SKIP)
"""
import sys, json, re, hashlib
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from extract_study_workbook import crop_page, parse_exam_key_text
from pypdfium2 import PdfDocument

PDF = "/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal23.pdf"
REPO = Path("/home/selam/roller/web/lgs-ai-coach")
OUT_BASE = REPO / "lgs_çalışma_soruları"
LOGS = REPO / "logs"
LOGS.mkdir(exist_ok=True)

# Unit definitions: (unit_num, name, start_page, end_page)
UNITS = {
    "inkilap-tarihi": [
        (1, "Bir Kahraman Doğuyor", 7, 24),
        (2, "Millî Uyanış: Bağımsızlık Yolunda Atılan Adımlar", 25, 50),
        (3, "Millî Bir Destan: Ya İstiklal Ya Ölüm!", 51, 70),
        (4, "Atatürkçülük ve Çağdaşlaşan Türkiye", 71, 82),
        (5, "Demokratikleşme Çabaları", 83, 88),
        (6, "Atatürk Dönemi Türk Dış Politikası", 89, 95),
    ],
    "din-kulturu": [
        (1, "Kader İnancı", 97, 120),
        (2, "Zekât ve Sadaka", 121, 142),
        (3, "Din ve Hayat", 143, 162),
        (4, "Hz. Muhammed'in Örnekliğı", 163, 170),
        (5, "Kur'an-ı Kerim ve Özellikleri", 171, 175),
    ],
    "ingilizce": [
        (1, "Friendship", 177, 200),
        (2, "Teen Life", 201, 220),
        (3, "In the Kitchen", 221, 244),
        (4, "On the Phone", 245, 264),
        (5, "The Internet", 265, 284),
        (6, "Adventures", 285, 296),
        (7, "Tourism", 297, 308),
        (8, "Chores", 309, 318),
        (9, "Science", 319, 324),
        (10, "Natural Forces", 325, 328),
    ],
}

KEY_PAGES = {"inkilap-tarihi": 96, "din-kulturu": 176, "ingilizce": 329}
SUBJECT_LABEL = {
    "inkilap-tarihi": "T.C. İNKILAP",
    "din-kulturu": "DİN KÜLTÜRÜ",
    "ingilizce": "İNGİLİZCE",
}

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def get_unit(subject, page):
    for u in UNITS[subject]:
        if u[2] <= page <= u[3]:
            return u[0], u[1]
    return None, None

def main():
    doc = PdfDocument(PDF)
    all_results = {}

    for subject, units in UNITS.items():
        print(f"\n{'='*50}")
        print(f"DERS: {subject}")
        print(f"{'='*50}")

        outdir = OUT_BASE / subject
        outdir.mkdir(exist_ok=True)
        key_page = KEY_PAGES[subject]
        label = SUBJECT_LABEL[subject]

        # Determine page range
        start = units[0][2]
        end = units[-1][3]

        questions = []
        for pno in range(start, end + 1):
            page = doc[pno - 1]
            crops = crop_page(page, pno, outdir, "cal23")
            for c in crops:
                unit_num, unit_name = get_unit(subject, pno)
                png_path = outdir / c["file"]
                entry = {
                    "file": str(png_path.relative_to(REPO)),
                    "page": pno,
                    "q": c["q"],
                    "unit": unit_num,
                    "unitName": unit_name,
                    "sha256": sha256(png_path),
                    "status": "NEEDS_REVIEW",
                    "sourceFile": "cal23.pdf",
                }
                questions.append(entry)
            if crops:
                print(f"  P{pno}: {len(crops)} soru (ünite {unit_num})")

        # Parse answer key
        print(f"\n  Cevap anahtarı: P{key_page}")
        key_page_obj = doc[key_page - 1]
        key_text = key_page_obj.get_textpage().get_text_range()
        print(f"  Key text (ilk 200): {key_text[:200]}")

        # Try to parse answers for this subject
        answers = parse_exam_key_text(key_text)
        print(f"  {label}: {len(answers)} cevap parse edildi")

        # Match answers
        matched = 0
        for q in questions:
            qnum = q["q"]
            if qnum in answers:
                q["answer"] = answers[qnum]
                q["answerSource"] = "key"
                matched += 1
            else:
                q["answer"] = None
                q["answerSource"] = None

        print(f"  Eşleşme: {matched}/{len(questions)}")

        # Save manifest
        manifest = {
            "book": "cal23",
            "subject": subject,
            "questions": questions,
            "answerMappingStatus": f"{matched}/{len(questions)}",
        }
        (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        print(f"  Manifest kaydedildi: {outdir / 'manifest.json'}")

        all_results[subject] = {"total": len(questions), "matched": matched}

    doc.close()

    print(f"\n{'='*50}")
    print("ÖZET")
    print(f"{'='*50}")
    for s, r in all_results.items():
        print(f"  {s}: {r['total']} soru, {r['matched']} cevap eşleşti")

if __name__ == "__main__":
    main()
