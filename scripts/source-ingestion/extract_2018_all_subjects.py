#!/usr/bin/env python3
"""Crop all 2018 LGS PDFs into complete question PNGs."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pdfplumber

INPUT_DIR = Path("/home/selam/İndirilenler/Lgs_2018")
OUTPUT_DIR = Path("/home/selam/.hermes/cache/scratch/nuli-2018-all-subjects-20pt")
YEAR = 2018
EDUCATIONAL_PERIOD = "2017-2018"
DPI = 300
MARGIN_PT = 20.0
FOOTER_PT = 70.0
QUESTION_RE = re.compile(r"^(\d{1,2})\.$")

SUBJECTS = [
    {"slug": "turkce", "file": "2018 LGS Türkçe.pdf", "name": "Türkçe", "count": 20},
    {"slug": "fen-bilimleri", "file": "2018 LGS Fen Bilimleri.pdf", "name": "Fen Bilimleri", "count": 20},
    {"slug": "matematik", "file": "2018 LGS Matematik.pdf", "name": "Matematik", "count": 20},
    {"slug": "din-kulturu", "file": "2018 LGS Din Kültürü.pdf", "name": "Din Kültürü ve Ahlak Bilgisi", "count": 10},
    {"slug": "ingilizce", "file": "2018 LGS İngilizce.pdf", "name": "Yabancı Dil (İngilizce)", "count": 10},
    {"slug": "inkilap-tarihi", "file": "2018 LGS İnkılap Tarihi.pdf", "name": "T.C. İnkılap Tarihi ve Atatürkçülük", "count": 10},
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def answer_candidates(pdf: Path) -> dict[str, str]:
    """Extract answer-key candidates from the final PDF page only."""
    try:
        page_count = int(subprocess.check_output(["pdfinfo", str(pdf)], text=True).split("Pages:")[1].splitlines()[0].strip())
        text = subprocess.check_output(["pdftotext", "-f", str(page_count), "-l", str(page_count), "-layout", str(pdf), "-"], text=True)
    except (subprocess.CalledProcessError, IndexError, ValueError):
        return {}
    answers: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split()
        for index, part in enumerate(parts[:-1]):
            if part.endswith(".") and part[:-1].isdigit() and parts[index + 1] in "ABCD":
                answers[part[:-1]] = parts[index + 1]
    return answers


def candidate_anchors(page, page_number: int, expected: set[int]) -> list[tuple[int, float, float]]:
    found: dict[int, list[tuple[int, float, float]]] = {}
    for word in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
        match = QUESTION_RE.fullmatch(str(word.get("text", "")).strip())
        if not match:
            continue
        number = int(match.group(1))
        if number not in expected:
            continue
        x0 = float(word["x0"])
        top = float(word["top"])
        if page_number == 1 and top < 130.0:
            continue
        near_column_edge = x0 <= 80.0 or page.width / 2 - 5.0 <= x0 <= page.width / 2 + 55.0
        if not near_column_edge:
            continue
        found.setdefault(number, []).append((number, x0, top))
    # The first occurrence of the expected question number is the anchor;
    # later same-number occurrences are normally numbers inside a diagram/text.
    return [min(values, key=lambda row: row[2]) for _, values in sorted(found.items())]


def page_anchors(pdf, question_count: int) -> tuple[dict[int, list[tuple[int, float, float]]], list[str]]:
    anchors_by_page: dict[int, list[tuple[int, float, float]]] = {}
    warnings: list[str] = []
    cursor = 1
    for page_number, page in enumerate(pdf.pages[:-1], 1):
        if cursor > question_count:
            break
        page_anchors: list[tuple[int, float, float]] = []
        while cursor <= question_count:
            found = candidate_anchors(page, page_number, set(range(cursor, question_count + 1)))
            by_number = {row[0]: row for row in found}
            if cursor not in by_number:
                break
            page_anchors.append(by_number[cursor])
            cursor += 1
        if page_anchors:
            anchors_by_page[page_number] = page_anchors
    if cursor <= question_count:
        warnings.append(f"Could not locate anchors through question {cursor} of {question_count}")
    return anchors_by_page, warnings


def content_bbox(rendered, page, top_pt: float, limit_pt: float, x0_pt: float, x1_pt: float):
    scale = rendered.width / float(page.width)
    y_start = max(0, int(top_pt * scale))
    y_end = min(rendered.height - 1, int(limit_pt * scale))
    x_start = max(0, int(x0_pt * scale))
    x_end = min(rendered.width, int(x1_pt * scale))
    pixels = rendered.load()
    rows: list[int] = []
    decorative_rows: list[int] = []
    for y in range(y_start, y_end + 1):
        occupied = 0
        dark_pixels = 0
        colored_pixels = 0
        for x in range(x_start, x_end):
            r, g, b = pixels[x, y][:3]
            if min(r, g, b) < 245:
                occupied += 1
                if max(r, g, b) < 180:
                    dark_pixels += 1
                if max(r, g, b) - min(r, g, b) > 45:
                    colored_pixels += 1
        if occupied >= 2:
            if occupied / max(1, x_end - x_start) >= 0.55 and y <= y_start + int(8 * scale):
                decorative_rows.append(y)
            elif dark_pixels >= 2 or colored_pixels < occupied * 0.65:
                rows.append(y)
    if not rows:
        return None
    y0, y1 = min(rows), max(rows)
    cols: list[int] = []
    for x in range(x_start, x_end):
        occupied = 0
        for y in range(y0, y1 + 1):
            r, g, b = pixels[x, y][:3]
            if min(r, g, b) < 245:
                occupied += 1
                if occupied >= 2:
                    cols.append(x)
                    break
    if not cols:
        return None
    return {
        "x0": min(cols) / scale,
        "y0": y0 / scale,
        "x1": (max(cols) + 1) / scale,
        "y1": (y1 + 1) / scale,
        "decorative_bottom": ((max(decorative_rows) + 1) / scale) if decorative_rows else None,
    }


def detect_center_divider_x(rendered, page):
    """Locate the colored ÖDSGM divider so it never enters a crop."""
    scale = rendered.width / float(page.width)
    center = int((page.width / 2) * scale)
    best = None
    for x in range(max(0, center - int(20 * scale)), min(rendered.width, center + int(40 * scale))):
        colored_pixels = 0
        for y in range(rendered.height):
            r, g, b = rendered.getpixel((x, y))
            if max(r, g, b) - min(r, g, b) > 55 and min(r, g, b) < 220:
                colored_pixels += 1
        if best is None or colored_pixels > best[1]:
            best = (x, colored_pixels)
    if best and best[1] >= rendered.height * 0.20:
        return best[0] / scale
    # Some 2023 pages carry the vertical ÖDSGM mark without a strong
    # colored divider. Use the mark's own text position as the collision cap.
    for word in page.extract_words(use_text_flow=False, keep_blank_chars=False) or []:
        text = str(word.get("text", "")).strip().upper()
        if "MGSD" in text or "ÖDSGM" in text:
            x0 = float(word["x0"])
            if page.width / 2 - 35.0 <= x0 <= page.width / 2 + 15.0:
                return x0
    return None


def detect_page_warning_top(page):
    """Find the non-question warning printed below the final question."""
    # Collect all words with their tops, join adjacent words on same line
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
    if not words:
        return None
    # Group words by line (same top rounded)
    lines = {}
    for w in words:
        top = round(float(w["top"]))
        lines.setdefault(top, []).append(w)
    # Warning words must appear as complete words (not substrings like "TEST" in "GREATEST")
    warning_words = {"TEST", "BİTTİ", "GEÇİNİZ", "GEÇINIZ", "KONTROL", "EDİNİZ", "CEVAPLARINIZI", "DİĞERSAYFAYA", "DIĞERSAYFAYA"}
    tops = []
    for top, line_words in lines.items():
        if top <= 450:
            continue
        # Join words on this line
        full_text = " ".join(str(w.get("text", "")).strip().upper() for w in line_words)
        # Split into words to check exact matches
        words_in_line = re.findall(r"[A-ZÇĞİÖŞÜ]+", full_text)
        # Check if any warning word appears as a complete word
        is_warning = any(w in words_in_line for w in warning_words)
        if is_warning:
            tops.append(float(top))
    return min(tops) if tops else None


def crop_specs(page, page_anchors: list[tuple[int, float, float]]):
    two_columns = any(x0 >= page.width / 2 - 5.0 for _, x0, _ in page_anchors) and any(x0 < page.width / 2 - 5.0 for _, x0, _ in page_anchors)
    groups: dict[str, list[tuple[int, float, float]]]
    if two_columns:
        groups = {
            "left": sorted([row for row in page_anchors if row[1] < page.width / 2 - 5.0], key=lambda row: row[2]),
            "right": sorted([row for row in page_anchors if row[1] >= page.width / 2 - 5.0], key=lambda row: row[2]),
        }
        bounds = {
            # Scan columns separately; divider caps are applied after the
            # question envelope is measured.
            "left": (MARGIN_PT, page.width / 2 + MARGIN_PT, 0.0, page.width / 2),
            "right": (page.width / 2 - MARGIN_PT, page.width - MARGIN_PT, page.width / 2 + 10.0, page.width),
        }
    else:
        groups = {"single": sorted(page_anchors, key=lambda row: row[2])}
        # For single-column: scan boundaries = crop boundaries (with margin)
        # NOT full page width, to avoid detecting page numbers, headers, etc.
        single_crop_left = MARGIN_PT
        single_crop_right = page.width - MARGIN_PT
        bounds = {"single": (single_crop_left, single_crop_right, single_crop_left, single_crop_right)}

    specs = []
    rendered = page.to_image(resolution=72).original.convert("RGB")
    divider_x = detect_center_divider_x(rendered, page)
    # Apply divider cap ONLY for two-column layouts
    if divider_x is not None and "left" in bounds:
        # Two-column: cap both sides to keep divider/filigree out
        bounds["left"] = (bounds["left"][0], min(bounds["left"][1], divider_x - 5.0), bounds["left"][2], min(bounds["left"][3], divider_x - 5.0))
        bounds["right"] = (max(bounds["right"][0], divider_x + 5.0), bounds["right"][1], max(bounds["right"][2], divider_x + 5.0), bounds["right"][3])
    # For single-column pages, do NOT cap at divider - questions may span full width
    for column, values in groups.items():
        crop_left, crop_right, scan_left, scan_right = bounds[column]
        for index, (number, _x0, anchor_top) in enumerate(values):
            top = max(0.0, anchor_top - MARGIN_PT)
            if page.page_number == 1:
                # 2019 page-1 instruction block ("1. Bu testte ... işaretleyiniz.")
                # ends at ~133 pt. Question anchors sit at 141.5 pt. Keep the 20 pt
                # margin above the question number but never overlap the instruction
                # block; do NOT force a fixed 156 (it cuts the first question line).
                top = max(top, 112.0)
            warning_top = detect_page_warning_top(page)
            if index + 1 < len(values):
                next_limit = values[index + 1][2] - MARGIN_PT
            elif warning_top is not None:
                # Last question on page: use the warning as the boundary
                # instead of the fixed footer, since the warning appears
                # above the page number.
                next_limit = warning_top - MARGIN_PT
            else:
                next_limit = page.height - FOOTER_PT
            # Collision cap: never cross the warning line
            if warning_top is not None:
                next_limit = min(next_limit, warning_top - MARGIN_PT)
            # Start detection at the question anchor, not in the 20 pt margin;
            # otherwise the page header enters the content envelope.
            bbox_scan_top = anchor_top
            # For single-column: use pdfplumber word positions (more accurate at 72 DPI)
            if column == "single":
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
                content_words = [w for w in words if scan_left <= float(w["x0"]) and float(w["x1"]) <= scan_right and bbox_scan_top <= float(w["top"]) <= next_limit]
                if content_words:
                    bbox = {
                        "x0": min(float(w["x0"]) for w in content_words),
                        "y0": min(float(w["top"]) for w in content_words),
                        "x1": max(float(w["x1"]) for w in content_words),
                        "y1": max(float(w["bottom"]) for w in content_words),
                        "decorative_bottom": None,
                    }
                else:
                    bbox = None
            else:
                bbox = content_bbox(rendered, page, bbox_scan_top, next_limit, scan_left, scan_right)
            if bbox:
                content_top = max(top, bbox["y0"] - MARGIN_PT)
                if page.page_number > 1:
                    # The 2024 booklet header ends just above the question row.
                    # Preserve the question number while excluding the header art.
                    content_top = max(content_top, 80.0)
                if bbox["decorative_bottom"] is not None:
                    content_top = max(content_top, bbox["decorative_bottom"] + 1.0)
                bottom = min(float(page.height), next_limit, bbox["y1"] + MARGIN_PT)
                left = max(crop_left, bbox["x0"] - MARGIN_PT)
                right = min(crop_right, bbox["x1"] + MARGIN_PT)
            else:
                content_top, bottom, left, right = top, next_limit, crop_left, crop_right
            specs.append({"question_number": number, "column": column, "rect_pt": {"x0": round(left, 3), "y0": round(content_top, 3), "x1": round(right, 3), "y1": round(bottom, 3)}})
    return sorted(specs, key=lambda spec: spec["question_number"])


def process_subject(subject: dict) -> dict:
    pdf = INPUT_DIR / subject["file"]
    out = OUTPUT_DIR / subject["slug"]
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifestVersion": "1.0",
        "status": "NEEDS_REVIEW",
        "published": False,
        "source": {
            "sourceId": f"MEB-LGS-{YEAR}-{subject['slug'].upper()}",
            "sourceType": "REAL_LGS",
            "fileName": pdf.name,
            "sha256": sha256(pdf),
            "examYear": YEAR,
            "educationalPeriod": EDUCATIONAL_PERIOD,
            "subject": subject["name"],
            "grade": 8,
            "questionCount": subject["count"],
            "answerKeyPage": None,
        },
        "render": {"dpi": DPI, "margin_pt_all_sides": MARGIN_PT, "footer_exclusion_pt": FOOTER_PT, "content_aware_bbox_margin_pt": MARGIN_PT, "reconstructed_from_ocr": False},
        "questions": [],
        "warnings": [],
    }
    with pdfplumber.open(pdf) as pdf_doc:
        manifest["source"]["answerKeyPage"] = len(pdf_doc.pages)
        anchors_by_page, warnings = page_anchors(pdf_doc, subject["count"])
        manifest["warnings"].extend(warnings)
        for page_number, page_anchors_for_page in anchors_by_page.items():
            page = pdf_doc.pages[page_number - 1]
            image = page.to_image(resolution=DPI).original
            sx = image.width / float(page.width)
            sy = image.height / float(page.height)
            for spec in crop_specs(page, page_anchors_for_page):
                number = spec["question_number"]
                path = out / f"q-{number:02d}.png"
                rect = spec["rect_pt"]
                box = (round(rect["x0"] * sx), round(rect["y0"] * sy), round(rect["x1"] * sx), round(rect["y1"] * sy))
                image.crop(box).save(path, "PNG")
                manifest["questions"].append({
                    "id": f"MEB-LGS-{YEAR}-{subject['slug'].upper()}-Q{number:02d}",
                    "questionNumber": number,
                    "page": page_number,
                    "column": spec["column"],
                    "representation": "IMAGE_BACKED",
                    "visual": {"publicPath": f"/pilot-{YEAR}-{subject['slug']}/q-{number:02d}.png", "clipRectPt": rect, "renderDpi": DPI, "authority": "ORIGINAL_MEB_PDF", "reconstructedFromOcr": False, "assetSha256": sha256(path)},
                    "status": "NEEDS_REVIEW",
                    "published": False,
                })
    manifest["questions"].sort(key=lambda item: item["questionNumber"])
    manifest["answerKeyCandidates"] = answer_candidates(pdf)
    manifest["summary"] = {"pagesProcessed": len(anchors_by_page), "questionsExtracted": len(manifest["questions"]), "expectedQuestions": subject["count"], "ambiguousPages": len(manifest["warnings"])}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined = {"manifestVersion": "1.0", "status": "NEEDS_REVIEW", "published": False, "subjects": []}
    for subject in SUBJECTS:
        manifest = process_subject(subject)
        combined["subjects"].append(manifest)
        print(json.dumps({"subject": subject["name"], "summary": manifest["summary"], "answers": len(manifest["answerKeyCandidates"])}, ensure_ascii=False))
    combined["summary"] = {"subjects": len(combined["subjects"]), "questionsExtracted": sum(item["summary"]["questionsExtracted"] for item in combined["subjects"]), "expectedQuestions": sum(item["summary"]["expectedQuestions"] for item in combined["subjects"])}
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"combined": combined["summary"], "output": str(OUTPUT_DIR)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
