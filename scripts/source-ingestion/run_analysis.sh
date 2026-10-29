#!/usr/bin/env bash
# Resumable analysis runner for fen + turkce.
# Restarts itself until both books are complete; each pass only analyzes
# files not already present in analysis.jsonl (the script's own `done` set).
set -u
cd /home/selam/roller/web/lgs-ai-coach
export PATH=/home/selam/.local/bin:$PATH
source .venv/bin/activate

declare -A TOTAL=( [fen]=625 [turkce]=620 )
MAX_PASSES=200

count_done() {
  python3 - "$1" <<'PY'
import json,os,sys
s=sys.argv[1]
aj=f'lgs_çalışma_soruları/{s}/analysis.jsonl'
n=0
if os.path.exists(aj):
    n=len({json.loads(l)['file'] for l in open(aj,encoding='utf-8') if l.strip()})
print(n)
PY
}

for pass in $(seq 1 $MAX_PASSES); do
  for s in fen turkce; do
    rm -f "lgs_çalışma_soruları/$s/analysis_locks/"*.claim 2>/dev/null
  done

  pids=()
  for s in fen turkce; do
    python3 scripts/source-ingestion/analyze_study_workbook.py \
      --subject "$s" --provider auto --shards 2 --shard 1 &
    pids+=($!)
    python3 scripts/source-ingestion/analyze_study_workbook.py \
      --subject "$s" --provider auto --shards 2 --shard 2 &
    pids+=($!)
  done
  wait "${pids[@]}" 2>/dev/null

  fen=$(count_done fen); tr=$(count_done turkce)
  echo "[pass $pass] fen=$fen/${TOTAL[fen]} turkce=$tr/${TOTAL[turkce]}"
  if [ "$fen" -ge "${TOTAL[fen]}" ] && [ "$tr" -ge "${TOTAL[turkce]}" ]; then
    echo "TAMAMLANDI"
    exit 0
  fi
  sleep 10
done
echo "MAX_PASSES aşıldı" >&2
exit 1
