#!/bin/bash
# tu2_turkce_2023 analysis supervisor — 1 worker, resumable, systemd-owned.
# Runs the resumable analyzer until every manifest question has a record.
# Analyzer skips files already present in analysis.jsonl, so each pass is lossless.
set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
SRC="lgs_çalışma_soruları/turkce"
OUT="lgs_çalışma_soruları/turkce/analysis.jsonl"
LOG="logs/analysis_tu2.log"
mkdir -p logs

for pass in $(seq 1 500); do
  counts=$($PY - "$SRC" "$OUT" <<'PY'
import json, sys
from pathlib import Path
base = Path(sys.argv[1]); outp = Path(sys.argv[2])
man = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
files = {q['file'] for q in man['questions'] if q.get('file')}
done = set()
if outp.exists():
    for line in outp.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try:
                done.add(json.loads(line)['file'])
            except Exception:
                pass
print(len(files), len(files & done))
PY
)
  TOTAL=$(echo "$counts" | awk '{print $1}')
  DONE=$(echo "$counts" | awk '{print $2}')
  echo "[$(date +%H:%M:%S)] pass=$pass  $DONE/$TOTAL" | tee -a "$LOG"

  if [ "$DONE" -ge "$TOTAL" ]; then
    echo "[$(date +%H:%M:%S)] TAMAMLANDI ($DONE/$TOTAL)" | tee -a "$LOG"
    exit 0
  fi

  # Ollama liveness — restart it rather than burning a pass on connection refused
  if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[$(date +%H:%M:%S)] ollama yanit vermiyor, yeniden baslatiliyor" | tee -a "$LOG"
    systemctl --user restart ollama-serve.service
    sleep 10
  fi

  $PY scripts/source-ingestion/analyze_study_workbook.py \
      --subject turkce \
      --source-dir "$SRC" \
      --output "$OUT" \
      --provider ollama \
      --ollama-model gemma3:4b \
      --ollama-resize 256 \
      --shards 1 \
      --shard 1 >> "$LOG" 2>&1

  sleep 5
done

echo "MAX_PASSES exhausted" >&2
exit 1
