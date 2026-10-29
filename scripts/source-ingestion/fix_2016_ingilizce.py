#!/usr/bin/env python3
"""Fix 2016 İngilizce crops from Sözel PDF."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2016")
DPI = 300

FIXES = {
    "ingilizce": {
        # Page 17: Q1 left, Q2 right (no D on page 17, D on page 18)
        1: {"page": 17, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 499.8}, "column": "left"},
        2: {"page": 17, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},
        # Page 18: Q3 left (D left 499.8), Q4 right (D right ?), Q5 right (D right 724.1)
        3: {"page": 18, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 519.8}, "column": "left"},
        4: {"page": 18, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 519.9}, "column": "right"},
        5: {"page": 18, "clipRectPt": {"x0": 281.4, "y0": 519.9, "x1": 532.8, "y1": 744.1}, "column": "right"},
        # Page 19: Q6 left (D left 278.9), Q7 left
        6: {"page": 19, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 298.9}, "column": "left"},
        7: {"page": 19, "clipRectPt": {"x0": 20.0, "y0": 298.9, "x1": 271.4, "y1": 709.5}, "column": "left"},
        # Page 20: Q8 left (D left 323.5), Q9 left (D left 685.2)
        8: {"page": 20, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 343.5}, "column": "left"},
        9: {"page": 20, "clipRectPt": {"x0": 20.0, "y0": 343.5, "x1": 271.4, "y1": 705.2}, "column": "left"},
        # Page 21: Q10 left (D left 425.9)
        10: {"page": 21, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 445.9}, "column": "left"},
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
    output_dir = REPO / "lgs_18_26" / "ingilizce"
    
    for qnum in range(1, 11):
        fix = FIXES["ingilizce"][qnum]
        re_crop_question(pdf_sozel, "ingilizce", qnum, fix, output_dir)
        update_manifest("ingilizce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in range(1, 11):
        src_png = output_dir / f"MEB-LGS-2016-INGILIZCE-Q{qnum:02d}.png"
        target = dst / f"2016-ingilizce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("İngilizce tamamlandı!")


if __name__ == "__main__":
    main()