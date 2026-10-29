#!/bin/bash
# TU2 Turkish analysis runner - hybrid text+image mode, single worker
# Uses analyze_text_mode.py which reads PDF text layer + attaches image for figure questions
# Resumable: skips already-analyzed questions

set -u
cd /home/selam/roller/web/lgs-ai-coach

PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3
MANIFEST="lgs_çalışma_soruları/turkce/manifest_tu2.json"
OUT="lgs_çalışma_soruları/turkce/analysis_tu2.jsonl"
LOG="logs/tu2_analysis.log"
mkdir -p logs

echo "[$(date +%H:%M:%S)] TU2 Türkçe analizi başlıyor..." | tee "$LOG"
echo "Manifest: $MANIFEST" | tee -a "$LOG"
echo "Output: $OUT" | tee -a "$LOG"
echo "Model: gemma3:4b (hybrid text+image)" | tee -a "$LOG"
echo "Worker: 1 (sequential)" | tee -a "$LOG"

$PY scripts/source-ingestion/analyze_text_mode.py \
    --manifest "$MANIFEST" \
    --output "$OUT" \
    --subject turkce \
    --model gemma3:4b \
    >> "$LOG" 2>&1

echo "[$(date +%H:%M:%S)] Analiz tamamlandı" | tee -a "$LOG"