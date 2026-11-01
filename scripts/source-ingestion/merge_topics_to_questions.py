#!/usr/bin/env python3
"""
Merge topic_map.json (from classifier) into all_questions.json
so questions have unit/unitName/topic for reinforcement tracking.
"""

import json
import os
import boto3
from botocore.config import Config
from pathlib import Path

BASE = Path("/home/selam/roller/web/lgs-ai-coach")
TOPIC_MAP = BASE / "lgs_18_26" / "exams_by_month" / "topic_map.json"
ALL_QUESTIONS = BASE / "scripts" / "source-ingestion" / "output" / "all_questions.json"
OUT_FILE = BASE / "scripts" / "source-ingestion" / "output" / "all_questions_with_topics.json"

print("Loading topic_map.json...")
with open(TOPIC_MAP, "r", encoding="utf-8") as f:
    topic_map = json.load(f)

print(f"Loaded {len(topic_map)} topic mappings")

print("Loading all_questions.json...")
with open(ALL_QUESTIONS, "r", encoding="utf-8") as f:
    data = json.load(f)

questions = data.get("questions", [])
print(f"Loaded {len(questions)} questions")

# Merge topic data
matched = 0
for q in questions:
    qid = q.get("id")
    if qid in topic_map:
        tm = topic_map[qid]
        q["unit"] = tm.get("unit")
        q["unitName"] = tm.get("unitName")
        q["topic"] = tm.get("topic")
        matched += 1

print(f"Merged topic data for {matched} questions")

# Save
data["questions"] = questions
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print(f"Saved to {OUT_FILE}")

# Upload to R2 using env vars (same as upload_webp_to_r2.py)
print("\nUploading to R2...")
R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET = os.environ["R2_BUCKET"]

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    region_name="auto",
)

s3.upload_file(
    str(OUT_FILE),
    R2_BUCKET,
    "study_manifests/all_questions.json",
    ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=31536000, immutable"}
)
print("Uploaded all_questions.json to R2")

print("\nDone! The study API will cache the new data on next request (or restart worker).")