#!/bin/bash
# LGS 18-26 tüm dersler + tüm yıllar — 1 işçi, bitene kadar (OOM önleme)
# Not: id'ler artık yıl-doğru (MEB-LGS-<yıl>-<DERS>-Qnn), bu yüzden yıl filtresi güvenli.
cd /home/selam/roller/web/lgs-ai-coach
PY=/home/selam/roller/web/lgs-ai-coach/.venv/bin/python3

SUBJECTS=("turkce" "matematik" "fen-bilimleri" "ingilizce" "din-kulturu" "inkilap-tarihi")
YEARS=("2018" "2019" "2020" "2021" "2022" "2023" "2024" "2025" "2026")
SHARDS=1

mkdir -p logs

while true; do
    ALL_DONE=true

    for SUBJECT in "${SUBJECTS[@]}"; do
        for YEAR in "${YEARS[@]}"; do
            SRC="Lgs_18-26/nuli-${YEAR}-all-subjects-20pt/${SUBJECT}"

            if [ ! -d "$SRC" ]; then
                continue
            fi

            MANIFEST="$SRC/manifest.json"
            if [ ! -f "$MANIFEST" ]; then
                continue
            fi

            TOTAL=$($PY -c "import json; print(len(json.load(open('$MANIFEST'))['questions']))" 2>/dev/null || echo 0)
            if [ "$TOTAL" -eq 0 ]; then
                echo "[$(date +%H:%M:%S)] $SUBJECT $YEAR: MANIFEST YOK — tekrar denenecek"
                ALL_DONE=false
                continue
            fi

            DONE=$($PY -c "
import json
try:
    done = set()
    for line in open('Lgs_18-26/analysis_${SUBJECT}.jsonl'):
        rec = json.loads(line)
        # ID format: MEB-LGS-2018-TURKCE-Q01 -> yıl 2018
        fid = rec.get('file', '')
        if fid.startswith('MEB-LGS-') and len(fid) > 9:
            rec_year = fid[8:12]
            if rec_year == '${YEAR}':
                done.add(fid)
    print(len(done))
except:
    print(0)
" 2>/dev/null || echo 0)

            if [ "$DONE" -ge "$TOTAL" ]; then
                echo "[$(date +%H:%M:%S)] $SUBJECT $YEAR: TAMAM ($DONE/$TOTAL)"
                continue
            fi

            ALL_DONE=false
            echo "[$(date +%H:%M:%S)] $SUBJECT $YEAR: $DONE/$TOTAL — başlatılıyor"

            for SHARD in $(seq 1 $SHARDS); do
                $PY scripts/source-ingestion/analyze_study_workbook.py \
                    --subject "$SUBJECT" \
                    --source-dir "$SRC" \
                    --output "Lgs_18-26/analysis_${SUBJECT}.jsonl" \
                    --provider ollama \
                    --ollama-model gemma3:4b \
                    --ollama-resize 256 \
                    --shards $SHARDS \
                    --shard $SHARD \
                    >> "logs/analysis_${SUBJECT}_${YEAR}.log" 2>&1
            done
        done
    done

    if $ALL_DONE; then
        echo "[$(date +%H:%M:%S)] 🎉 TÜM ANALİZLER TAMAMLANDI"
        exit 0
    fi

    echo "[$(date +%H:%M:%S)] Döngü tamamlandı, 30s sonra tekrar..."
    sleep 30
done