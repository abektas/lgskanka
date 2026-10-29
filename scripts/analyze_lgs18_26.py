#!/usr/bin/env python3
"""LGS 2018-2026 AI analysis — manifest içindeki subjects yapısı için.

Her yılın manifest.json'ını okur, her soru için AI analizi yapar.
Kazanım kodu + zorluk derecesi + kısa analiz üretir.
Resumable: analysis.jsonl dosyasına ekler, tekrar çalıştırınca atlanır.
"""
import argparse, base64, json, os, sys, time, urllib.request
from pathlib import Path
from io import BytesIO

ROOT = Path("/home/selam/roller/web/lgs-ai-coach")
LGS_DIR = ROOT / "Lgs_18-26"

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "minicpm-v:latest"

# MEB kazanım kodları (8. sınıf, 2018+ müfredat)
MEB_KAZANIM = {
    "turkce": [
        "KOD-8.TRK.01", "KOD-8.TRK.02", "KOD-8.TRK.03", "KOD-8.TRK.04",
        "KOD-8.TRK.05", "KOD-8.TRK.06", "KOD-8.TRK.07", "KOD-8.TRK.08",
        "KOD-8.TRK.09", "KOD-8.TRK.10", "KOD-8.TRK.11", "KOD-8.TRK.12",
    ],
    "matematik": [
        "KOD-8.MAT.01", "KOD-8.MAT.02", "KOD-8.MAT.03", "KOD-8.MAT.04",
        "KOD-8.MAT.05", "KOD-8.MAT.06", "KOD-8.MAT.07", "KOD-8.MAT.08",
        "KOD-8.MAT.09", "KOD-8.MAT.10", "KOD-8.MAT.11", "KOD-8.MAT.12",
    ],
    "fen": [
        "KOD-8.FEN.01", "KOD-8.FEN.02", "KOD-8.FEN.03", "KOD-8.FEN.04",
        "KOD-8.FEN.05", "KOD-8.FEN.06", "KOD-8.FEN.07", "KOD-8.FEN.08",
    ],
    "inkilap": [
        "KOD-8.TAR.01", "KOD-8.TAR.02", "KOD-8.TAR.03", "KOD-8.TAR.04",
        "KOD-8.TAR.05", "KOD-8.TAR.06", "KOD-8.TAR.07", "KOD-8.TAR.08",
    ],
    "din": [
        "KOD-8.DIN.01", "KOD-8.DIN.02", "KOD-8.DIN.03", "KOD-8.DIN.04",
        "KOD-8.DIN.05", "KOD-8.DIN.06", "KOD-8.DIN.07", "KOD-8.DIN.08",
    ],
    "ingilizce": [
        "KOD-8.ING.01", "KOD-8.ING.02", "KOD-8.ING.03", "KOD-8.ING.04",
        "KOD-8.ING.05", "KOD-8.ING.06", "KOD-8.ING.07", "KOD-8.ING.08",
    ],
}

SUBJECT_MAP = {
    "Türkçe": "turkce",
    "Matematik": "matematik",
    "Fen Bilimleri": "fen",
    "Fen": "fen",
    "T.C. İnkılap Tarihi ve Atatürkçülük": "inkilap",
    "İnkılap Tarihi": "inkilap",
    "Din Kültürü ve Ahlak Bilgisi": "din",
    "Din Kültürü": "din",
    "İngilizce": "ingilizce",
    "Yabancı Dil": "ingilizce",
}

PROMPT_TEMPLATE = """Bu LGS sorusu için kısa JSON:
{"kazanimKodi":"<listeden bir kod>","zorluk":1-5}
Kodlar: {kazanim_list}
Sadece JSON."""


def analyze_question(png_path: str, subject_key: str, model: str, resize: int = 256) -> dict:
    """AI ile tek soru analizi — regex ile sağlam parse."""
    try:
        from PIL import Image
        img = Image.open(png_path)
        if resize and max(img.size) > resize:
            ratio = resize / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        kazanim_list = ", ".join(MEB_KAZANIM.get(subject_key, MEB_KAZANIM["turkce"]))
        prompt = PROMPT_TEMPLATE.format(kazanim_list=kazanim_list)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt, "image": b64}],
            "stream": False,
        }
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())

        content = result["message"]["content"].strip()

        # Regex ile alan bazlı çıkarma (JSON parse yerine)
        import re
        kod_match = re.search(r'KOD-8[./][A-Z]{2,3}[./]?\d{2}', content)
        zorluk_match = re.search(r'"?zorluk"?\s*:\s*(\d+)', content)

        if kod_match and zorluk_match:
            kod = kod_match.group(0).replace("/", ".")
            zorluk = int(zorluk_match.group(1))
            zorluk = max(1, min(5, zorluk))  # 1-5 arası sınırla
            return {"kazanimKodi": kod, "zorluk": zorluk}

        return {"error": f"Regex eşleşmedi: {content[:200]}"}

    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", help="Sadece bu dersi analiz et (örn: turkce)")
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--ollama-model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-resize", type=int, default=256)
    args = parser.parse_args()

    # Bul subject key
    subject_key = None
    for k, v in SUBJECT_MAP.items():
        if args.subject and v == args.subject.lower():
            subject_key = v
            break
    
    if not subject_key:
        print(f"Geçersiz subject: {args.subject}")
        return

    # Bul analysis.jsonl
    analysis_file = LGS_DIR / f"analysis_{subject_key}.jsonl"
    done = set()
    if analysis_file.exists():
        for line in analysis_file.open():
            try:
                rec = json.loads(line)
                # Sadece başarılı kayıtları "done" say
                if "kazanimKodi" in rec and "error" not in rec:
                    done.add(f"{rec['year']}_{rec['questionNumber']:03d}")
            except:
                pass

    # Tüm yılları tara
    total = 0
    for year_dir in sorted(LGS_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        manifest_path = year_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        
        manifest = json.loads(manifest_path.read_text())
        
        for subj in manifest.get("subjects", []):
            source = subj.get("source", {})
            subj_name = source.get("subject", "")
            
            # Subject kontrolü
            mapped = None
            for k, v in SUBJECT_MAP.items():
                if k in subj_name:
                    mapped = v
                    break
            if mapped != subject_key:
                continue
            
            year = source.get("examYear")
            questions = subj.get("questions", [])
            
            for q in questions:
                qnum = q["questionNumber"]
                key = f"{year}_{qnum:03d}"
                
                if key in done:
                    continue
                
                # Bul PNG dosyası
                png_path = None
                for png_file in year_dir.rglob("*.png"):
                    if q.get("visual", {}).get("publicPath") and q["visual"]["publicPath"] in str(png_file):
                        png_file = png_file.resolve()
                        break
                    # Alternatif: dosya adından bul
                    if f"q-{qnum:02d}.png" in str(png_file) or f"q-{qnum}.png" in str(png_file):
                        png_path = png_file.resolve()
                        break
                
                if not png_path or not png_path.exists():
                    print(f"  ⚠️ PNG bulunamadı: {year} Soru {qnum}")
                    continue
                
                # AI analizi
                print(f"  🔍 {year} Soru {qnum} analiz ediliyor...")
                result = analyze_question(str(png_path), subject_key, args.ollama_model, args.ollama_resize)
                
                # Kaydet
                with analysis_file.open("a") as f:
                    f.write(json.dumps({
                        "year": year,
                        "questionNumber": qnum,
                        "topic": q.get("topic"),
                        "page": q.get("page"),
                        **result
                    }, ensure_ascii=False) + "\n")
                
                done.add(key)
                total += 1
                time.sleep(0.5)  # Rate limit

    print(f"\n✅ Toplam {total} soru analiz edildi")


if __name__ == "__main__":
    main()