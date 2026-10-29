#!/usr/bin/env python3
"""Fix 2016 İnkılap Tarihi crops from Sözel PDF."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300

FIXES = {
    "inkilap-tarihi": {
        # Page 10: Q1 left (D left 413.6), Q2 right (D right 462.5)
        1: {"page": 10, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 433.6}, "column": "left"},
        2: {"page": 10, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 482.5}, "column": "right"},
        # Page 11: Q3 left (D left ?), Q4 left (D left 630.7)
        3: {"page": 11, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 400.0}, "column": "left"},
        4: {"page": 11, "clipRectPt": {"x0": 20.0, "y0": 400.0, "x1": 271.4, "y1": 650.7}, "column": "left"},
        # Page 12: Q5 left (D left 434.8), Q6 right (D right ?), Q7 right (D right ?)
        5: {"page": 12, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 454.8}, "column": "left"},
        6: {"page": 12, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},
        7: {"page": 12, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},
        # Page 13: Q8 left (D left 398.6), Q9 left (D left 712.9), Q10 right (D right ?)
        8: {"page": 13, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 418.6}, "column": "left"},
        9: {"page": 13, "clipRectPt": {"x0": 20.0, "y0": 418.6, "x1": 271.4, "y1": 732.9}, "column": "left"},
        10: {"page": 13, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},
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
    output_dir = REPO / "lgs_18_26" / "inkilap-tarihi"
    
    for qnum in range(1, 11):
        fix = FIXES["inkilap-tarihi"][qnum]
        re_crop_question(pdf_sozel, "inkilap-tarihi", qnum, fix, output_dir)
        update_manifest("inkilap-tarihi", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in range(1, 11):
        src_png = output_dir / f"MEB-LGS-2016-INKILAPTARİHİ-Q{qnum:02d}.png"
        target = dst / f"2016-inkilap-tarihi-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("İnkılap Tarihi tamamlandı!")


if __name__ == "__main__":
    main()