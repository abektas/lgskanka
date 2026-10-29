#!/usr/bin/env bash
# LGS MEBI LGS-2 text-first hybrid analysis (single worker).
set -u
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
ROOT=/home/selam/roller/web/lgs-ai-coach
SRC=$ROOT/lgs_çalışma_soruları
LOG=$ROOT/_mebi_lgs2_analysis.log
: > "$LOG"

run_one() {
  local subj=$1 pdf_kind=$2
  local manifest=$SRC/$subj/manifest_mebi_lgs2.json
  local out=$SRC/$subj/analysis.jsonl
  local cropdir=$SRC/$subj
  echo "[$(date '+%H:%M:%S')] START $subj" | tee -a "$LOG"
  $PY $ROOT/scripts/source-ingestion/analyze_text_mode.py \
      --manifest "$manifest" \
      --output "$out" \
      --subject "$subj" \
      --model gemma3:4b \
      --crop-dir "$cropdir" >> "$LOG" 2>&1
  echo "[$(date '+%H:%M:%S')] DONE $subj (exit $?)" | tee -a "$LOG"
}

run_one turkce sozel
run_one ingilizce sozel
run_one inkilap-tarihi sozel
run_one din-kulturu sozel
run_one matematik sayisal
run_one fen sayisal

echo "[$(date '+%H:%M:%S')] ALL DONE" | tee -a "$LOG"
EOF