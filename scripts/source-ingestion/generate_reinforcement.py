#!/usr/bin/env python3
"""
Aylık deneme pekiştirme üretimi (reinforcement generation).

Girdi:
- Öğrenci yanıtları: Supabase `student_answers` (user_id, question_id, answer, correct, exam_month)
- Manifest'ler: lgs_18_26/exams_by_month/*/manifest_*.json (unit/unitName/topic alanları merge edilmiş)
- Haftalık test geçmişi: student_answers where exam_type='haftalik'

Çıktı (her öğrenci için):
- reinforcement_plan.json: {
    user_id,
    exam_month,
    monthly_wrong: [{question_id, subject, unit, unitName, topic, difficulty}],
    weekly_weak_units: {unitName: {wrong_count, total_seen, weakness_score}},
    reinforcement_topics: [{unit, unitName, topic, priority, reason}],
    practice_questions: [{question_id, subject, unit, unitName, topic, source_exam, source_month}]
  }

Kural:
- Aylık deneme 4. hafta (cumartesi+pazar aynı test)
- Pekiştirme: aylık deneme yanlışları + son 3 haftalık testten zayıf üniteler
- Öncelik: (aylık yanlış sayısı * 2) + (haftalık zayıflık skoru)
- Çıktı soru havuzu: published=True analysis dosyalarından, aynı unit/topic'teki sorular
"""
from __future__ import annotations
import json, glob, os
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import Optional

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
MANIFEST_DIR = BASE / "exams_by_month"
ANALYSIS_DIR = BASE  # analysis_*.jsonl her ders klasöründe

@dataclass
class QuestionMeta:
    id: str
    subject: str
    unit: Optional[int]
    unitName: Optional[str]
    topic: Optional[str]
    difficultyScore: float
    examYear: int
    examMonth: str
    questionNumber: int
    file: str
    answer: str

def load_manifests() -> dict[str, QuestionMeta]:
    """Tüm manifest'lerden soru meta verilerini yükle."""
    metas: dict[str, QuestionMeta] = {}
    for mf in glob.glob(str(MANIFEST_DIR / "*" / "manifest_*.json")):
        with open(mf, encoding="utf-8") as f:
            m = json.load(f)
        month = m["month"]
        month_name = m["monthName"]
        for q in m["questions"]:
            metas[q["id"]] = QuestionMeta(
                id=q["id"],
                subject=q["subject"],
                unit=q.get("unit"),
                unitName=q.get("unitName"),
                topic=q.get("topic"),
                difficultyScore=q.get("difficultyScore", 3.0),
                examYear=q.get("examYear", 0),
                examMonth=month_name,
                questionNumber=q["questionNumber"],
                file=q["file"],
                answer=q["answer"],
            )
    return metas

def load_practice_pool(question_metas: dict[str, QuestionMeta]) -> dict[str, list[QuestionMeta]]:
    """Published manifest sorularını unitName'e göre grupla (pekiştirme havuzu)."""
    pool: dict[str, list[QuestionMeta]] = defaultdict(list)
    for qm in question_metas.values():
        if qm.unitName:
            pool[qm.unitName].append(qm)
    return pool

def generate_reinforcement_plan(
    user_id: str,
    student_answers: list[dict],
    question_metas: dict[str, QuestionMeta],
    practice_pool: dict[str, list[QuestionMeta]],
    target_month: str,
    target_sunday: Optional[str] = None,  # ISO date "YYYY-MM-DD" of the Sunday
) -> dict:
    """Tek öğrenci için pekiştirme planı üret."""

    # 1. Hedef aylık deneme yanlışları
    monthly_wrong = []
    for ans in student_answers:
        if ans.get("exam_month") == target_month and ans.get("exam_type") == "aylik":
            if not ans.get("correct", False):
                qm = question_metas.get(ans["question_id"])
                if qm and qm.unitName:
                    monthly_wrong.append({
                        "question_id": ans["question_id"],
                        "subject": qm.subject,
                        "unit": qm.unit,
                        "unitName": qm.unitName,
                        "topic": qm.topic,
                        "difficulty": qm.difficultyScore,
                    })

    # 2. Son 3 haftalık testten zayıf üniteler (exam_type='haftalik', önceki 3 ay)
    # Basitlik için: tüm haftalık yanıtları al, unitName bazında wrong rate hesapla
    weekly_by_unit = defaultdict(lambda: {"wrong": 0, "total": 0})
    for ans in student_answers:
        if ans.get("exam_type") == "haftalik":
            qm = question_metas.get(ans["question_id"])
            if qm and qm.unitName:
                weekly_by_unit[qm.unitName]["total"] += 1
                if not ans.get("correct", False):
                    weekly_by_unit[qm.unitName]["wrong"] += 1

    weekly_weak_units = {}
    for unit_name, stats in weekly_by_unit.items():
        if stats["total"] >= 3:  # en az 3 soru görmüş
            weakness = stats["wrong"] / stats["total"]
            if weakness > 0.4:  # %40'tan fazla yanlış
                weekly_weak_units[unit_name] = {
                    "wrong_count": stats["wrong"],
                    "total_seen": stats["total"],
                    "weakness_score": round(weakness, 3),
                }

    # 3. Pekiştirme konuları öncelikle
    # Birim skor = (aylık yanlış sayısı * 2) + (haftalık weakness * 10)
    unit_priority = defaultdict(float)
    for w in monthly_wrong:
        unit_priority[w["unitName"]] += 2.0
    for unit_name, stats in weekly_weak_units.items():
        unit_priority[unit_name] += stats["weakness_score"] * 10

    # 4. Her öncelikli unit için havuzdan soru seç (en fazla 5 soru/unit)
    practice_questions = []
    for unit_name, priority in sorted(unit_priority.items(), key=lambda x: -x[1]):
        if priority < 1.0:
            continue
        # Havuzdan aynı unitName'e sahip soruları bul
        candidates = practice_pool.get(unit_name, [])
        # Zorluğa göre sırala (orta zorluk önce)
        candidates.sort(key=lambda x: abs(x.difficultyScore - 3.5))
        for aq in candidates[:5]:
            practice_questions.append({
                "question_id": aq.id,
                "subject": aq.subject,
                "unit": aq.unit,
                "unitName": aq.unitName,
                "topic": aq.topic,
                "source_exam": aq.examYear,
                "source_month": aq.examMonth,
                "difficulty": aq.difficultyScore,
            })

    reinforcement_topics = [
        {
            "unit": question_metas.get(next((w["question_id"] for w in monthly_wrong if w["unitName"] == un), ""), QuestionMeta("", "", None, un, None, 0, 0, "", 0, "", "")).unit,
            "unitName": un,
            "topic": next((w["topic"] for w in monthly_wrong if w["unitName"] == un), None),
            "priority": round(priority, 2),
            "reason": "monthly_wrong" if any(w["unitName"] == un for w in monthly_wrong) else "weekly_weak"
        }
        for un, priority in sorted(unit_priority.items(), key=lambda x: -x[1])
        if priority >= 1.0
    ]

    return {
        "user_id": user_id,
        "exam_month": target_month,
        "monthly_wrong": monthly_wrong,
        "weekly_weak_units": weekly_weak_units,
        "reinforcement_topics": reinforcement_topics,
        "practice_questions": practice_questions,
    }

def main():
    question_metas = load_manifests()
    print(f"Manifest soru sayısı: {len(question_metas)}")

    practice_pool = load_practice_pool(question_metas)
    total_pool = sum(len(v) for v in practice_pool.values())
    print(f"Pekiştirme havuzu: {total_pool} soru, {len(practice_pool)} unit")

    # Demo: test verisi (gerçekte Supabase'den gelecek)
    demo_student_answers = [
        # 1. ay aylık deneme yanlışları
        {"question_id": "MEB-LGS-2016-TURKCE-Q19", "correct": False, "exam_month": "01_ay", "exam_type": "aylik"},
        {"question_id": "MEB-LGS-2016-MATEMATIK-Q05", "correct": False, "exam_month": "01_ay", "exam_type": "aylik"},
        # Haftalık testler (son 3 ay simülasyonu)
        {"question_id": "MEB-LGS-2016-MATEMATIK-Q01", "correct": False, "exam_month": "01_ay", "exam_type": "haftalik"},
        {"question_id": "MEB-LGS-2016-MATEMATIK-Q02", "correct": False, "exam_month": "01_ay", "exam_type": "haftalik"},
        {"question_id": "MEB-LGS-2016-MATEMATIK-Q03", "correct": True, "exam_month": "01_ay", "exam_type": "haftalik"},
        {"question_id": "MEB-LGS-2016-MATEMATIK-Q04", "correct": False, "exam_month": "01_ay", "exam_type": "haftalik"},
        # Fen bilimleri zayıf
        {"question_id": "MEB-LGS-2016-FENBILIMLERI-Q10", "correct": False, "exam_month": "01_ay", "exam_type": "haftalik"},
        {"question_id": "MEB-LGS-2016-FENBILIMLERI-Q11", "correct": False, "exam_month": "01_ay", "exam_type": "haftalik"},
        {"question_id": "MEB-LGS-2016-FENBILIMLERI-Q12", "correct": True, "exam_month": "01_ay", "exam_type": "haftalik"},
    ]

    # Pazar tarihi örneği (4. hafta pazarı)
    target_sunday = "2026-11-22"  # 1. ay aylık deneme pazarı

    plan = generate_reinforcement_plan(
        user_id="demo-user-001",
        student_answers=demo_student_answers,
        question_metas=question_metas,
        practice_pool=practice_pool,
        target_month="01_ay",
        target_sunday=target_sunday,
    )

    # Pazar odaklı özet ekle
    if target_sunday:
        plan["sunday_focus"] = {
            "date": target_sunday,
            "message": f"{target_sunday} pazar günü bu konulara odaklan: " + ", ".join(
                f"{t['unitName']} ({t['topic']})" for t in plan["reinforcement_topics"][:3]
            ),
            "recommended_duration_minutes": 90,
            "structure": [
                {"step": 1, "activity": "Aylık deneme yanlışları tekrarı", "minutes": 30},
                {"step": 2, "activity": "Haftalık zayıf üniteler pekiştirme", "minutes": 40},
                {"step": 3, "activity": "Yeni soru çözümü (havuzdan)", "minutes": 20},
            ],
        }

    print(json.dumps(plan, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()