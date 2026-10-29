#!/bin/bash
# cal14 Türkçe analysis runner — resumable, systemd-managed
set -e
cd /home/selam/roller/web/lgs-ai-coach
source .venv/bin/activate

SUBJECT="turkce_cal14"
SHARDS=3
TOTAL=583

while true; do
    DONE=$(python3 -c "
import json
done=set()
try:
    for line in open('lgs_çalışma_soruları/turkce_cal14/analysis.jsonl'):
        done.add(json.loads(line)['file'])
except: pass
print(len(done))
" 2>/dev/null || echo 0)
    
    echo "[$(date +%H:%M:%S)] cal14_turkce: $DONE/$TOTAL done"
    
    if [ "$DONE" -ge "$TOTAL" ]; then
        echo "[$(date +%H:%M:%S)] COMPLETE — all $TOTAL questions analyzed"
        break
    fi
    
    for SHARD in $(seq 1 $SHARDS); do
        python3 scripts/source-ingestion/analyze_study_workbook.py \
            --subject "$SUBJECT" \
            --shards "$SHARDS" --shard "$SHARD" \
            --provider ollama \
            --ollama-model minicpm-v:latest \
            --ollama-resize 448 \
            >> "logs/cal14_analysis_shard${SHARD}.log" 2>&1 &
    done
    
    wait
    sleep 5
done
