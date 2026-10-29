#!/usr/bin/env python3
"""
topic_map.json → exam manifest'lerine merge eder.
Düşük confidence (< 0.30) olanları NEEDS_REVIEW kuyruğuna atar.
Çıktı: güncellenmiş manifest_*.json + review_queue.jsonl
"""
from __future__ import annotations
import json, glob, os
from pathlib import Path
from collections import defaultdict

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
TOPIC_MAP = BASE / "exams_by_month" / "topic_map.json"
REVIEW_QUEUE = BASE / "exams_by_month" / "review_queue.jsonl"
CONFIDENCE_THRESHOLD = 0.30

def main():
    with open(TOPIC_MAP, encoding="utf-8") as f:
        topic_map = json.load(f)

    # Manifest dosyalarını bul
    manifest_files = sorted(glob.glob(str(BASE / "exams_by_month" / "*" / "manifest_*.json")))
    print(f"Bulunan manifest: {len(manifest_files)}")

    review_items = []
    updated = 0

    for mf in manifest_files:
        with open(mf, encoding="utf-8") as f:
            manifest = json.load(f)

        changed = False
        for q in manifest["questions"]:
            tm = topic_map.get(q["id"])
            if tm:
                q["unit"] = tm["unit"]
                q["unitName"] = tm["unitName"]
                q["topic"] = tm["topic"]
                q["topicConfidence"] = tm["confidence"]
                q["topicProbs"] = tm["probs"]

                if tm["confidence"] < CONFIDENCE_THRESHOLD:
                    review_items.append({
                        "id": q["id"],
                        "subject": q["subject"],
                        "questionNumber": q["questionNumber"],
                        "examYear": q.get("examYear"),
                        "file": q["file"],
                        "predictedUnit": tm["unit"],
                        "predictedUnitName": tm["unitName"],
                        "predictedTopic": tm["topic"],
                        "confidence": tm["confidence"],
                        "probs": tm["probs"],
                        "reason": f"confidence {tm['confidence']:.3f} < {CONFIDENCE_THRESHOLD}",
                        "status": "NEEDS_REVIEW"
                    })
                changed = True

        if changed:
            with open(mf, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=1)
            updated += 1

    # Review queue yaz
    with open(REVIEW_QUEUE, "w", encoding="utf-8") as f:
        for item in review_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Güncellenen manifest: {updated}/{len(manifest_files)}")
    print(f"Review kuyruğu: {len(review_items)} soru → {REVIEW_QUEUE}")

    # Özet
    by_subject = defaultdict(int)
    for item in review_items:
        by_subject[item["subject"]] += 1
    print("Ders bazında review:", dict(by_subject))

if __name__ == "__main__":
    main()