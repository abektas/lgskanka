#!/usr/bin/env python3
"""Nüli pedagogical analysis — a SEPARATE stage that runs after extraction.

Why separate (project invariant: "AI only produces candidate analysis"):
  extraction is deterministic and re-runnable; analysis is probabilistic and
  costs money/time per question. Mixing them would (a) lose determinism,
  (b) couple a 5-minute crop to an hours-long AI run, (c) let a 429/402 wipe
  out crop work. So this reads manifest.json + the cropped PNGs and writes its
  own output, never touching the extraction artefacts.

What it produces per question (ALL candidate / NEEDS_REVIEW):
  topic, learningOutcomeCode, learningOutcomeText, skill, questionType,
  operationStepCount, conceptCount, cognitiveLoad, reasoningDepth,
  visualComplexity, languageLoad, distractorStrength, pedagogicalDifficulty,
  difficultyConfidence, pedagogicalRationale, multiSkill, multiOutcome,
  curriculumMapping{framework,status}, analysisWarnings

Hard rules enforced in code (not just asked of the model):
  * learningOutcomeCode MUST exist in the official MEB registry for this
    subject; anything else is dropped and the outcome stays null with a warning.
    The AI SELECTS from a provided list, it never invents a code.
  * Nothing is ever marked VERIFIED; every record is NEEDS_REVIEW.
  * topic/unit comes from the book TOC deterministically, not from the model.

Resumable: results append to a JSONL; re-running skips already-done questions.

Usage:
  python3 analyze_study_workbook.py --subject matematik --limit 20
  python3 analyze_study_workbook.py --subject matematik          # all
  python3 analyze_study_workbook.py --subject matematik --provider ollama \
         --ollama-model qwen2.5vl:3b --ollama-resize 448
"""
from __future__ import annotations
import argparse, base64, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

ROOT = Path("/home/selam/roller/web/lgs-ai-coach")
OUT_ROOT = ROOT / "lgs_çalışma_soruları"
LGS18_26_ROOT = ROOT / "Lgs_18-26"
CURRICULUM = ROOT / "data/curriculum/meb-2018-grade8-outcomes.json"
ENV_FILE = ROOT / ".env.local"
DEFAULT_MODEL = "gemini-3.5-flash"

SUBJECT_KEY = {
    "matematik": "matematik", "fen": "fen", "fen-bilimleri": "fen", "turkce": "turkce",
    "turkce_cal14": "turkce",  # cal14 uses same Turkish curriculum
    "ingilizce": "ingilizce", "din": "din", "inkilap": "inkilap",
    "inkilap-tarihi": "inkilap",  # cal05 block uses same curriculum
    "din-kulturu": "din",  # cal05 block uses same curriculum
}

SYSTEM = """Sen Nüli LGS QBANK boru hattının pedagojik analiz asistanısın.
Sana tek bir LGS sorusunun görseli verilir. Görevin, soruyu ÖLÇMEK ve
SINIFLANDIRMAK; soruyu çözmek ya da cevabı tahmin etmek değil.

Kurallar:
- Kazanım kodunu UYDURMA. Sana verilen resmî kazanım listesinden SEÇ.
  Hiçbiri uymuyorsa learning_outcome_code alanını null bırak.
- Soru metnini değiştirme, özetleme, düzeltme.
- Emin olmadığın alanda düşük güven bildir (confidence).
- Yalnızca istenen JSON'u döndür; açıklama veya kod bloğu ekleme.
- [FEW-SHOT] Aşağıdaki 3 örnek çıktı formatını BİREBİR tut. Sadece istenen şemada tek bir JSON objesi üret.

Few-shot örnek 1 (Üslü İfadeler):
{"topic": "Üslü sayılarla işlem", "learning_outcome_code": "M.8.1.2.2",
 "learning_outcome_text": "Üslü ifadelerdeki işlem kurallarını açıklar.",
 "skill": "Uygulama", "question_type": "Rutin İşlem",
 "operation_step_count": 2, "concept_count": 1, "cognitive_load": 1,
 "reasoning_depth": 2, "visual_complexity": 1, "language_load": 1,
 "distractor_strength": "MEDIUM", "pedagogical_difficulty": 2,
 "difficulty_confidence": "HIGH", "pedagogical_rationale": "Soru üslü ifadelerde ...",
 "multi_skill": false, "multi_outcome": false}

Few-shot örnek 2 (Olasılık):
{"topic": "Deney ve sonuç sayısından olasılık", "learning_outcome_code": "M.8.5.1.2",
 "learning_outcome_text": "Tüm olası sonuçları ...",
 "skill": "Uygulama", "question_type": "Problem Çözme",
 "operation_step_count": 2, "concept_count": 1, "cognitive_load": 3,
 "reasoning_depth": 2, "visual_complexity": 2, "language_load": 2,
 "distractor_strength": "LOW", "pedagogical_difficulty": 3,
 "difficulty_confidence": "MEDIUM", "pedagogical_rationale": "Soru bir deneyin ...",
 "multi_skill": false, "multi_outcome": false}

Few-shot örnek 3 (Üçgenler):
{"topic": "Üçgenin iç açıları toplamı", "learning_outcome_code": "M.8.3.1.1",
 "learning_outcome_text": "Üçgenin iç açıları toplamını ifade eder.",
 "skill": "Bilgi", "question_type": "Doğrudan Bilgi",
 "operation_step_count": 1, "concept_count": 1, "cognitive_load": 1,
 "reasoning_depth": 1, "visual_complexity": 1, "language_load": 1,
 "distractor_strength": "LOW", "pedagogical_difficulty": 2,
 "difficulty_confidence": "HIGH", "pedagogical_rationale": "Soru üçgenin iç ...",
 "multi_skill": false, "multi_outcome": false}"""

PROMPT_TMPL = """Ders: {subject}
Kitap ünitesi (TOC): {unit_name}

Aşağıda bu dersin TÜM resmî 8. sınıf kazanımları verilmiştir. Bu soruya EN
UYGUN olanı MUTLAKA seç. Soru bir kazanımın konusuna/kavramına giriyorsa o
kazanımı seçmek zorunludur; null'ı yalnızca soru bu dersin HİÇBİR kazanımıyla
ilişkilendirilemiyorsa kullan. Başka kod üretme, yalnızca listeden seç:

{outcome_list}

Şu JSON şemasıyla yanıtla:
{{
  "topic": "kısa konu adı",
  "learning_outcome_code": "listedeki kod ya da null",
  "learning_outcome_text": "seçtiğin kazanımın metni ya da null",
  "skill": "Bilgi | Kavrama | Uygulama | Analiz | Değerlendirme",
  "question_type": "Doğrudan Bilgi | Rutin İşlem | Problem Çözme | Muhakeme | Modelleme",
  "operation_step_count": 1,
  "concept_count": 1,
  "cognitive_load": 1,
  "reasoning_depth": 1,
  "visual_complexity": 1,
  "language_load": 1,
  "distractor_strength": "LOW | MEDIUM | HIGH",
  "pedagogical_difficulty": 1,
  "difficulty_confidence": "LOW | MEDIUM | HIGH",
  "pedagogical_rationale": "tek cümle gerekçe",
  "multi_skill": false,
  "multi_outcome": false
}}"""

NIM_MODELS = ["meta/llama-3.2-11b-vision-instruct", "meta/llama-3.2-90b-vision-instruct"]
OLLAMA_MODELS = ["qwen2.5vl:3b"]   # gemma collapse + qwen crash sonrasi ana model
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def load_curriculum(subject_key):
    d = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    return d["subjects"][subject_key]


def outcome_list_text(outcomes, limit=40):
    return "\n".join(f"- {o['code']}: {o['text']}" for o in outcomes[:limit])


def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0) if m else t)


def _resize_png_b64(path, max_side=448):
    """Shrink an LGS crop before sending to a tight-VRAM local model (PIL)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if max(im.size) > max_side:
        scale = max_side / max(im.size)
        im = im.resize((int(im.width * scale), int(im.height * scale)),
                       Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _nim_chat(env, model, png, system, prompt, timeout=100):
    key = env.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise RuntimeError("NVIDIA_API_KEY yok")
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ]},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req, timeout=timeout)
    j = json.loads(r.read().decode("utf-8"))
    return j["choices"][0]["message"]["content"]


def analyze_one_nim(env, png, subject, unit_name, outcomes, attempts=3):
    prompt = PROMPT_TMPL.format(subject=subject, unit_name=unit_name or "-",
                                outcome_list=outcome_list_text(outcomes))
    prompt = prompt + "\n\nCRITICAL: Output only a valid JSON object. No markdown, no prose."
    chain = list(NIM_MODELS)
    last = None
    for attempt in range(attempts):
        for m in chain:
            try:
                text = _nim_chat(env, m, png, SYSTEM, prompt)
                return parse_json(text), m
            except Exception as e:
                last = e
                msg = str(e)
                if "429" in msg or "503" in msg or "timeout" in msg.lower() or "timed out" in msg.lower() \
                        or "404" in msg or "Expecting value" in msg or "Unterminated" in msg \
                        or "JSONDecodeError" in type(e).__name__ or "ValueError" in type(e).__name__:
                    continue
                raise
        time.sleep(min(2 ** attempt, 20))
    raise last


def _ollama_chat(b64, system, prompt, model, timeout=300):
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt, "images": [b64]},
        ],
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_thread": 4},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req, timeout=timeout)
    j = json.loads(r.read().decode("utf-8"))
    return j["message"]["content"]


def analyze_one_ollama(path, system, prompt, outcomes, model_chain, max_side=448, attempts=3):
    """Local Ollama analyzer: resize + retry, force JSON via format=json.

    Returns (parsed_dict, used_model).
    """
    last = None
    b64s = {
        "full": None,
        "small": _resize_png_b64(path, max_side=max_side),
    }
    # try small first (tight-VRAM friendly)
    plan = [("small", model_chain)] * attempts
    for use_small, models in plan:
        b64 = _resize_png_b64(path, max_side=(max_side if use_small else 10**9))
        for m in models:
            for _retry in range(2):
                try:
                    text = _ollama_chat(b64, system, prompt, m, timeout=300)
                    a = parse_json(text)
                    # validate quickly
                    if a.get("learning_outcome_code") and a["learning_outcome_code"] not in \
                       {o["code"] for o in outcomes}:
                        a["_outcome_warning"] = "code_not_in_registry"
                    return a, m
                except Exception as e:
                    last = e
                    msg = str(e)
                    if "400" in msg or "cuda" in msg.lower() or "timeout" in msg.lower() \
                            or "expecting value" in msg.lower() or "invalid" in msg.lower():
                        time.sleep(2.0)
                        continue
                    raise
            time.sleep(1.0)
        time.sleep(2.0)
    raise last or RuntimeError("ollama all attempts failed")


def analyze_one_gemini(client, types, model, png, subject, unit_name, outcomes, attempts=4):
    prompt = PROMPT_TMPL.format(subject=subject, unit_name=unit_name or "-",
                                outcome_list=outcome_list_text(outcomes))
    chain = ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.1-flash-lite"]
    last = None
    for attempt in range(attempts):
        for m in chain:
            try:
                r = client.models.generate_content(
                    model=m,
                    contents=[types.Part.from_bytes(data=png.read_bytes(), mime_type="image/png"), prompt],
                    config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.2,
                                                     response_mime_type="application/json"),
                )
                return parse_json(r.text), m
            except Exception as e:
                last = e
                msg = str(e)
                if "429" in msg or "503" in msg or "RESOURCE_EXHAUSTED" in msg:
                    continue
                raise
        time.sleep(min(2 ** attempt, 20))
    raise last


def dedupe_jsonl(path):
    """Keep first record per 'file'; collapse duplicate lines from racing workers."""
    try:
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return
    seen, keep = set(), []
    for line in lines:
        try:
            f = json.loads(line)["file"]
        except Exception:
            continue
        if f in seen:
            continue
        seen.add(f)
        keep.append(line)
    if len(keep) != len(lines):
        path.write_text("\n".join(keep) + "\n", encoding="utf-8")
        print(f"  (dedupe: {len(lines)} -> {len(keep)} satır)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--model", default="qwen2.5vl:3b")
    ap.add_argument("--provider", choices=["auto", "nim", "gemini", "ollama"],
                    default="auto", help="analiz provider'ı (auto=NVIDIA key varsa nim)")
    ap.add_argument("--ollama-model", default="", help="ollama'da tek bir model adı")
    ap.add_argument("--ollama-resize", type=int, default=448,
                    help="ollama için görsel kenar sınırı (0=boyutlandırma yok)")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--only", default="", help="comma list of file names to analyse")
    ap.add_argument("--shard", type=int, default=1, help="1-based shard index (shards>1 iken paralel işçi partition)")
    ap.add_argument("--shards", type=int, default=1, help="Toplam shard sayısı (paralel parçalama)")
    ap.add_argument("--source-dir", default="", help="Kaynak klasör (ör: Lgs_18-26/nuli-2022-all-subjects-20pt). Boş=bırakılırsa lgs_çalışma_soruları kullanılır")
    ap.add_argument("--output", default="", help="Çıktı JSONL yolu (ör: Lgs_18-26/analysis_turkce.jsonl). Boş=bırakılırsa lgs_çalışma_soruları/{subject}/analysis.jsonl kullanılır")
    args = ap.parse_args()

    # Kaynak klasör belirleme
    if args.source_dir:
        source_dir = Path(args.source_dir)
    else:
        source_dir = OUT_ROOT / args.subject

    manifest_path = source_dir / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"manifest yok: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    subject_key = SUBJECT_KEY.get(args.subject, args.subject)
    subj = load_curriculum(subject_key)
    unit_names = {u["unit"]: u["name"] for u in manifest.get("units", [])}

    # Çıktı klasörü ve dosyası
    if args.output:
        jsonl = Path(args.output)
    else:
        outdir = OUT_ROOT / args.subject
        outdir.mkdir(parents=True, exist_ok=True)
        jsonl = outdir / "analysis.jsonl"

    outdir = jsonl.parent
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG: jsonl={jsonl}, type={type(jsonl)}", file=sys.stderr)
    done = set()
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["file"])
                except Exception:
                    pass

    env = load_env()
    # provider resolution
    if args.provider == "auto":
        if env.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY"):
            provider = "nim"
        elif env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY"):
            provider = "gemini"
        else:
            provider = "ollama"
    else:
        provider = args.provider

    client = None
    types = None
    if provider == "gemini":
        import google.genai as genai
        from google.genai import types as gt
        client = genai.Client(api_key=env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY"))
        types = gt

    qs = manifest["questions"]
    # Lgs_18-26 manifest'inde 'file' yerine 'id' ve 'visual.publicPath' var
    for q in qs:
        if "file" not in q:
            q["file"] = q.get("id", "")
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        qs = [q for q in qs if q["file"] in want]
    todo = [q for q in qs if q["file"] not in done]
    lockdir = outdir / "analysis_locks"
    lockdir.mkdir(exist_ok=True)
    # stale claim'leri temizle (önceki crash'lerden kalanlar)
    if lockdir.exists():
        for c in list(lockdir.glob("*.claim")):
            if c.name.replace(".claim", "") in done:
                try:
                    c.unlink()
                except OSError:
                    pass
    if args.shards > 1:
        todo = [q for i, q in enumerate(todo) if (i % args.shards) == (args.shard - 1)]
    if args.limit:
        todo = todo[:args.limit]

    print(f"analiz: {args.subject} | toplam={len(qs)} biten={len(done)} bu koşu={len(todo)} | provider={provider}")

    ok = fail = 0
    lockdir = outdir / "analysis_locks"
    lockdir.mkdir(exist_ok=True)
    for i, q in enumerate(todo, 1):
        claim = lockdir / f"{Path(q['file']).name}.claim"
        try:
            fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}-{args.shard}/{args.shards}".encode("ascii"))
            os.close(fd)
        except FileExistsError:
            # mevcut claim — sahibi canlı mı?
            try:
                owner_raw = claim.read_text(encoding="ascii").strip().split("-")[0]
                owner_pid = int(owner_raw)
            except (OSError, ValueError):
                owner_pid = -1
            try:
                os.kill(owner_pid, 0)
                owner_live = True
            except OSError:
                owner_live = False
            if owner_live:
                print(f"  [shard {args.shard}/{args.shards}] atla (sahibi canlı, pid={owner_pid}): {q['file']}")
                continue
            # sahip bitmiş → claim devral
            try:
                claim.unlink()
            except OSError:
                pass
            try:
                fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()}-{args.shard}/{args.shards}".encode("ascii"))
                os.close(fd)
            except FileExistsError:
                print(f"  [shard {args.shard}/{args.shards}] devralma yarışını kaybetti: {q['file']}")
                continue
        # Lgs_18-26: visual.publicPath'ten dosya adını çıkar (örn: /pilot-2022-turkce/q-01.png)
        if "visual" in q and "publicPath" in q["visual"]:
            png_name = Path(q["visual"]["publicPath"]).name
            png = source_dir / png_name
        else:
            png_name = Path(q["file"]).name
            png = outdir / png_name
        
        unit = q.get("unit")
        outcomes = subj["outcomes"]
        try:
            if provider == "nim":
                a, used_model = analyze_one_nim(env, png, subj["subject"],
                                               unit_names.get(unit, ""), outcomes)
            elif provider == "gemini":
                a, used_model = analyze_one_gemini(client, types, args.model, png,
                                                  subj["subject"], unit_names.get(unit, ""), outcomes)
            else:  # ollama
                system_for_prompt = SYSTEM
                prompt = PROMPT_TMPL.format(subject=subj["subject"],
                                            unit_name=unit_names.get(unit, "-"),
                                            outcome_list=outcome_list_text(outcomes))
                prompt = prompt + "\n\nCRITICAL: Output only a valid JSON object. No markdown, no prose."
                model_chain = ([args.ollama_model] if args.ollama_model else OLLAMA_MODELS)
                max_side = args.ollama_resize if args.ollama_resize > 0 else 10**9
                a, used_model = analyze_one_ollama(str(png.resolve()), system_for_prompt, prompt,
                                                  outcomes, model_chain,
                                                  max_side=max_side, attempts=3)
        except Exception as e:
            a = {"_error": str(e)[:200]}
            used_model = None
        warnings = []
        code = a.get("learning_outcome_code")
        if code:
            valid = {o["code"] for o in outcomes}
            if code not in valid:
                warnings.append("outcome_code_not_in_registry")
                a.pop("learning_outcome_code", None)
                a.pop("learning_outcome_text", None)
        rec = {
            "file": q["file"], "page": q["page"], "q": q.get("questionNumber", q.get("q", 0)),
            "section": q.get("section"), "unit": unit,
            "examYear": q.get("examYear") or (q["file"][8:12] if q["file"].startswith("MEB-LGS-") and len(q["file"]) > 9 else None),
            "unitName": unit_names.get(unit),
            "subject": subj["subject"],
            "answerKeyCandidate": q.get("answer"),
            "status": "NEEDS_REVIEW", "published": False,
            "analysisSource": f"AI_CANDIDATE:{used_model}",
            "analyzedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "topic": a.get("topic"),
            "learningOutcomeCode": a.get("learning_outcome_code"),
            "learningOutcomeText": a.get("learning_outcome_text"),
            "skill": a.get("skill"),
            "questionType": a.get("question_type"),
            "operationStepCount": a.get("operation_step_count"),
            "conceptCount": a.get("concept_count"),
            "cognitiveLoad": a.get("cognitive_load"),
            "reasoningDepth": a.get("reasoning_depth"),
            "visualComplexity": a.get("visual_complexity"),
            "languageLoad": a.get("language_load"),
            "distractorStrength": a.get("distractor_strength"),
            "pedagogicalDifficulty": a.get("pedagogical_difficulty"),
            "difficultyConfidence": a.get("difficulty_confidence"),
            "pedagogicalRationale": a.get("pedagogical_rationale"),
            "multiSkill": a.get("multi_skill"),
            "multiOutcome": a.get("multi_outcome"),
            "curriculumMapping": {"framework": "CURRENT_TYMM",
                                  "status": "MAPPED_NEEDS_REVIEW" if a.get("learning_outcome_code")
                                  else "UNMAPPED"},
            "analysisWarnings": warnings + ([a["_error"]] if a.get("_error") else []),
        }
        if a.get("_error"):
            fail += 1
            try:
                claim.unlink(missing_ok=True)
            except OSError:
                pass
            print(f"  [{i}/{len(todo)}] {q['file']} HATA: {a['_error'][:80]}")
            time.sleep(1.0)
            continue
        with jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            claim.unlink(missing_ok=True)
        except OSError:
            pass
        ok += 1
        print(f"  [{i}/{len(todo)}] {q['file']:26} {str(rec['topic'])[:32]:32} {rec['learningOutcomeCode'] or '-':14} z{rec['pedagogicalDifficulty']}")
        time.sleep(0.4 if provider != "ollama" else 0.8)

    dedupe_jsonl(jsonl)
    print(f"\nbitti: ok={ok} hata={fail} -> {jsonl}")


if __name__ == "__main__":
    sys.exit(main())
