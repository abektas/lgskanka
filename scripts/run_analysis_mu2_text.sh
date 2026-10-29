#!/bin/bash
# MU2 (mu2_matematik) analysis supervisor — TEXT-first hybrid mode, 1 worker.
# Calls analyze_text_mode.py (PDF text layer + image only for figure questions)
# manifest is manifest_mu2.json (annotated with questionText + hasFigure)
# output is analysis_mu2.jsonl, resumable: files already recorded are skipped
# SHARDS=1, sequential — one worker, so the machine stays usable

set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
SRC="lgs_çalışma_soruları/matematik"
MANIFEST="$SRC/manifest_mu2.json"
OUT="$SRC/analysis_mu2.jsonl"
LOG="logs/analysis_mu2.log"
CROPDIR="$SRC"
mkdir -p logs

for pass in $(seq 1 900); do
  counts=$($PY - "$MANIFEST" "$OUT" <<'PY'
import json, sys
from pathlib import Path
man = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
files = {q['file'] for q in man['questions'] if q.get('file')}
done = set()
outp = Path(sys.argv[2])
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

  $PY scripts/source-ingestion/analyze_text_mode.py \
      --manifest "$MANIFEST" \
      --output "$OUT" \
      --subject matematik \
      --model gemma3:4b \
      --crop-dir "$CROPDIR" >> "$LOG" 2>&1

  sleep 5
done

echo "MAX_PASSES exhausted" >&2
exit 1