#!/usr/bin/env python3
"""lgs_18_26 — sınav ayırıcı: her ders içi easy→hard sıralama, 13 ay (00 + 11)."""

from __future__ import annotations
import json
import shutil
from collections import defaultdict
from pathlib import Path

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
BASE = REPO / "lgs_18_26"
OUT = BASE / "exams_by_month"
SUBJECTS = {
    "turkce": 20, "matematik": 20, "fen-bilimleri": 20,
    "ingilizce": 10, "din-kulturu": 10, "inkilap-tarihi": 10,
}
MONTHS = 11  # 00_seviye_tespit + 11 ay = 12 sınav (12 LGS)
TOTAL_PER_MONTH = 90

# Sıralama ağırlıkları (daha yüksek = daha zor)
TYPE_WEIGHT = {
    "Doğrudan Bilgi": 1,
    "Rutin İşlem": 2,
    "Problem Çözme": 3,
    "Muhakeme": 4,
    "Modelleme": 5,
}
VIS_DEP_WEIGHT = {"none": 0, "figure_unverified": 1, "data_required": 2}


def load_analysis(sub: str, year: int) -> dict:
    """analysis_<year>.jsonl -> {file: record}"""
    f = BASE / sub / f"analysis_{year}.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        out[r["file"]] = r
    return out


def difficulty_score(rec: dict) -> float:
    """Daha yüksek = daha zor."""
    pd = rec.get("pedagogicalDifficulty") or 1
    qt = TYPE_WEIGHT.get(rec.get("questionType") or "", 1)
    vd = VIS_DEP_WEIGHT.get(rec.get("visualDependency") or "none", 0)
    steps = rec.get("operationStepCount") or 1
    concepts = rec.get("conceptCount") or 1
    return pd * 2.0 + qt * 1.5 + vd * 1.0 + steps * 0.3 + concepts * 0.2


def collect_all_sorted() -> dict[str, list[dict]]:
    """Her ders için (yıl, dosya, skor, kayıt) listesi — easy→hard."""
    by_sub = defaultdict(list)
    for sub in SUBJECTS:
        for year in range(2015, 2027):
            amap = load_analysis(sub, year)
            for fn, rec in amap.items():
                if rec.get("published") is False:
                    continue
                score = difficulty_score(rec)
                by_sub[sub].append((year, fn, score, rec))
        # Easy → hard
        by_sub[sub].sort(key=lambda x: x[2])
        print(f"{sub}: {len(by_sub[sub])} soru, skor aralığı "
              f"{by_sub[sub][0][2]:.1f}–{by_sub[sub][-1][2]:.1f}")
    return by_sub


def distribute_months(sorted_by_sub: dict[str, list]) -> list[dict[str, list]]:
    """
    Round-robin dağıtım: her ders kendi içinde eşit aralıklarla 13 gruba bölünür.
    Bu sayede her ay her dersten eşit sayıda soru gelir VE zorluk dağılımı dengeli olur.
    """
    months = [defaultdict(list) for _ in range(MONTHS + 1)]  # 0..12 (13 klasör)
    for sub, need in SUBJECTS.items():
        items = sorted_by_sub[sub]
        if len(items) < need * (MONTHS + 1):
            raise ValueError(f"{sub}: yeterli soru yok ({len(items)} < {need * (MONTHS + 1)})")
        # 13 gruba eşit dağıt (her gruptan need adet)
        step = len(items) // (MONTHS + 1)
        for m in range(MONTHS + 1):
            start = m * step
            end = start + need
            months[m][sub] = items[start:end]
    return months


def dry_run():
    sorted_by_sub = collect_all_sorted()
    months = distribute_months(sorted_by_sub)

    print("\n--- DAĞILIM ÖZETİ ---")
    for m in range(MONTHS + 1):
        name = "00_seviye_tespit" if m == 0 else f"{m:02d}_ay"
        total = sum(len(v) for v in months[m].values())
        subs = {k: len(v) for k, v in months[m].items()}
        avg_score = sum(r[2] for v in months[m].values() for r in v) / total if total else 0
        print(f"{name:16s} | toplam {total:3d} | {subs} | ortalama zorluk: {avg_score:.2f}")

    # İlk/son ay karşılaştırması
    first = months[0]
    last = months[MONTHS]
    for sub in SUBJECTS:
        f_avg = sum(r[2] for r in first[sub]) / len(first[sub])
        l_avg = sum(r[2] for r in last[sub]) / len(last[sub])
        print(f"  {sub:16s} ay1={f_avg:.2f} ay12={l_avg:.2f}  Δ={l_avg-f_avg:.2f}")

    return months


def build_folders(months: list[dict[str, list]]):
    """exams_by_month/ klasörüne PNG + manifest yaz."""
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for m in range(MONTHS + 1):
        name = "00_seviye_tespit" if m == 0 else f"{m:02d}_ay"
        mdir = OUT / name
        for sub in SUBJECTS:
            (mdir / sub).mkdir(parents=True)

        # PNG kopyala + manifest yaz - önce tüm dersleri topla
        all_manifest_qs = []
        for sub in SUBJECTS:
            items = months[m].get(sub, [])
            mdir_sub = mdir / sub
            for idx, (year, fn, score, rec) in enumerate(items, 1):
                src = BASE / sub / fn
                dst_name = f"Q{idx:02d}.png"
                dst = mdir_sub / dst_name
                if src.exists():
                    shutil.copy2(src, dst)
                else:
                    print(f"UYARI: {src} yok")
                    continue

                all_manifest_qs.append({
                    "id": rec["id"],
                    "questionNumber": idx,
                    "file": dst_name,
                    "answer": rec.get("answerKeyCandidate"),
                    "subject": sub,
                    "examYear": year,
                    "originalYear": year,
                    "difficultyScore": round(score, 2),
                    "questionType": rec.get("questionType"),
                    "visualDependency": rec.get("visualDependency"),
                    "underlineDependent": rec.get("underlineDependent"),
                    "topic": rec.get("topic"),
                    "unit": rec.get("unit"),
                    "unitName": rec.get("unitName"),
                })

        # Tek manifest yaz (tüm dersler)
        manifest = {
            "month": m,
            "monthName": name,
            "totalQuestions": len(all_manifest_qs),
            "durationMinutes": 155,
            "subjectDurations": {
                "matematik": 40,
                "fen-bilimleri": 40,
                "turkce": 30,
                "inkilap-tarihi": 15,
                "din-kulturu": 15,
                "ingilizce": 15,
            },
            "questions": all_manifest_qs,
        }
        (mdir / f"manifest_{name}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    print(f"\nYAZILDI: {OUT}")


def main():
    months = dry_run()
    # Onay bekle
    import sys
    if "--apply" not in sys.argv:
        print("\n--apply ile yazılır (dry-run bitti).")
        return
    build_folders(months)


if __name__ == "__main__":
    main()