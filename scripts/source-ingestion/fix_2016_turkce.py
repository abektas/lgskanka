#!/usr/bin/env python3
"""Fix 2016 Türkçe crops from Sözel PDF."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300

FIXES = {
    "turkce": {
        # Page 3: Q1 left (D left 254.8), Q2 left (D left 608.2), Q3 right (D right 246.3), Q4 right (D right 570.0)
        1: {"page": 3, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 274.8}, "column": "left"},
        2: {"page": 3, "clipRectPt": {"x0": 20.0, "y0": 380.6, "x1": 271.4, "y1": 628.2}, "column": "left"},
        3: {"page": 3, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 266.3}, "column": "right"},
        4: {"page": 3, "clipRectPt": {"x0": 281.4, "y0": 381.8, "x1": 532.8, "y1": 590.0}, "column": "right"},
        # Page 4: Q5 left (D left 338.8), Q6 left (D left on pg6 at 544.2), Q7 right (D right 410.8)
        5: {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 358.8}, "column": "left"},
        6: {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 358.8, "x1": 271.4, "y1": 564.2}, "column": "left"},
        7: {"page": 4, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 430.8}, "column": "right"},
        # Page 5: Q8 left (D left 398.8), Q9 right (D right 302.8)
        8: {"page": 5, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 418.8}, "column": "left"},
        9: {"page": 5, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 322.8}, "column": "right"},
        # Page 6: Q10 left (D left 544.2)
        10: {"page": 6, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 564.2}, "column": "left"},
        # Page 7: Q11 left (D left 374.8), Q12 left (D left 621.9), Q13 right (D right 654.3)
        11: {"page": 7, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 394.8}, "column": "left"},
        12: {"page": 7, "clipRectPt": {"x0": 20.0, "y0": 394.8, "x1": 271.4, "y1": 641.9}, "column": "left"},
        13: {"page": 7, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 674.3}, "column": "right"},
        # Page 8: Q14 left (D left 636.5), Q15 left (D left ?), Q16 right (D right 353.0), Q17 right (D right ?)
        14: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 656.5}, "column": "left"},
        15: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 656.5, "x1": 271.4, "y1": 709.5}, "column": "left"},
        16: {"page": 8, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 373.0}, "column": "right"},
        17: {"page": 8, "clipRectPt": {"x0": 281.4, "y0": 373.0, "x1": 532.8, "y1": 709.5}, "column": "right"},
        # Page 9: Q18 left (D left 234.3), Q19 left (D left 622.7), Q20 right (D right ?)
        18: {"page": 9, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 254.3}, "column": "left"},
        19: {"page": 9, "clipRectPt": {"x0": 20.0, "y0": 254.3, "x1": 271.4, "y1": 642.7}, "column": "left"},
        20: {"page": 9, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},
    },
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def re_crop_question(pdf_path: Path, subj: str, qnum: int, fix: dict, output_dir: Path):
    page_idx = fix["page"] - 1
    clip = fix["clipRectPt"]
    
    doc = fitz.open(str(pdf_path))
    page = doc[page_idx]
    
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    
    sx = img.width / float(page.rect.width)
    sy = img.height / float(page.rect.height)
    
    box = (round(clip["x0"] * sx), round(clip["y0"] * sy),
           round(clip["x1"] * sx), round(clip["y1"] * sy))
    
    cropped = img.crop(box)
    if cropped.width == 0 or cropped.height == 0:
        print(f"  ERROR: Empty crop for {subj} Q{qnum}")
        return False
    
    old_path = output_dir / f"MEB-LGS-2016-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2016-{subj.upper()}-Q{qnum:02d}.png.bak")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    h = clip['y1'] - clip['y0']
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} col={fix['column']} h={h:.1f}pt")
    return True


def update_manifest(subj: str, qnum: int, fix: dict):
    manifest_path = REPO / "lgs_18_26" / subj / "manifest_2016.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    for q in manifest["questions"]:
        if q["questionNumber"] == qnum:
            q["visual"]["clipRectPt"] = fix["clipRectPt"]
            q["page"] = fix["page"]
            break
    
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Manifest updated: {subj} Q{qnum}")


def main():
    pdf_sozel = INPUT_DIR / "2016 Sözel.pdf"
    output_dir = REPO / "lgs_18_26" / "turkce"
    
    for qnum in range(1, 21):
        fix = FIXES["turkce"][qnum]
        re_crop_question(pdf_sozel, "turkce", qnum, fix, output_dir)
        update_manifest("turkce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in range(1, 21):
        src_png = output_dir / f"MEB-LGS-2016-TURKCE-Q{qnum:02d}.png"
        target = dst / f"2016-turkce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Turkce tamamlandı!")


if __name__ == "__main__":
    main()