#!/usr/bin/env python3
"""Generate one representative q1 crop per non-Mathematics 2025 LGS subject."""
from pathlib import Path
import importlib.util
import pdfplumber

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("extractor", ROOT / "extract_2025_other_subjects_pilot.py")
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)

OUT = Path("/home/selam/.hermes/cache/scratch/nuli-2025-subject-samples-20pt")
OUT.mkdir(parents=True, exist_ok=True)

for subject in extractor.SUBJECTS:
    pdf_path = extractor.INPUT_DIR / subject["file"]
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        anchors = extractor.candidate_anchors(page, 1, set(range(1, subject["count"] + 1)))
        q1 = [row for row in anchors if row[0] == 1]
        if not q1:
            raise RuntimeError(f"Q1 anchor not found: {subject['name']}")
        q1_spec = [spec for spec in extractor.crop_specs(page, anchors) if spec["question_number"] == 1][0]
        image = page.to_image(resolution=extractor.DPI).original
        sx = image.width / float(page.width)
        sy = image.height / float(page.height)
        rect = q1_spec["rect_pt"]
        box = (round(rect["x0"] * sx), round(rect["y0"] * sy), round(rect["x1"] * sx), round(rect["y1"] * sy))
        output = OUT / f"{subject['slug']}-q01.png"
        image.crop(box).save(output, "PNG")
        print(f"{subject['name']}: {output} rect_pt={rect} size={image.crop(box).size}")
