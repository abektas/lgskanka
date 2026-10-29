#!/usr/bin/env python3
"""Fix matematik 2017 Q3, Q6, Q20 with correct full-width bounds."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs_2017")
DPI = 300

# Corrected bounds for Matematik from Sayısal PDF - FULL WIDTH for multi-column questions
FIXES = {
    "matematik": {
        # Q3: Page 3 - Spans BOTH columns. Left anchor at top=478, right content at top=478.
        # Options at top=715.2. Full width crop.
        3: {
            "page": 3,
            "clipRectPt": {"x0": 20.0, "y0": 458.0, "x1": 532.8, "y1": 735.2},  # Full width
            "column": "single"
        },
        # Q6: Page 4 - Spans BOTH columns. Left anchor at top=418.4, right has table data.
        # Options: A,B at left top=652.8; C,D at right top=652.8. Full width crop.
        6: {
            "page": 4,
            "clipRectPt": {"x0": 20.0, "y0": 398.4, "x1": 532.8, "y1": 672.8},  # Full width
            "column": "single"
        },
        # Q20: Page 8 - Single column full width. Anchor at top=399.1.
        # Options at top=664.2, visual details (Yeşil/Mavi/Sarı) down to top=704.
        20: {
            "page": 8,
            "clipRectPt": {"x0": 20.0, "y0": 379.1, "x1": 532.8, "y1": 724.2},  # Full width
            "column": "single"
        },
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
    
    old_path = output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2017-{subj.upper()}-Q{qnum:02d}.png.bak6")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f}) hash={asset_hash[:16]}...")
    return True


def update_manifest(subj: str, qnum: int, fix: dict):
    manifest_path = REPO / "lgs_18_26" / subj / "manifest_2017.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    for q in manifest["questions"]:
        if q["questionNumber"] == qnum:
            q["visual"]["clipRectPt"] = fix["clipRectPt"]
            q["page"] = fix["page"]
            break
    
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Manifest updated: {subj} Q{qnum}")


def main():
    pdf_sayisal = INPUT_DIR / "2017 Sayısal.pdf"
    output_dir = REPO / "lgs_18_26" / "matematik"
    
    for qnum, fix in FIXES["matematik"].items():
        re_crop_question(pdf_sayisal, "matematik", qnum, fix, output_dir)
        update_manifest("matematik", qnum, fix)
    
    # Copy to public/exams
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in FIXES["matematik"].keys():
        src_png = output_dir / f"MEB-LGS-2017-MATEMATIK-Q{qnum:02d}.png"
        target = dst / f"2017-matematik-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Tamamlandı!")


if __name__ == "__main__":
    main()