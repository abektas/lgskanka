#!/bin/bash
# ingilizce hybrid text+image analysis - tek işçi
set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
SRC="lgs_çalışma_soruları/ingilizce"
MANIFEST="$SRC/manifest.json"
OUT="$SRC/analysis.jsonl"
LOG="logs/analysis_ingilizce_hybrid.log"
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

  if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[$(date +%H:%M:%S)] ollama yanit vermiyor, yeniden baslatiliyor" | tee -a "$LOG"
    systemctl --user restart ollama-serve.service
    sleep 10
  fi

  $PY scripts/source-ingestion/analyze_text_mode.py \
      --manifest "$MANIFEST" \
      --output "$OUT" \
      --subject ingilizce \
      --model gemma3:4b \
      --crop-dir "$CROPDIR" >> "$LOG" 2>&1

  sleep 5
done

echo "MAX_PASSES exhausted" >&2
exit 1