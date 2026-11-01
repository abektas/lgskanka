#!/usr/bin/env python3
"""R2'de eksik nesneleri doğrular (public URL HEAD) ve yalnızca eksikleri tekrar yükler."""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request, urllib.error

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
WEBP = REPO / "webp"
BUCKET = "lgs-ai-coach"
BASE = "https://pub-ddee1949bfea484b8ea4ec1574e492c6.r2.dev"
WR = ["node", str(REPO / "node_modules/.bin/wrangler")]

jobs = []
for p in sorted(WEBP.rglob("*.webp")):
    jobs.append((str(p.relative_to(WEBP)), str(p), "image/webp"))
jobs.append(("study_manifests/image_map.json", str(REPO / "scripts/source-ingestion/output/image_map.json"), "application/json"))
jobs.append(("study_manifests/all_questions.json", str(REPO / "scripts/source-ingestion/output/all_questions_with_topics.json"), "application/json"))

print(f"toplam {len(jobs)} nesne kontrol edilecek", flush=True)

def head(key):
    req = urllib.request.Request(f"{BASE}/{key}", method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return key, r.status
    except urllib.error.HTTPError as e:
        return key, e.code
    except Exception:
        return key, 0

missing = []
with ThreadPoolExecutor(max_workers=32) as pool:
    futs = [pool.submit(head, k) for k, _, _ in jobs]
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
for k in missing:
    path, ctype = by_key[k]
    ok = False
    for attempt in range(3):
        cmd = WR + ["r2", "object", "put", f"{BUCKET}/{k}", "--file", path, "--remote",
                    "--content-type", ctype, "--cache-control", "public, max-age=31536000, immutable"]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        if r.returncode == 0:
            ok = True
            break
        time.sleep(2 * (attempt + 1))
    if ok:
        done += 1
    else:
        fail += 1
        failures.append((k, (r.stderr or r.stdout)[-200:]))
    if (done + fail) % 50 == 0:
        print(f"retry {done + fail}/{len(missing)} tamam={done} hata={fail}", flush=True)

print(f"RETRY BITTI: tamam={done} hata={fail}", flush=True)
for k, e in failures[:20]:
    print("HATA:", k, e, flush=True)