#!/usr/bin/env python3
"""Fix_27 klasorundeki duzeltilmis PNG'leri asil yerlerine koyar:
- public/exams/<ay>/<ders>/QNN.png        (canli site)
- lgs_18_26/exams_by_month/<ay>/<ders>/QNN.png  (ay manifest kopyasi)
- lgs_18_26/<slug>/<ID>.png                (kaynak kopya)
- lgs_18_26/<slug>/manifest_<yil>.json     (visual.clipRectPt guncelleme)
Her eski dosya .bak olarak yedeklenir.
"""
import json
import os
import shutil
import hashlib

BASE = "/home/selam/roller/web/lgs-ai-coach"
STAGING = os.path.join(BASE, "_fix_27")
REPORT = os.path.join(STAGING, "fix_report.json")

SUBJ_SLUG = {
    "turkce": "turkce", "matematik": "matematik", "fen-bilimleri": "fen-bilimleri",
    "ingilizce": "ingilizce", "din-kulturu": "din-kulturu", "inkilap-tarihi": "inkilap-tarihi",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        bak = dst + ".bak"
        if not os.path.exists(bak):
            shutil.copy2(dst, bak)
    shutil.copy2(src, dst)


def main():
    report = json.load(open(REPORT, encoding="utf-8"))
    installed = []
    for r in report:
        if r.get("error") or "out" not in r:
            continue
        src = r["out"]
        rel = r["rel"]  # public/exams/00_seviye_tespit/fen-bilimleri/Q04.png
        parts = rel.split("/")  # ['public','exams','00_seviye_tespit','fen-bilimleri','Q04.png']
        month_dir, subject, fname = parts[2], parts[3], parts[4]

        # 1) canli site (zaten orasi kaynak, ama .bak alip ustune yaz)
        dst_live = os.path.join(BASE, rel)
        backup_copy(src, dst_live)

        # 2) ay kopyasi
        dst_month = os.path.join(BASE, "lgs_18_26", "exams_by_month", month_dir, subject, fname)
        backup_copy(src, dst_month)

        # 3) kaynak kopya: lgs_18_26/<slug>/<ID>.png
        slug = SUBJ_SLUG.get(subject)
        if not slug:
            continue
        qid = r["id"]
        dst_src = os.path.join(BASE, "lgs_18_26", slug, qid + ".png")
        backup_copy(src, dst_src)

        # 4) kaynak manifest guncelleme
        import glob
        mpath = None
        for mp in glob.glob(os.path.join(BASE, "lgs_18_26", slug, "manifest_*.json")):
            if mp.endswith(".updated.json"):
                continue
            man = json.load(open(mp, encoding="utf-8"))
            for q in man.get("questions", []):
                if q.get("id") == qid:
                    mpath = mp
                    break
            if mpath:
                break
        if mpath:
            man = json.load(open(mpath, encoding="utf-8"))
            for q in man.get("questions", []):
                if q.get("id") == qid:
                    q.setdefault("visual", {})["clipRectPt"] = r.get("new_clip")
                    q["visual"]["assetSha256"] = sha256(dst_src)
                    q["visual"]["renderDpi"] = 300
                    break
            with open(mpath, "w", encoding="utf-8") as f:
                json.dump(man, f, ensure_ascii=False, indent=1)
        installed.append(rel)

    print("Kurulan:", len(installed))
    for rel in installed:
        print("  ", rel)


if __name__ == "__main__":
    main()