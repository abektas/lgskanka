#!/usr/bin/env python3
"""
Aylık deneme soruları için ünite/konu sınıflandırma (Evren `laya`).

1080 sorunun (12 sınav × 90 soru) konu eşlemesini üretir.
Çıktı: lgs_18_26/exams_by_month/topic_map.json  (id → {unit, unitName, topic, confidence})
"""
from __future__ import annotations
import json, os, re, sys, time, glob
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.request

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
EVREN = "https://evren-llmapi.ssyz.org.tr/v1/systemone"
KEY = os.environ.get("EVREN_API_KEY", "")
OUT = BASE / "exams_by_month" / "topic_map.json"

# ---------------------------------------------------------------- taksonomi
# MEB 8. sınıf müfredatı birim/konu listeleri (günlük havuzdaki unitName ile hizalı).
TAXONOMY: dict[str, list[tuple[int, str, list[str]]]] = {
    "turkce": [
        (1, "SÖZCÜKTE ANLAM", ["SÖZCÜKTE ANLAM", "DEYIM VE ATASÖZÜ", "SÖZ SANATLARI"]),
        (2, "CÜMLEDE ANLAM", ["CÜMLEDE ANLAM", "SÖZEL MANTIK / MUHAKEME"]),
        (3, "PARÇADA ANLAM", ["PARÇADA ANLAM"]),
        (4, "METİN TÜRLERİ", ["METİN TÜRLERİ"]),
        (5, "FIILIMSILER", ["FIILIMSILER"]),
        (6, "CÜMLENİN ÖGELERİ", ["CÜMLENİN ÖGELERİ"]),
        (7, "YAZIM KURALLARI", ["YAZIM KURALLARI"]),
        (8, "NOKTALAMA İŞARETLERİ", ["NOKTALAMA İŞARETLERİ", "GÖRSEL OKUMA (Tablo / Grafik / Çizelge)"]),
    ],
    "matematik": [
        (1, "SAYILAR VE İŞLEMLER", ["SAYILAR VE İŞLEMLER"]),
        (2, "CEBİRSEL İFADELER", ["CEBİRSEL İFADELER"]),
        (3, "ÜSLÜ İFADELER", ["ÜSLÜ İFADELER"]),
        (4, "KAREKÖKLÜ İFADELER", ["KAREKÖKLÜ İFADELER"]),
        (5, "VERİ ANALİZİ", ["VERİ ANALİZİ", "OLASILIK"]),
        (6, "GEOMETRİ", ["GEOMETRİ", "ÖLÇÜ", "DENKLEMLER", "EŞİTSİZLİKLER"]),
    ],
    "fen-bilimleri": [
        (1, "MADDE VE DOĞASI", ["MADDE VE DOĞASI"]),
        (2, "CANLILARIN TEMEL BİLEŞENLERİ", ["CANLILARIN TEMEL BİLEŞENLERİ", "DNA VE KALITIM"]),
        (3, "MADDE VE ENERJİ", ["MADDE VE ENERJİ", "BASINÇ", "BASİT MAKİNELER", "ISIL VE SICAKLIK"]),
        (4, "KUVVET VE ENERJİ", ["KUVVET VE ENERJİ"]),
        (5, "DÜNYA VE EVREN", ["DÜNYA VE EVREN", "MEVSİMLER VE İKLİM"]),
        (6, "ELEKTRİK VE MANYETİZMA", ["ELEKTRİK VE MANYETİZMA"]),
        (7, "MADDE VE ENDÜSTRİ", ["MADDE VE ENDÜSTRİ"]),
    ],
    "ingilizce": [
        (1, "Friendship", ["Friendship"]),
        (2, "Teen Life", ["Teen Life"]),
        (3, "In the Kitchen", ["In the Kitchen"]),
        (4, "On the Phone", ["On the Phone"]),
        (5, "The Internet", ["The Internet"]),
        (6, "Adventures", ["Adventures"]),
        (7, "Tourism", ["Tourism"]),
        (8, "Chores", ["Chores"]),
        (9, "Science", ["Science"]),
        (10, "Natural Forces", ["Natural Forces"]),
    ],
    "din-kulturu": [
        (1, "Kader İnancı", ["Kader İnancı"]),
        (2, "Zekât ve Sadaka", ["Zekât ve Sadaka"]),
        (3, "Din ve Hayat", ["Din ve Hayat"]),
        (4, "Hz. Muhammed'in Örnekliği", ["Hz. Muhammed'in Örnekliğı"]),
        (5, "Kur'an-ı Kerim ve Özellikleri", ["Kur'an-ı Kerim ve Özellikleri"]),
    ],
    "inkilap-tarihi": [
        (1, "Bir Kahraman Doğuyor", ["Bir Kahraman Doğuyor"]),
        (2, "Millî Uyanış: Bağımsızlık Yolunda Atılan Adımlar", ["Millî Uyanış: Bağımsızlık Yolunda Atılan Adımlar"]),
        (3, "Millî Bir Destan: Ya İstiklal Ya Ölüm!", ["Millî Bir Destan: Ya İstiklal Ya Ölüm!"]),
        (4, "Atatürkçülük ve Çağdaşlaşan Türkiye", ["Atatürkçülük ve Çağdaşlaşan Türkiye"]),
        (5, "Demokratikleşme Çabaları", ["Demokratikleşme Çabaları"]),
        (6, "Atatürk Dönemi Türk Dış Politikası", ["Atatürk Dönemi Türk Dış Politikası"]),
    ],
}

# Uzun metinleri kırp (laya input sınırı + hız)
MAX_CHARS = 2200


def load_questions() -> list[dict]:
    """exam manifest'lerindeki 1080 soruyu id + metin ile döndür."""
    meta: dict[tuple[str, str], dict] = {}
    for sub in TAXONOMY:
        for af in sorted(glob.glob(str(BASE / sub / "analysis_*.jsonl"))):
            for line in open(af, encoding="utf-8"):
                if not line.strip():
                    continue
                a = json.loads(line)
                if a.get("published") is False:
                    continue
                meta[(sub, a.get("id"))] = a

    out: list[dict] = []
    for mf in sorted(glob.glob(str(BASE / "exams_by_month" / "*" / "manifest_*.json"))):
        m = json.load(open(mf, encoding="utf-8"))
        for q in m["questions"]:
            rec = meta.get((q["subject"], q["id"]))
            text = (rec or {}).get("questionText") or q.get("questionText") or ""
            out.append({
                "id": q["id"],
                "subject": q["subject"],
                "questionNumber": q["questionNumber"],
                "file": q["file"],
                "examYear": q.get("examYear"),
                "text": text.strip()[:MAX_CHARS],
                "hasText": len(text.strip()) >= 40,
            })
    return out


def call_laya(batch: list[dict]) -> dict:
    """Tek HTTP çağrısında bir batch (aynı ders) için konu tahmini."""
    sub = batch[0]["subject"]
    units = TAXONOMY[sub]
    labels = [u[1] for u in units]
    label_to_unit = {u[1]: (u[0], u[1]) for u in units}

    state = {str(i): q["text"] for i, q in enumerate(batch)}
    questions = {
        str(i): {
            "type": "choice",
            "question": str(i),
            "instructions": (
                f"Soru {i} bir MEB LGS 8. sınıf {sub} sorusudur. "
                "Sorunun müfredat konusunu (unit) seçeneklerden tam olarak birini seç."
            ),
            "criteria": labels,
        }
        for i in range(len(batch))
    }

    payload = json.dumps(
        {"model": "laya", "state": json.dumps(state, ensure_ascii=False), "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        EVREN,
        data=payload,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    answers = body.get("answers", {})
    result: dict[str, dict] = {}
    for i, q in enumerate(batch):
        a = answers.get(str(i), {})
        choice = a.get("choice")
        unit, unit_name = label_to_unit.get(choice, (None, None))
        result[q["id"]] = {
            "unit": unit,
            "unitName": unit_name,
            "topic": choice,
            "confidence": round(float(a.get("confidence") or 0), 4),
            "probs": {k: round(float(v), 4) for k, v in (a.get("probabilities") or {}).items()},
        }
    return result


def main() -> None:
    questions = load_questions()
    print(f"Yüklendi: {len(questions)} soru")

    by_subject: dict[str, list[dict]] = {}
    for q in questions:
        by_subject.setdefault(q["subject"], []).append(q)

    # Her ders için batch'ler (laya state boyutu sınırlı)
    BATCH = 8
    jobs: list[list[dict]] = []
    for sub, qs in by_subject.items():
        for i in range(0, len(qs), BATCH):
            jobs.append(qs[i:i + BATCH])
    print(f"Toplam batch: {len(jobs)}")

    results: dict[str, dict] = {}
    done = 0
    errors = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(call_laya, job): job for job in jobs}
        for fut in as_completed(futures):
            job = futures[fut]
            try:
                results.update(fut.result())
            except Exception as e:
                errors += 1
                print(f"HATA ({job[0]['subject']}): {e}")
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{len(jobs)} batch ({time.time()-t0:.0f}s)")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Yazıldı: {OUT} — {len(results)} soru, {errors} hata, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
