#!/usr/bin/env python3
"""
Upload all exam manifests to R2 for Cloudflare Workers access.
"""

import os
import json
import boto3
from botocore.config import Config
from pathlib import Path

BASE = Path("/home/selam/roller/web/lgs-ai-coach")
EXAMS_BASE = BASE / "lgs_18_26" / "exams_by_month"

# R2 credentials from env
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

# Upload each month's manifest
for month_dir in sorted(EXAMS_BASE.iterdir()):
    if not month_dir.is_dir():
        continue
    
    # Match month directory pattern
    import re
    match = re.match(r'^(\d{2})_ay$', month_dir.name) or re.match(r'^00_seviye_tespit$', month_dir.name)
    if not match:
        continue
    
    month = 0 if month_dir.name == "00_seviye_tespit" else int(match.group(1))
    manifest_file = month_dir / f"manifest_{month_dir.name}.json"
    
    if not manifest_file.exists():
        print(f"Skipping {month_dir.name}: manifest not found")
        continue
    
    print(f"Uploading month {month} manifest...")
    
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # Update image paths to use R2 URLs
    R2_PUBLIC_URL = f"https://pub-{R2_ACCOUNT_ID}.r2.dev"
    for q in manifest.get("questions", []):
        q["imagePath"] = f"{R2_PUBLIC_URL}/exams/{manifest['monthName']}/{q['subject']}/{q['file']}"
    
    # Save updated manifest locally
    updated_manifest = manifest_file.with_suffix(".updated.json")
    with open(updated_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))
    
    # Upload to R2
    s3.upload_file(
        str(updated_manifest),
        R2_BUCKET,
        f"exam_manifests/manifest_{month_dir.name}.json",
        ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=31536000, immutable"}
    )
    print(f"  ✓ Uploaded to R2: exam_manifests/manifest_{month_dir.name}.json")
    
    # Also upload subject directories (PNG images)
    for subject_dir in month_dir.iterdir():
        if not subject_dir.is_dir():
            continue
        for img_file in subject_dir.glob("*.png"):
            s3.upload_file(
                str(img_file),
                R2_BUCKET,
                f"exams/{manifest['monthName']}/{subject_dir.name}/{img_file.name}",
                ExtraArgs={"ContentType": "image/png", "CacheControl": "public, max-age=31536000, immutable"}
            )
        print(f"  ✓ Uploaded {subject_dir.name} images")

# Also upload exam list index
months_list = []
for month_dir in sorted(EXAMS_BASE.iterdir()):
    if not month_dir.is_dir():
        continue
    match = re.match(r'^(\d{2})_ay$', month_dir.name) or re.match(r'^00_seviye_tespit$', month_dir.name)
    if not match:
        continue
    month = 0 if month_dir.name == "00_seviye_tespit" else int(match.group(1))
    manifest_file = month_dir / f"manifest_{month_dir.name}.json"
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        months_list.append({
            "month": m["month"],
            "monthName": m["monthName"],
            "totalQuestions": m["totalQuestions"],
            "durationMinutes": m["durationMinutes"]
        })

with open("/tmp/exams_list.json", "w", encoding="utf-8") as f:
    json.dump({"months": months_list}, f, ensure_ascii=False, separators=(",", ":"))

s3.upload_file(
    "/tmp/exams_list.json",
    R2_BUCKET,
    "exam_manifests/exams_list.json",
    ExtraArgs={"ContentType": "application/json", "CacheControl": "public, max-age=31536000, immutable"}
)
print(f"\n✓ Uploaded exams_list.json to R2")

print("\nDone! All exam manifests uploaded to R2.")