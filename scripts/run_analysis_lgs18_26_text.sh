#!/bin/bash
# LGS 18-26 analysis supervisor — TEXT-FIRST hybrid mode, 1 worker, resumable.
#
# Calls analyze_lgs18_26_text.py which uses PDF text layer + image only for figure questions.
# Output is analysis.jsonl in each subject folder, resumable: files already recorded are skipped.
# SHARDS=1, sequential — one worker, so the machine stays usable.
set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
MANIFEST_DIR="/home/selam/roller/web/lgs-ai-coach/lgs_18_26"
PDF_SOURCE_DIR="/home/selam/roller/web/kaynak dosyalar/Lgs_soruları"
LOG="logs/analysis_lgs18_26.log"
mkdir -p logs

for pass in $(seq 1 900); do
  # Count total and done across all subjects
  counts=$($PY - "$MANIFEST_DIR" <<'PY'
import json, sys
from pathlib import Path
base = Path(sys.argv[1])
total = done = 0
for man_file in base.glob("*/manifest_*.json"):
    man = json.loads(man_file.read_text(encoding='utf-8'))
    for q in man.get("questions", []):
        if q.get("file"):
            total += 1
            out_file = base / man_file.parent.name / "analysis.jsonl"
            if out_file.exists():
                for line in out_file.read_text(encoding='utf-8').splitlines():
                    if line.strip():
                        try:
                            if json.loads(line)["file"] == q["file"]:
                                done += 1
                                break
                        except Exception:
                            pass
print(total, done)
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
    echo "[$(date +%H:%M:%S)] ollama yanıt vermiyor, yeniden başlatılıyor" | tee -a "$LOG"
    systemctl --user restart ollama-serve.service
    sleep 10
  fi

  # Run one subject at a time (sequential, single worker)
  for subj in turkce matematik fen-bilimleri ingilizce din-kulturu inkilap-tarihi; do
    OUT="$MANIFEST_DIR/$subj/analysis.jsonl"
    $PY scripts/source-ingestion/analyze_lgs18_26_text.py \
        --manifest-dir "$MANIFEST_DIR" \
        --pdf-source-dir "$PDF_SOURCE_DIR" \
        --output "$OUT" \
        --subject "$subj" \
        --model gemma3:4b >> "$LOG" 2>&1
  done

  sleep 5
done

echo "MAX_PASSES exhausted" >&2
exit 1