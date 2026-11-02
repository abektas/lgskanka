#!/usr/bin/env python3
"""Split all_questions.json into per-subject pre-processed files."""
import json
import os
import re

BASE = "/home/selam/roller/web/lgs-ai-coach"
R2_PUBLIC_URL = "https://lgskanka.alibey.workers.dev/r2"

# Load source data
with open(f"{BASE}/scripts/source-ingestion/output/all_questions.json", "r") as f:
    all_data = json.load(f)

with open(f"{BASE}/scripts/source-ingestion/output/image_map.json", "r") as f:
    image_map_raw = json.load(f)

# Build image map: filename -> webp R2 key
image_map = {}
for local_path, info in image_map_raw.items():
    name = local_path.split("/")[-1]
    webp_path = info.get("webp_path", "")
    if webp_path:
        r2_key = webp_path.split("/webp/")[1] if "/webp/" in webp_path else ""
        if r2_key:
            image_map[name] = r2_key

print(f"Image map entries: {len(image_map)}")

questions = all_data.get("questions", [])
print(f"Total questions: {len(questions)}")

by_subject = {}
for q in questions:
    if q.get("published") == False or q.get("cancelledInSource"):
        continue
    
    subject = q.get("_subject") or "unknown"
    original_file = q.get("file", "q-" + str(q.get("q", 0)) + ".png")
    qnum = q.get("q") or q.get("questionNumber") or 1
    
    webp_path = image_map.get(original_file)
    if not webp_path:
        basename = original_file.split("/")[-1]
        webp_path = image_map.get(basename)
    
    image_path = R2_PUBLIC_URL + "/" + webp_path if webp_path else None
    
    mebi_match = re.match(r"^mebi", original_file, re.I)
    book_match = re.match(r"^((?:cal|nuli|mu|tu)\d+)", original_file, re.I)
    source_book = "MEBI" if mebi_match else (book_match.group(1).upper() if book_match else "UNKNOWN")
    
    clean_id = original_file.replace(".png", "").upper()
    processed = {
        "id": q.get("id") or ("STUDY-" + subject.upper() + "-" + clean_id),
        "subject": subject,
        "sourceBook": source_book,
        "questionNumber": qnum,
        "page": q.get("page", 0),
        "imagePath": image_path,
        "answer": q.get("answer"),
        "unit": q.get("unit"),
        "unitName": q.get("unitName"),
        "section": q.get("section"),
        "questionText": q.get("questionText"),
    }
    
    by_subject.setdefault(subject, []).append(processed)

os.makedirs(f"{BASE}/scripts/output", exist_ok=True)

SUBJECTS = ["turkce", "matematik", "fen", "inkilap-tarihi", "din-kulturu", "ingilizce"]

for subject in SUBJECTS:
    subject_questions = by_subject.get(subject, [])
    output = {"questions": subject_questions, "count": len(subject_questions)}
    output_path = f"{BASE}/scripts/output/questions_{subject}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(output_path)
    print(f"  {subject}: {len(subject_questions)} questions, {size:,} bytes ({size/1024:.0f} KB)")

total_size = sum(os.path.getsize(f"{BASE}/scripts/output/questions_{s}.json") for s in SUBJECTS)
original_size = os.path.getsize(f"{BASE}/scripts/source-ingestion/output/all_questions.json")
print(f"\nTotal per-subject files: {total_size:,} bytes ({total_size/1024:.0f} KB)")
print(f"Original all_questions.json: {original_size:,} bytes ({original_size/1024:.0f} KB)")
print(f"Reduction: {100 - total_size*100//original_size}%")