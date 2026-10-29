#!/usr/bin/env python3
"""
R2'ye görsel yükleme: deduplication + WebP + manifest mapping.

Canonical kaynaklar:
- lgs_18_26/{subject}/ → 1080 resmi LGS sorusu
- lgs_çalışma_soruları/{subject}/ → ~3975 çalışma sorusu

Çıktı:
- R2 bucket'a WebP yükleme
- image_map.json: {local_path: {r2_url, sha256, webp_size, width, height}}
- manifest_mapping.json: {question_id: r2_url} manifest güncellemesi için
"""
from __future__ import annotations
import hashlib, json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Optional

try:
    from PIL import Image
except ImportError:
    print("Pillow gerekli: pip install pillow")
    sys.exit(1)

try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("boto3 gerekli: pip install boto3")
    sys.exit(1)

# ─── Config ──────────────────────────────────────────────────────
REPO = Path("/home/selam/roller/web/lgs-ai-coach")
CANONICAL_SOURCES = [
    REPO / "lgs_18_26" / "turkce",
    REPO / "lgs_18_26" / "matematik",
    REPO / "lgs_18_26" / "fen-bilimleri",
    REPO / "lgs_18_26" / "inkilap-tarihi",
    REPO / "lgs_18_26" / "din-kulturu",
    REPO / "lgs_18_26" / "ingilizce",
    REPO / "lgs_çalışma_soruları" / "turkce",
    REPO / "lgs_çalışma_soruları" / "matematik",
    REPO / "lgs_çalışma_soruları" / "fen",
    REPO / "lgs_çalışma_soruları" / "inkilap-tarihi",
    REPO / "lgs_çalışma_soruları" / "ingilizce",
    REPO / "lgs_çalışma_soruları" / "din-kulturu",
]

# R2 config (env'den al)
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.environ.get("R2_BUCKET", "lgs-ai-coach")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL")  # https://pub-xxx.r2.dev

if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, R2_PUBLIC_URL]):
    print("R2 credentials eksik. Şunları export et:")
    print("  export R2_ACCOUNT_ID=...")
    print("  export R2_ACCESS_KEY_ID=...")
    print("  export R2_SECRET_ACCESS_KEY=...")
    print("  export R2_BUCKET=lgs-ai-coach")
    print("  export R2_PUBLIC_URL=https://pub-xxx.r2.dev")
    sys.exit(1)

# S3 client for R2
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(retries={"max_attempts": 3}),
)

OUT_DIR = REPO / "scripts" / "source-ingestion" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_MAP_FILE = OUT_DIR / "image_map.json"
MANIFEST_MAP_FILE = OUT_DIR / "manifest_mapping.json"

# ─── Data classes ────────────────────────────────────────────────
@dataclass
class ImageInfo:
    local_path: str
    sha256: str
    webp_size: int
    width: int
    height: int
    r2_key: str
    r2_url: str
    subject: str
    source_type: str  # "official" or "study"

# ─── Helpers ─────────────────────────────────────────────────────
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def png_to_webp_bytes(png_path: Path) -> tuple[bytes, int, int]:
    """PNG → WebP (lossless), bytes + dimensions döndür."""
    with Image.open(png_path) as im:
        # RGB/RGBA normalize
        if im.mode == "P":
            im = im.convert("RGBA")
        elif im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        width, height = im.size
        from io import BytesIO
        buf = BytesIO()
        im.save(buf, format="WEBP", lossless=True, method=6)
        return buf.getvalue(), width, height

def r2_key_for(subject: str, source_type: str, sha256: str, original_name: str) -> str:
    """R2 object key: subject/source_type/sha256_prefix.webp"""
    prefix = sha256[:16]
    ext = ".webp"
    return f"{subject}/{source_type}/{prefix}{ext}"

def upload_to_r2(key: str, data: bytes, content_type: str = "image/webp") -> bool:
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        return True
    except Exception as e:
        print(f"  ✗ R2 upload failed {key}: {e}")
        return False

# ─── Main ────────────────────────────────────────────────────────
def process_image(png_path: Path, subject: str, source_type: str) -> Optional[ImageInfo]:
    try:
        sha = sha256_file(png_path)
        webp_bytes, w, h = png_to_webp_bytes(png_path)
        key = r2_key_for(subject, source_type, sha, png_path.name)
        r2_url = f"{R2_PUBLIC_URL}/{key}"

        # Upload
        if not upload_to_r2(key, webp_bytes):
            return None

        return ImageInfo(
            local_path=str(png_path),
            sha256=sha,
            webp_size=len(webp_bytes),
            width=w,
            height=h,
            r2_key=key,
            r2_url=r2_url,
            subject=subject,
            source_type=source_type,
        )
    except Exception as e:
        print(f"  ✗ {png_path.name}: {e}")
        return None

def extract_question_id(filename: str) -> Optional[str]:
    """MEB-LGS-2016-TURKCE-Q19.png → MEB-LGS-2016-TURKCE-Q19"""
    if filename.endswith(".png"):
        return filename[:-4]
    return None

def main():
    print("🔍 Canonical kaynaklar taranıyor...")
    all_pngs: list[tuple[Path, str, str]] = []  # (path, subject, source_type)

    for src in CANONICAL_SOURCES:
        if not src.exists():
            print(f"  ⚠️  Yok: {src}")
            continue
        subject = src.name
        # source_type belirle
        if "lgs_18_26" in str(src):
            source_type = "official"
        else:
            source_type = "study"
            # fen-bilimleri → fen normalize
            if subject == "fen-bilimleri":
                subject = "fen"

        pngs = list(src.glob("*.png"))
        print(f"  {subject} ({source_type}): {len(pngs)} PNG")
        for p in pngs:
            all_pngs.append((p, subject, source_type))

    print(f"\nToplam: {len(all_pngs)} PNG")

    # SHA256 bazlı deduplication
    print("\n🔐 SHA256 hesaplanıyor (deduplication)...")
    sha_to_item: dict[str, tuple[Path, str, str]] = {}
    for png_path, subject, source_type in all_pngs:
        sha = sha256_file(png_path)
        if sha not in sha_to_item:
            sha_to_item[sha] = (png_path, subject, source_type)

    unique_items = list(sha_to_item.values())
    print(f"Benzersiz: {len(unique_items)} (duplicate: {len(all_pngs) - len(unique_items)})")

    # Paralel işleme
    print("\n⚙️  WebP dönüştürme + R2 upload...")
    results: list[ImageInfo] = []
    errors = 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process_image, p, sub, st): (p, sub, st) for p, sub, st in unique_items}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            if res:
                results.append(res)
            else:
                errors += 1
            if i % 50 == 0:
                print(f"  {i}/{len(unique_items)} tamamlandı...")

    # Image map kaydet
    image_map = {r.local_path: asdict(r) for r in results}
    IMAGE_MAP_FILE.write_text(json.dumps(image_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ Image map: {IMAGE_MAP_FILE} ({len(results)} öğe)")

    # Manifest mapping: question_id → r2_url
    manifest_map = {}
    for r in results:
        qid = extract_question_id(Path(r.local_path).name)
        if qid:
            manifest_map[qid] = r.r2_url

    MANIFEST_MAP_FILE.write_text(json.dumps(manifest_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Manifest mapping: {MANIFEST_MAP_FILE} ({len(manifest_map)} question_id)")

    # İstatistik
    total_webp = sum(r.webp_size for r in results)
    by_subject = {}
    for r in results:
        by_subject.setdefault(r.subject, {"count": 0, "bytes": 0})
        by_subject[r.subject]["count"] += 1
        by_subject[r.subject]["bytes"] += r.webp_size

    print(f"\n📊 Özet:")
    print(f"  Yüklenen: {len(results)} | Hata: {errors}")
    print(f"  Toplam WebP boyutu: {total_webp/1024/1024:.1f} MB")
    for sub, stats in sorted(by_subject.items()):
        print(f"  {sub}: {stats['count']} görsel, {stats['bytes']/1024/1024:.1f} MB")

if __name__ == "__main__":
    main()