#!/usr/bin/env python3
"""WebP dosyalarını R2'ye paralel yükle."""
import json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.config import Config

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
WEBP_DIR = REPO / "webp"
IMAGE_MAP = REPO / "scripts/source-ingestion/output/image_map.json"
OUTPUT_MAP = REPO / "scripts/source-ingestion/output/r2_upload_map.json"

R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET = os.environ["R2_BUCKET"]
R2_PUBLIC_URL = os.environ["R2_PUBLIC_URL"]

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    region_name="auto",
)

webp_files = sorted(WEBP_DIR.rglob("*.webp"))
print(f"Toplam {len(webp_files)} WebP dosyası yüklenecek")
print(f"R2 Bucket: {R2_BUCKET}")
print(f"Public URL: {R2_PUBLIC_URL}")
print()

uploaded = 0
failed = 0
failed_keys = []
start = time.time()
total_bytes = 0

def upload_one(webp_path: Path):
    key = str(webp_path.relative_to(WEBP_DIR))
    try:
        data = webp_path.read_bytes()
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=data,
            ContentType="image/webp",
            CacheControl="public, max-age=31536000, immutable",
        )
        return True, key, len(data), None
    except Exception as e:
        return False, key, 0, str(e)

with ThreadPoolExecutor(max_workers=16) as pool:
    futures = {pool.submit(upload_one, p): p for p in webp_files}
    for i, fut in enumerate(as_completed(futures), 1):
        ok, key, size, err = fut.result()
        if ok:
            uploaded += 1
            total_bytes += size
        else:
            failed += 1
            failed_keys.append(key)
            print(f"  ✗ {key}: {err}")
        if i % 500 == 0 or i == len(webp_files):
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(webp_files) - i) / rate if rate > 0 else 0
            print(f"  {i}/{len(webp_files)} ({rate:.0f}/sn, ETA {eta:.0f}s, {total_bytes/1024/1024:.1f}MB)")

elapsed = time.time() - start
print(f"\n{'='*50}")
print(f"✅ Yükleme tamamlandı!")
print(f"  Başarılı: {uploaded}")
print(f"  Hata: {failed}")
print(f"  Toplam boyut: {total_bytes/1024/1024:.1f} MB")
print(f"  Süre: {elapsed:.1f}s ({uploaded/max(elapsed,0.1):.0f} dosya/sn)")
print(f"  Public URL: {R2_PUBLIC_URL}")

if failed_keys:
    print(f"\n❌ Başarısız dosyalar ({len(failed_keys)}):")
    for k in failed_keys[:20]:
        print(f"  {k}")

# Save R2 mapping
r2_map = {}
for p in webp_files:
    key = str(p.relative_to(WEBP_DIR))
    r2_map[key] = f"{R2_PUBLIC_URL}/{key}"
OUTPUT_MAP.write_text(json.dumps(r2_map, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n📝 R2 mapping kaydedildi: {OUTPUT_MAP} ({len(r2_map)} URL)")