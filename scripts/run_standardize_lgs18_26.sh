#!/bin/bash
# lgs_18_26: dots-ocr -> standartlaştırma -> doğrulama (gemma yok)
set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
TS() { date +%H:%M:%S; }

echo "[$(TS)] OCR basliyor (resumable)"
"$PY" scripts/source-ingestion/ocr_lgs18_26.py
echo "[$(TS)] OCR bitti"

OK=$("$PY" -c "
import json
from pathlib import Path
n = 0
for l in Path('logs/ocr_cache_20261023.jsonl').open():
    try:
        if json.loads(l).get('status') == 'ok':
            n += 1
    except Exception:
        pass
print(n)
")
echo "[$(TS)] OCR kapsami: $OK/1080"
if [ "$OK" -lt 1080 ]; then
  echo "OCR EKSIK — standartlaştırma uygulanmadi"
  exit 1
fi

echo "[$(TS)] Standartlaştırma uygulanıyor"
"$PY" scripts/source-ingestion/standardize_lgs18_26.py --apply

echo "[$(TS)] Dogrulama"
"$PY" scripts/source-ingestion/verify_lgs18_26_standard.py
echo "[$(TS)] TAMAM"
