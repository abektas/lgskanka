#!/usr/bin/env python3
"""R2'de eksik nesneleri doğrular ve yalnızca eksikleri --remote ile tekrar yükler.

Doğrulama yolları (r2.dev 404 cache'i yanılttığı için kullanılmaz):
- *.webp  -> worker /r2 proxy (R2 binding, doğrudan bucket okur)
- manifestolar -> wrangler r2 object get --remote (cevap anahtarı içerdiğinden
  proxy'den sunulmaz; varlıkları S3 API'den teyit edilir)
"""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request, urllib.error

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
WEBP = REPO / "webp"
BUCKET = "lgs-ai-coach"
PROXY = "https://lgskanka.alibey.workers.dev/r2"
WR = ["node", str(REPO / "node_modules/.bin/wrangler")]

jobs = []
for p in sorted(WEBP.rglob("*.webp")):
    jobs.append((str(p.relative_to(WEBP)), str(p), "image/webp"))
jobs.append(("study_manifests/image_map.json", str(REPO / "scripts/source-ingestion/output/image_map.json"), "application/json"))
jobs.append(("study_manifests/all_questions.json", str(REPO / "scripts/source-ingestion/output/all_questions_with_topics.json"), "application/json"))

print(f"toplam {len(jobs)} nesne kontrol edilecek", flush=True)

def check(key):
    if key.endswith(".webp"):
        # NOT: Python-urllib UA'ları 403 alıyor (bot koruması); curl ile kontrol et.
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "30",
             "-A", "Mozilla/5.0", f"{PROXY}/{key}"],
            capture_output=True, text=True)
        try:
            return key, int(r.stdout.strip())
        except ValueError:
            return key, 0
    # manifestolar: S3 API üzerinden varlık kontrolü
    cmd = WR + ["r2", "object", "get", f"{BUCKET}/{key}", "--file", "/dev/null", "--remote"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    return key, 200 if r.returncode == 0 else 404

missing = []
with ThreadPoolExecutor(max_workers=16) as pool:
    futs = [pool.submit(check, k) for k, _, _ in jobs]
    for i, fu in enumerate(as_completed(futs), 1):
        k, st = fu.result()
        if st != 200:
            missing.append(k)
        if i % 500 == 0:
            print(f"kontrol {i}/{len(jobs)} eksik={len(missing)}", flush=True)

print(f"KONTROL BITTI: eksik={len(missing)}", flush=True)

if not missing:
    sys.exit(0)

by_key = {k: (p, c) for k, p, c in jobs}
done = fail = 0
failures = []

def retry_put(k):
    path, ctype = by_key[k]
    err = ""
    for attempt in range(4):
        cmd = WR + ["r2", "object", "put", f"{BUCKET}/{k}", "--file", path, "--remote",
                    "--content-type", ctype, "--cache-control", "public, max-age=31536000, immutable"]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        if r.returncode == 0:
            return k, True, ""
        err = (r.stderr or r.stdout)[-200:]
        time.sleep(3 * (attempt + 1))
    return k, False, err

with ThreadPoolExecutor(max_workers=5) as pool:
    futs = [pool.submit(retry_put, k) for k in missing]
    for fu in as_completed(futs):
        k, ok, err = fu.result()
        if ok:
            done += 1
        else:
            fail += 1
            failures.append((k, err))
        if (done + fail) % 100 == 0:
            print(f"retry {done + fail}/{len(missing)} tamam={done} hata={fail}", flush=True)

print(f"RETRY BITTI: tamam={done} hata={fail}", flush=True)
for k, e in failures[:20]:
    print("HATA:", k, e, flush=True)