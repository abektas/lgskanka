#!/bin/bash
# 2015 LGS analiz — text-first hybrid, tek işçi (SHARDS=1), resumable.
# Her ders için manifest_2015.json okunur, analysis_2015.jsonl'e yazılır.
set -u
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
A=scripts/source-ingestion/analyze_text_mode.py
BASE=lgs_18_26
LOG=logs/analysis_2015.log
mkdir -p logs

declare -A SUBJ=(
  [turkce]=turkce
  [matematik]=matematik
  [fen-bilimleri]=fen-bilimleri
  [ingilizce]=ingilizce
  [din-kulturu]=din-kulturu
  [inkilap-tarihi]=inkilap-tarihi
)

for pass in $(seq 1 5); do
  ALL_DONE=1
  for slug in turkce matematik fen-bilimleri ingilizce din-kulturu inkilap-tarihi; do
    MAN="$BASE/$slug/manifest_2015.json"
    OUT="$BASE/$slug/analysis_2015_ai.jsonl"
    [ -f "$MAN" ] || continue
    TOTAL=$(python3 -c "import json;print(len(json.load(open('$MAN'))['questions']))")
    DONE=$( [ -f "$OUT" ] && wc -l < "$OUT" || echo 0 )
    if [ "$DONE" -lt "$TOTAL" ]; then
      ALL_DONE=0
      echo "[$(date +%H:%M:%S)] $slug: $DONE/$TOTAL" | tee -a "$LOG"
      "$PY" "$A" --manifest "$MAN" --output "$OUT" --subject "${SUBJ[$slug]}" \
        --model gemma3:4b --crop-dir "$BASE/$slug" 2>&1 | tee -a "$LOG"
    else
      echo "[$(date +%H:%M:%S)] $slug: TAMAM ($DONE/$TOTAL)" | tee -a "$LOG"
    fi
  done
  [ "$ALL_DONE" -eq 1 ] && { echo "[$(date +%H:%M:%S)] TÜMÜ TAMAMLANDI" | tee -a "$LOG"; exit 0; }
done
echo "[$(date +%H:%M:%S)] pass limiti doldu" | tee -a "$LOG"