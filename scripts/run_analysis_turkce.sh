#!/bin/bash
# turkce analysis runner — resumable, systemd-managed
set -e
cd /home/selam/roller/web/lgs-ai-coach
source .venv/bin/activate

SUBJECT="turkce"
SHARDS=3
TOTAL=1203

while true; do
    DONE=$(python3 -c "
import json
done=set()
try:
    for line in open('lgs_çalışma_soruları/turkce/analysis.jsonl'):
        done.add(json.loads(line)['file'])
except: pass
print(len(done))
" 2>/dev/null || echo 0)
    
    echo "[$(date +%H:%M:%S)] turkce: $DONE/$TOTAL done"
    
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
            >> "logs/turkce_analysis_shard${SHARD}.log" 2>&1 &
    done
    
    wait
    sleep 5
done
