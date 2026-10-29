#!/usr/bin/env python3
"""Fix 2015 Türkçe all problematic crops - precise D option positions."""
import json
import hashlib
from pathlib import Path
import fitz
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
INPUT_DIR = Path("/home/selam/roller/web/kaynak dosyalar/Lgs_soruları/lgs 2015")
DPI = 300

# Precise crop bounds based on actual D option positions from PDF
# Format: qnum: {page, clipRectPt, column}
# D option positions from PDF analysis:
# Page 3: Q1 left D=326.8, Q2 right D=314.8, Q3 right D=636.7, Q4 left D=693.2
# Page 4: Q5 left D=417.8(x=143), Q6 right D=677.7, Q7 right D=374.8
# Page 5: Q8 left D=386.8, Q9 right D=446.1
# Page 6: Q10 right?, Q11 right?
# Page 8: Q14 left D=634.5, Q15 right D=374.8
# Page 9: Q16 single D=390.8
# Page 10: Q17 left D=225.8, Q18 left D=611.3, Q19 right D=326.8, Q20 right D=628.3

FIXES = {
    "turkce": {
        # Page 3: Q1 left (D=326.8), Q2 right (D=314.8), Q3 right (D=636.7), Q4 left (D=693.2)
        1:  {"page": 3, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 346.8}, "column": "left"},   # D=326.8+20
        2:  {"page": 3, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 334.8}, "column": "right"},  # D=314.8+20
        3:  {"page": 3, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 656.7}, "column": "right"},  # D=636.7+20
        4:  {"page": 3, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 713.2}, "column": "left"},   # D=693.2+20 (page bottom)

        # Page 4: Q5 left, Q6 left, Q7 right
        5:  {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 437.8}, "column": "left"},   # D≈417.8+20
        6:  {"page": 4, "clipRectPt": {"x0": 20.0, "y0": 437.8, "x1": 271.4, "y1": 697.7}, "column": "left"},   # D=677.7+20
        7:  {"page": 4, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 394.8}, "column": "right"},  # D=374.8+20

        # Page 5: Q8 left D=386.8, Q9 right D=446.1
        8:  {"page": 5, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 406.8}, "column": "left"},   # D=386.8+20
        9:  {"page": 5, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 466.1}, "column": "right"},  # D=446.1+20

        # Page 6: Q10 right?, Q11 right?
        10: {"page": 6, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},  # full right
        11: {"page": 6, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 709.5}, "column": "right"},  # full right

        # Page 8: Q14 left (D=634.5), Q15 right (D=374.8)
        14: {"page": 8, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 654.5}, "column": "left"},   # D=634.5+20
        15: {"page": 8, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 394.8}, "column": "right"},  # D=374.8+20

        # Page 9: Q16 single D=390.8
        16: {"page": 9, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 532.8, "y1": 410.8}, "column": "single"},

        # Page 10: Q17 left D=225.8, Q18 left D=611.3, Q19 right D=326.8, Q20 right D=628.3
        17: {"page": 10, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 245.8}, "column": "left"},   # D=225.8+20
        18: {"page": 10, "clipRectPt": {"x0": 20.0, "y0": 78.7, "x1": 271.4, "y1": 631.3}, "column": "left"},   # D=611.3+20
        19: {"page": 10, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 346.8}, "column": "right"},  # D=326.8+20
        20: {"page": 10, "clipRectPt": {"x0": 281.4, "y0": 78.7, "x1": 532.8, "y1": 648.3}, "column": "right"},  # D=628.3+20
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
    
    old_path = output_dir / f"MEB-LGS-2015-{subj.upper()}-Q{qnum:02d}.png"
    if old_path.exists():
        old_path.rename(output_dir / f"MEB-LGS-2015-{subj.upper()}-Q{qnum:02d}.png.bak")
    
    cropped.save(old_path, "PNG")
    asset_hash = sha256(old_path)
    h = clip['y1'] - clip['y0']
    print(f"  Fixed {subj} Q{qnum}: page={fix['page']} col={fix['column']} h={h:.1f}pt crop=({clip['x0']:.1f},{clip['y0']:.1f})-({clip['x1']:.1f},{clip['y1']:.1f})")
    return True


def update_manifest(subj: str, qnum: int, fix: dict):
    manifest_path = REPO / "lgs_18_26" / subj / "manifest_2015.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    for q in manifest["questions"]:
        if q["questionNumber"] == qnum:
            q["visual"]["clipRectPt"] = fix["clipRectPt"]
            q["page"] = fix["page"]
            break
    
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Manifest updated: {subj} Q{qnum}")


def main():
    pdf_sozel = INPUT_DIR / "2015 Sözel.pdf"
    output_dir = REPO / "lgs_18_26" / "turkce"
    
    for qnum in sorted(FIXES["turkce"].keys()):
        fix = FIXES["turkce"][qnum]
        re_crop_question(INPUT_DIR / "2015 Sözel.pdf", "turkce", qnum, fix, output_dir)
        update_manifest("turkce", qnum, fix)
    
    import shutil
    dst = REPO / "public" / "exams"
    for qnum in FIXES["turkce"].keys():
        src_png = output_dir / f"MEB-LGS-2015-TURKCE-Q{qnum:02d}.png"
        target = dst / f"2015-turkce-q{qnum:02d}.png"
        if src_png.exists():
            shutil.copy2(src_png, target)
            print(f"  Copied: {target.name}")
    
    print("Türkçe tüm sorular tamamlandı!")


if __name__ == "__main__":
    main()