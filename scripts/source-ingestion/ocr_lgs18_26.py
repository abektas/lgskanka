#!/usr/bin/env python3
"""lgs_18_26 dots-ocr — tüm yıllar (2015-2026) ve dersler.

Evren API dots-ocr ile her soru PNG'sinden metin çıkarır; resumable cache.
Tek işçi (seri çağrı), rate-limit dostu, kırılınca kaldığı yerden devam eder.

Çıktı: lgs_18_26/_ocr_cache_20261023.jsonl  (key = "<ders>/<dosya>")
  {"key","status":"ok|missing_png|error","text","error","sec","at"}

Kullanım:
  python3 ocr_lgs18_26.py           # OCR (resumable)
  python3 ocr_lgs18_26.py --stats   # yalnızca durum özeti
"""
from __future__ import annotations
import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
CACHE = REPO / "logs" / "ocr_cache_20261023.jsonl"
API = "https://evren-llmapi.ssyz.org.tr/v1/ocr"
SUBJECTS = ["turkce", "matematik", "fen-bilimleri", "inkilap-tarihi", "din-kulturu", "ingilizce"]
YEARS = list(range(2015, 2027))


def load_key():
    p = Path.home() / ".hermes" / ".env"
    for line in p.read_text().splitlines():
        if line.strip().startswith("EVREN_API_KEY"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip().strip('"').strip("'")
    sys.exit("EVREN_API_KEY yok")


KEY = load_key()


def ocr(png: Path):
    b64 = base64.b64encode(png.read_bytes()).decode()
    payload = json.dumps({"model": "dots-ocr",
                          "image": f"data:image/png;base64,{b64}"}).encode()
    last = ""
    for attempt in range(5):
        req = urllib.request.Request(API, data=payload, method="POST",
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r).get("text", ""), None
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:160]
            last = f"HTTP {e.code}: {body}"
            if e.code == 429 or e.code >= 500:
                time.sleep(15 * (attempt + 1))
                continue
            return "", last
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(8 * (attempt + 1))
    return "", last


def collect_jobs():
    """(key, png_path) listesi — manifest_<year>.json içindeki soru PNG'leri."""
    jobs, seen = [], set()
    for sub in SUBJECTS:
        d = BASE / sub
        if not d.is_dir():
            continue
        for y in YEARS:
            man = d / f"manifest_{y}.json"
            if not man.exists():
                continue
            for q in json.loads(man.read_text(encoding="utf-8")).get("questions", []):
                fn = q.get("file")
                if not fn:
                    continue
                key = f"{sub}/{Path(fn).name}"
                if key in seen:
                    continue
                seen.add(key)
                jobs.append((key, d / Path(fn).name))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    cache = {}
    if CACHE.exists():
        for line in CACHE.open(encoding="utf-8"):
            try:
                d = json.loads(line)
                cache[d["key"]] = d
            except Exception:  # noqa: BLE001
                pass

    jobs = collect_jobs()
    done = [k for k, _ in jobs if k in cache and cache[k].get("status") == "ok"]
    bad = [k for k, _ in jobs if k in cache and cache[k].get("status") != "ok"]
    print(f"TOPLAM {len(jobs)} PNG | ok {len(done)} | hatalı {len(bad)} | "
          f"kalan {len(jobs) - len(done) - len(bad)}")
    if args.stats:
        if bad:
            print("hatalı anahtarlar (ilk 10):", bad[:10])
        return 0

    todo = [(k, p) for k, p in jobs
            if cache.get(k, {}).get("status") not in ("ok",)]
    if not todo:
        print("OCR TAMAM")
        return 0

    with CACHE.open("a", encoding="utf-8") as cf:
        for i, (key, png) in enumerate(todo, 1):
            t0 = time.time()
            if not png.exists():
                rec = {"key": key, "status": "missing_png", "text": ""}
            else:
                text, err = ocr(png)
                rec = {"key": key, "status": "ok" if not err else "error",
                       "text": text, "error": err or ""}
            rec["sec"] = round(time.time() - t0, 1)
            rec["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            cf.flush()
            n = len(done) + i
            if i % 20 == 0 or i == len(todo) or rec["status"] != "ok":
                print(f"[{n}/{len(jobs)}] {key} {rec['status']} {rec['sec']}s", flush=True)
    print("OCR TAMAM" if bad == [] else "OCR BİTTİ (hatalı anahtarlar cache'de)")
    return 0


if __name__ == "__main__":
    sys.exit(main())