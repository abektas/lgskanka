#!/bin/bash
# cal05 analysis runner — 3 subjects sequentially, resumable
set -e
cd /home/selam/roller/web/lgs-ai-coach
source .venv/bin/activate

SUBJECTS=("inkilap-tarihi" "din-kulturu" "ingilizce")
SHARDS=2

for SUBJECT in "${SUBJECTS[@]}"; do
    TOTAL=$(python3 -c "import json; print(len(json.load(open('lgs_çalışma_soruları/$SUBJECT/manifest.json'))['questions']))")
    echo "[$(date +%H:%M:%S)] === $SUBJECT: $TOTAL questions ==="
    
    while true; do
        DONE=$(python3 -c "
import json
done=set()
try:
    for line in open('lgs_çalışma_soruları/$SUBJECT/analysis.jsonl'):
        done.add(json.loads(line)['file'])
except: pass
print(len(done))
" 2>/dev/null || echo 0)
        
        echo "[$(date +%H:%M:%S)] $SUBJECT: $DONE/$TOTAL done"
        
        if [ "$DONE" -ge "$TOTAL" ]; then
            echo "[$(date +%H:%M:%S)] $SUBJECT COMPLETE"
            break
        fi
        
        for SHARD in $(seq 1 $SHARDS); do
            python3 scripts/source-ingestion/analyze_study_workbook.py \
                --subject "$SUBJECT" \
                --shards "$SHARDS" --shard "$SHARD" \
                --provider ollama \
                --ollama-model minicpm-v:latest \
                --ollama-resize 256 \
                >> "logs/cal05_${SUBJECT}_shard${SHARD}.log" 2>&1 &
        done
        
        wait
        sleep 5
    done
done

echo "[$(date +%H:%M:%S)] ALL CAL05 ANALYSIS COMPLETE"
