#!/bin/bash
# türkce eksik analiz — manifest'te olup analysis.jsonl'de olmayan soruları çalıştırır.
# Resumable. Tek işçi (SHARDS=1).
set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
SUBJ=turkce
MODEL=minicpm-v:latest

ONLY=$($PY - <<'PY'
import json, os
from pathlib import Path
d = Path('/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce')
qs = json.loads((d/'manifest.json').read_text(encoding='utf-8'))['questions']
recs = [json.loads(l) for l in (d/'analysis.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
done = {os.path.basename(r['file']) for r in recs}
missing = [q['file'] for q in qs if os.path.basename(q['file']) not in done]
print(','.join(missing))
PY
)

N=$(echo "$ONLY" | tr ',' '\n' | grep -c .)
echo "=== eksik analiz: $N soru ==="
if [ "$N" -eq 0 ]; then echo "hiç eksik yok"; exit 0; fi

$PY scripts/source-ingestion/analyze_study_workbook.py \
  --subject "$SUBJ" \
  --provider ollama \
  --ollama-model "$MODEL" \
  --only "$ONLY"

echo "=== SON KONTROL ==="
$PY - <<'PY'
import json, os
from pathlib import Path
d = Path('/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce')
qs = json.loads((d/'manifest.json').read_text(encoding='utf-8'))['questions']
recs = [json.loads(l) for l in (d/'analysis.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
done = {os.path.basename(r['file']) for r in recs}
miss = [q['file'] for q in qs if os.path.basename(q['file']) not in done]
print(f"manifest={len(qs)}  analysis={len(recs)}  kalan eksik={len(miss)}")
PY