#!/usr/bin/env python3
"""
Split all_questions.json into per-subject files to reduce Cloudflare Worker CPU usage.
Each subject file is much smaller and faster to parse.

Usage:
  python3 scripts/split_questions_by_subject.py
  
Then upload the files to R2:
  wrangler r2 object put lgs-ai-coach/study_manifests/questions_turkce.json --file=scripts/output/questions_turkce.json --remote
  (repeat for each subject)
"""
import json
import os
import sys

SUBJECTS = ["turkce", "matematik", "fen", "inkilap-tarihi", "din-kulturu", "ingilizce"]

def main():
    # Try to find all_questions.json
    possible_paths = [
        "scripts/source-ingestion/data/questions/all_questions.json",
        "data/all_questions.json",
        "public/study_manifests/all_questions.json",
        "scripts/output/all_questions.json",
    ]
    
    source_path = None
    for p in possible_paths:
        if os.path.exists(p):
            source_path = p
            break
    
    if not source_path:
        print(f"ERROR: all_questions.json not found. Checked: {possible_paths}")
        print("Please provide the path to all_questions.json")
        sys.exit(1)
    
    print(f"Loading {source_path}...")
    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    questions = data.get("questions", [])
    print(f"Total questions: {len(questions)}")
    
    # Group by subject
    by_subject = {}
    for q in questions:
        subject = q.get("_subject") or q.get("subject") or "unknown"
        if subject not in by_subject:
            by_subject[subject] = []
        by_subject[subject].append(q)
    
    # Create output directory
    os.makedirs("scripts/output", exist_ok=True)
    
    # Write per-subject files
    for subject in SUBJECTS:
        subject_questions = by_subject.get(subject, [])
        output = {"questions": subject_questions, "count": len(subject_questions)}
        output_path = f"scripts/output/questions_{subject}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, separators=(",", ":"))
        size = os.path.getsize(output_path)
        print(f"  {subject}: {len(subject_questions)} questions, {size:,} bytes ({size/1024:.0f} KB)")
    
    # Also write a combined file (for reference)
    combined_path = "scripts/output/all_questions_combined.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(combined_path)
    print(f"\nCombined: {len(questions)} questions, {size:,} bytes ({size/1024:.0f} KB)")
    
    print("\nNext steps:")
    print("1. Upload per-subject files to R2:")
    for subject in SUBJECTS:
        print(f"   wrangler r2 object put lgs-ai-coach/study_manifests/questions_{subject}.json --file=scripts/output/questions_{subject}.json --remote")
    print("2. Update app/api/study/route.ts to load per-subject files")

if __name__ == "__main__":
    main()