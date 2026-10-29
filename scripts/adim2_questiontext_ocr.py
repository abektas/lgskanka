#!/usr/bin/env python3
"""ADIM 2 — dots-ocr ile tum korpusa questionText ekleme (TALIMATNAME).

Kurallar:
  - Goruntuleme PNG kalir; questionText YALNIZCA analiz verisidir.
  - Mevcut kayitlarin uzerine YAZILMAZ; yalnizca alan eklenir. Once yedek alinir.
  - Tek isci (seri cagri), resumable (ocr_cache.jsonl), rate-limit dostu.
  - Metninde "alti cizili / vurgulanan" gecen sorulara underlineDependent: true.
"""
import base64, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_çalışma_soruları"
CACHE = Path("/home/selam/.hermes/cache/scratch/adim2_ocr_cache.jsonl")
API = "https://evren-llmapi.ssyz.org.tr/v1/ocr"

KEY = None
for line in (Path.home() / ".hermes" / ".env").read_text().splitlines():
    if line.strip().startswith("EVREN_API_KEY"):
        parts = line.split("=", 1)
        if len(parts) == 2:
            KEY = parts[1].strip().strip('"').strip("'")
        break
if not KEY:
    sys.exit("EVREN_API_KEY yok")

UNDERLINE_RE = re.compile(
    r"alt[ıi]\s*çizili|alt[ıi]nda\s*çizili|vurgulan\w*|kal[ıi]n\s*(yaz|harf)|i[şs]aretli\s*(s[öo]zc[üu]k|c[üu]mle|ifade)",
    re.IGNORECASE)


def ocr(png: Path):
    b64 = base64.b64encode(png.read_bytes()).decode()
    payload = json.dumps({"model": "dots-ocr", "image": f"data:image/png;base64,{b64}"}).encode()
    last = ""
    for attempt in range(5):
        req = urllib.request.Request(API, data=payload, method="POST",
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r).get("text", ""), None
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            last = f"HTTP {e.code}: {body}"
            if e.code == 429 or e.code >= 500:
                time.sleep(15 * (attempt + 1))
                continue
            return "", last
        except Exception as e:
            last = str(e)
            time.sleep(8 * (attempt + 1))
    return "", last


def main():
    cache = {}
    if CACHE.exists():
        for line in CACHE.open():
            try:
                d = json.loads(line)
                cache[d["key"]] = d
            except Exception:
                pass

    jobs = []
    for sub_dir in sorted(BASE.iterdir()):
        if not sub_dir.is_dir() or sub_dir.name.startswith("_"):
            continue
        for af in sorted(sub_dir.glob("analysis*.jsonl")):
            seen = set()
            for line in af.open():
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                fn = rec.get("file")
                if not fn:
                    continue
                key = f"{sub_dir.name}/{fn}"
                if key in seen:
                    continue
                seen.add(key)
                jobs.append(key)

    todo = [k for k in jobs if k not in cache]
    print(f"TOPLAM {len(jobs)} PNG | tamamlanan {len(cache)} | kalan {len(todo)}", flush=True)

    with CACHE.open("a") as cf:
        for i, key in enumerate(todo):
            sub, fn = key.split("/", 1)
            png = BASE / sub / fn
            t0 = time.time()
            if not png.exists():
                rec = {"key": key, "status": "missing_png", "text": ""}
            else:
                text, err = ocr(png)
                rec = {"key": key, "status": "ok" if not err else "error",
                       "text": text, "error": err or ""}
            rec["sec"] = round(time.time() - t0, 1)
            cf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            cf.flush()
            done = len(cache) + i + 1
            print(f"[{done}/{len(jobs)}] {key} {rec['status']} {rec['sec']}s", flush=True)
    print("OCR ASAMASI TAMAM", flush=True)

    # --- MERGE: yedek + alan ekleme (mevcut alanlar korunur) ---
    bak = BASE / "_yedek_adim2_oncesi_20261022"
    for sub_dir in sorted(BASE.iterdir()):
        if not sub_dir.is_dir() or sub_dir.name.startswith("_"):
            continue
        for af in sorted(sub_dir.glob("analysis*.jsonl")):
            bakdir = bak / sub_dir.name
            bakdir.mkdir(parents=True, exist_ok=True)
            tb = bakdir / af.name
            if not tb.exists():
                tb.write_bytes(af.read_bytes())
            out, changed, empty = [], 0, 0
            for line in af.open():
                try:
                    rec = json.loads(line)
                except Exception:
                    out.append(line)
                    continue
                if "questionText" in rec:
                    out.append(json.dumps(rec, ensure_ascii=False) + "\n")
                    continue
                fn = rec.get("file")
                c = cache.get(f"{sub_dir.name}/{fn}") if fn else None
                if c and c.get("status") == "ok" and c.get("text", "").strip():
                    rec["questionText"] = c["text"]
                    rec["questionTextSource"] = "dots-ocr"
                    rec["ocrAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    if UNDERLINE_RE.search(c["text"]):
                        rec["underlineDependent"] = True
                    changed += 1
                else:
                    rec["questionText"] = ""
                    rec["questionTextStatus"] = (c or {}).get("status", "not_processed")
                    empty += 1
                out.append(json.dumps(rec, ensure_ascii=False) + "\n")
            af.write_text("".join(out))
            print(f"MERGE {sub_dir.name}/{af.name}: +{changed} metin, {empty} bos/eksik", flush=True)
    print("ADIM2 TAMAMLANDI", flush=True)


if __name__ == "__main__":
    main()