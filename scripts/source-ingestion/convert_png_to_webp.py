#!/usr/bin/env python3
"""
PNG → WebP dönüştürme + SHA256 deduplication (R2 upload gerektirmez).

Çıktı:
- webp/ dizininde WebP dosyaları
- scripts/source-ingestion/output/image_map.json (yerel WebP mapping)
- scripts/source-ingestion/output/manifest_mapping.json (question_id → dosya adı)
"""
from __future__ import annotations
import hashlib, json, os, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from dataclasses import dataclass, asdict
from typing import Optional

try:
    from PIL import Image
except ImportError:
    print("Pillow gerekli: pip install pillow")
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

WEBP_DIR = REPO / "webp"
OUT_DIR = REPO / "scripts" / "source-ingestion" / "output"
IMAGE_MAP_FILE = OUT_DIR / "image_map.json"
MANIFEST_MAP_FILE = OUT_DIR / "manifest_mapping.json"

# ─── Data classes ────────────────────────────────────────────────
@dataclass
class ImageInfo:
    local_path: str
    webp_path: str
    sha256: str
    webp_size: int
    png_size: int
    width: int
    height: int
    subject: str
    source_type: str  # "official" or "study"

# ─── Helpers ─────────────────────────────────────────────────────
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def png_to_webp_file(png_path: Path, webp_path: Path) -> tuple[int, int, int]:
    """PNG → WebP (lossless). Boyut ve boyutları döndür."""
    with Image.open(png_path) as im:
        if im.mode == "P":
            im = im.convert("RGBA")
        elif im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        width, height = im.size
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        im.save(webp_path, format="WEBP", lossless=True, method=6)
    return webp_path.stat().st_size, width, height

def extract_question_id(filename: str) -> Optional[str]:
    """MEB-LGS-2016-TURKCE-Q19.png → MEB-LGS-2016-TURKCE-Q19"""
    if filename.endswith(".png"):
        return filename[:-4]
    return None

# ─── Main ────────────────────────────────────────────────────────
def main():
    print("🔍 Canonical kaynaklar taranıyor...")
    all_pngs: list[tuple[Path, str, str]] = []  # (path, subject, source_type)

    for src in CANONICAL_SOURCES:
        if not src.exists():
            print(f"  ⚠️  Yok: {src}")
            continue
        subject = src.name
        if "lgs_18_26" in str(src):
            source_type = "official"
        else:
            source_type = "study"
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

    # Paralel WebP dönüştürme
    print("\n⚙️  WebP dönüştürme başlatılıyor...")
    start = time.time()
    results: list[ImageInfo] = []
    errors = 0

    def process_item(item: tuple[Path, str, str]) -> Optional[ImageInfo]:
        png_path, subject, source_type = item
        try:
            sha = sha256_file(png_path)
            # WebP dosya adı: subject/source_type/sha_prefix.webp
            prefix = sha[:16]
            webp_rel = f"{subject}/{source_type}/{prefix}.webp"
            webp_path = WEBP_DIR / webp_rel
            webp_size, w, h = png_to_webp_file(png_path, webp_path)
            return ImageInfo(
                local_path=str(png_path),
                webp_path=str(webp_path),
                sha256=sha,
                webp_size=webp_size,
                png_size=png_path.stat().st_size,
                width=w,
                height=h,
                subject=subject,
                source_type=source_type,
            )
        except Exception as e:
            print(f"  ✗ {png_path.name}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(process_item, item): item for item in unique_items}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            if res:
                results.append(res)
            else:
                errors += 1
            if i % 50 == 0:
                print(f"  {i}/{len(unique_items)} tamamlandı...")

    elapsed = time.time() - start

    # Image map kaydet
    image_map = {r.local_path: asdict(r) for r in results}
    IMAGE_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMAGE_MAP_FILE.write_text(json.dumps(image_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ Image map: {IMAGE_MAP_FILE} ({len(results)} öğe)")

    # Manifest mapping: question_id → webp_path
    manifest_map = {}
    for r in results:
        qid = extract_question_id(Path(r.local_path).name)
        if qid:
            manifest_map[qid] = r.webp_path

    MANIFEST_MAP_FILE.write_text(json.dumps(manifest_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ Manifest mapping: {MANIFEST_MAP_FILE} ({len(manifest_map)} question_id)")

    # İstatistik
    total_png = sum(r.png_size for r in results)
    total_webp = sum(r.webp_size for r in results)
    by_subject = {}
    for r in results:
        by_subject.setdefault(r.subject, {"count": 0, "png_bytes": 0, "webp_bytes": 0})
        by_subject[r.subject]["count"] += 1
        by_subject[r.subject]["png_bytes"] += r.png_size
        by_subject[r.subject]["webp_bytes"] += r.webp_size

    print(f"\n📊 Özet ({elapsed:.1f}s):")
    print(f"  Dönüştürülen: {len(results)} | Hata: {errors}")
    print(f"  PNG toplam: {total_png/1024/1024:.1f} MB")
    print(f"  WebP toplam: {total_webp/1024/1024:.1f} MB")
    print(f"  Tasarruf: {(1 - total_webp/total_png)*100:.1f}%")
    print(f"\n  Ders bazında:")
    for sub, stats in sorted(by_subject.items()):
        saving = (1 - stats["webp_bytes"] / max(stats["png_bytes"], 1)) * 100
        print(f"    {sub}: {stats['count']} görsel, {stats['png_bytes']/1024/1024:.1f} MB → {stats['webp_bytes']/1024/1024:.1f} MB ({saving:.0f}% tasarruf)")

if __name__ == "__main__":
    main()