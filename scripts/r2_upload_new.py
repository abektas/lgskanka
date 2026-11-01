#!/usr/bin/env python3
"""webp/ + study_manifests JSON'larini yeni R2 kovasina paralel yukler (wrangler OAuth)."""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
WEBP = REPO / "webp"
BUCKET = "lgs-ai-coach"
WR = ["node", str(REPO / "node_modules/.bin/wrangler")]

jobs = []
for p in sorted(WEBP.rglob("*.webp")):
    key = str(p.relative_to(WEBP))
    jobs.append((key, str(p), "image/webp"))
jobs.append(("study_manifests/image_map.json", str(REPO / "scripts/source-ingestion/output/image_map.json"), "application/json"))
jobs.append(("study_manifests/all_questions.json", str(REPO / "scripts/source-ingestion/output/all_questions_with_topics.json"), "application/json"))

print(f"toplam {len(jobs)} nesne", flush=True)
done = fail = 0
failures = []
start = time.time()

def put(job):
    key, path, ctype = job
    cmd = WR + ["r2", "object", "put", f"{BUCKET}/{key}", "--file", path, "--remote",
                "--content-type", ctype, "--cache-control", "public, max-age=31536000, immutable"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    return key, r.returncode, (r.stderr or r.stdout)[-200:]

with ThreadPoolExecutor(max_workers=16) as pool:
    futs = [pool.submit(put, j) for j in jobs]
    for i, fu in enumerate(as_completed(futs), 1):
        key, rc, err = fu.result()
        if rc == 0:
            done += 1
        else:
            fail += 1
            failures.append((key, err))
        if i % 200 == 0:
            print(f"{i}/{len(jobs)} tamam={done} hata={fail} {time.time()-start:.0f}s", flush=True)

print(f"BITTI: tamam={done} hata={fail} sure={time.time()-start:.0f}s", flush=True)
for k, e in failures[:20]:
    print("HATA:", k, e, flush=True)
