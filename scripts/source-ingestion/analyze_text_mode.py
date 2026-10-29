#!/usr/bin/env python3
"""Hybrid TEXT-first analyser (no OCR, no reliance on reading text from pixels).

WHY: measured on this machine, a local 4B VLM cannot read Turkish question text from
a crop at ANY resize (150/192/256/448/768 all produced word-salad). The workbook PDFs
have an exact text layer, so the semantic fields (topic, learning outcome, question
type, language load, distractor strength) are derived from TEXT, which is both exact
and far cheaper (no vision encoder). The image is attached ONLY for questions that
actually contain a figure, where coarse visual structure (bar chart / table / cartoon)
still matters for visual_complexity.

GÖRSEL OKUMA questions are marked NEEDS_REVIEW with an explicit warning: their answer
depends on reading data out of a figure, which the model must not fabricate.

TWO QUALITY GUARDS (both measured on the 10-question pilot):
  1. The outcome list is FILTERED to the ~8 outcomes most relevant to the question's
     topic (keyword overlap). Sending all 76 outcomes made the model pick wrong codes
     (e.g. "metnin konusu" for a question about expression features).
  2. If the model returns a code that is not in the registry, the call is retried once
     with an explicit warning; only a second failure leaves the field null.

Usage:
  python3 analyze_text_mode.py --manifest <manifest.json> --output <out.jsonl> \
      --subject turkce --limit 10
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import re
import unicodedata
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
CURRIC = REPO / "data/curriculum/meb-2018-grade8-outcomes.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
SUBJECT_KEY = {"turkce": "turkce", "matematik": "matematik", "fen-bilimleri": "fen",
               "ingilizce": "ingilizce", "din-kulturu": "din", "inkilap-tarihi": "inkilap"}

SYSTEM = "Sen LGS analiz asistanı. Sadece istenen JSON'u döndür."

PROMPT = """Ders: {subject}
Konu başlığı (kitaptan): {topic}
{visual_note}
Aşağıda bu dersin TÜM resmî 8. sınıf kazanımları var. Bu soruya EN UYGUN olanı MUTLAKA seç;
null'ı yalnızca hiçbiri uymuyorsa kullan. Başka kod üretme:

{outcome_list}

=== SORU METNİ (PDF metin katmanından, birebir) ===
{question_text}
=== SORU METNİ SONU ===

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
  "visual_kind": "yok | grafik | tablo | şekil | karikatür | harita | diğer",
  "language_load": 1,
  "distractor_strength": "LOW | MEDIUM | HIGH",
  "pedagogical_difficulty": 1,
  "difficulty_confidence": "LOW | MEDIUM | HIGH",
  "pedagogical_rationale": "tek cümle gerekçe",
  "multi_skill": false,
  "multi_outcome": false
}}"""


def load_outcomes(subject_key):
    d = json.loads(CURRIC.read_text(encoding="utf-8"))
    subj = d["subjects"][subject_key]
    return subj["subject"], subj["outcomes"]


def outcome_list_text(outcomes):
    return "\n".join(f'- {o["code"]}: {o["text"]}' for o in outcomes)


STOP = {"ve", "ile", "bir", "bu", "şu", "o", "da", "de", "ki", "mi", "mı", "mu", "mü",
        "için", "gibi", "kadar", "daha", "çok", "en", "her", "tüm", "bütün", "olarak",
        "ise", "ama", "fakat", "ancak", "ya", "hem", "ne", "the", "a", "an", "of",
        "to", "in", "on", "at", "by", "for", "and", "or", "is", "are", "be", "hangi",
        "hangisidir", "aşağıdaki", "yukarıdaki", "verilen", "ilgili", "soru", "soruda"}
TOKEN = re.compile(r"[a-zçğıöşüâîû0-9]+", re.IGNORECASE)


def _stem(t):
    """Turkish is agglutinative ('anlamını' vs 'anlamı'); compare 5-char roots."""
    return t[:5] if len(t) >= 5 else t


def _norm(s):
    # Turkish 'İ' lowercases to 'i' + U+0307; NFKD then drop combining marks so the
    # tokenizer sees whole words instead of fragments ('HİKÂYE' -> 'kâye').
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def tokens(text):
    return {_stem(t) for t in TOKEN.findall(_norm(text).lower())
            if t not in STOP and len(t) > 2}


TOPIC_EXTRA = {
    "GÖRSEL OKUMA": ["T.8.3.32", "T.8.3.27"],
    "SÖZEL MANTIK": ["T.8.3.21", "T.8.3.22"],
    "MUHAKEME": ["T.8.3.21", "T.8.3.22", "T.8.3.34"],
    "FİİLİMSİLER": ["T.8.3.33"],
    "YAZIM KURALLARI": ["T.8.3.8", "T.8.4.16"],
    "CÜMLEDE ANLAM": ["T.8.3.10", "T.8.3.18"],
    "PARÇADA ANLAM": ["T.8.3.17", "T.8.3.18"],
}


def _extra_codes(topic_text):
    t = (topic_text or "").upper()
    return list(dict.fromkeys(c for k, v in TOPIC_EXTRA.items() if k in t for c in v))


def filter_outcomes(topic_text, outcomes, k=8):
    """Topic-relevant outcomes: a small explicit supplement for topics whose book
    title shares no vocabulary with the outcome texts, then lexical matches."""
    by_code = {o["code"]: o for o in outcomes}
    picks, seen = [], set()
    for c in _extra_codes(topic_text):
        if c in by_code and c not in seen:
            picks.append(by_code[c]); seen.add(c)
    tt = tokens(topic_text)
    if tt:
        scored = []
        for o in outcomes:
            s = len(tt & tokens(o["text"]))
            if s:
                scored.append((s, o["code"], o))
        scored.sort(key=lambda x: (-x[0], x[1]))
        for _, _, o in scored:
            if o["code"] not in seen:
                picks.append(o); seen.add(o["code"])
            if len(picks) >= k:
                break
    return picks or outcomes


def build_prompt(subject, topic, visual_note, outcomes, question_text):
    return f"{subject} | {topic}\n{visual_note}\nKazanımlar:\n{outcome_list_text(outcomes)}\nSoru:\n{question_text[:4000]}\nJSON."


def b64_image(path: Path, max_side=256):
    im = Image.open(path).convert("RGB")
    if max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def ollama_chat(model, system, prompt, image_b64=None, timeout=300):
    user = {"role": "user", "content": prompt}
    if image_b64:
        user["images"] = [image_b64]
    payload = {
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "system", "content": system}, user],
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_thread": 4},
    }
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read().decode("utf-8"))["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--subject", default="turkce")
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated question ids")
    ap.add_argument("--crop-dir", default=str(REPO / "lgs_çalışma_soruları/turkce"))
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    qs = man["questions"]
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        qs = [q for q in qs if q["id"] in want]
    if args.limit:
        qs = qs[:args.limit]

    out_path = Path(args.output)
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["file"])
                except Exception:
                    pass

    subj_name, all_outcomes = load_outcomes(SUBJECT_KEY[args.subject])
    valid_codes = {o["code"] for o in all_outcomes}
    crop_dir = Path(args.crop_dir)

    todo = [q for q in qs if q["file"] not in done]
    print(f"manifest: {len(qs)} soru | biten: {len(done)} | bu koşu: {len(todo)}")
    print(f"model: {args.model} | şekilli: {sum(1 for q in todo if q.get('hasFigure'))}")

    ok = fail = 0
    t0 = time.time()
    for i, q in enumerate(todo, 1):
        txt = q.get("questionText", "")
        has_fig = bool(q.get("hasFigure"))
        topic = q.get("topicFull") or q.get("topic", "-")
        visual_note = ("Bu soruda GÖRSEL/ŞEKİL vardır; görsel ayrıca eklenmiştir. "
                       "Görselin türünü ve karmaşıklığını değerlendir, verisini okumaya çalışma."
                       if has_fig else "Bu soruda görsel yok; yalnızca metne göre değerlendir.")
        outcomes = filter_outcomes(topic, all_outcomes)
        prompt = build_prompt(subj_name, topic, visual_note, outcomes, txt)
        img = None
        if has_fig:
            p = crop_dir / q["file"]
            if p.exists():
                try:
                    img = b64_image(p)
                except Exception:
                    img = None

        raw = None
        a = None
        for attempt in (1, 2):
            try:
                raw = ollama_chat(args.model, SYSTEM, prompt, img)
                a = json.loads(raw)
            except Exception as e:
                if attempt == 1:
                    print(f"  [{i}/{len(todo)}] {q['id']} ağ hatası, tekrar: {str(e)[:50]}")
                    time.sleep(2.0)
                    continue
                fail += 1
                print(f"  [{i}/{len(todo)}] {q['id']} HATA: {str(e)[:70]}")
                time.sleep(1.0)
                break
            code = a.get("learning_outcome_code")
            if code and code not in valid_codes:
                if attempt == 1:
                    prompt += (f"\n\nUYARI: önceki denemede listede olmayan '{code}' kodunu "
                               f"ürettin. YALNIZCA yukarıdaki listeden bir kod seç.")
                    continue
                a["learning_outcome_code"] = None
                a["learning_outcome_text"] = None
            break
        if raw is None or a is None:
            continue

        warnings = []
        code = a.get("learning_outcome_code")
        if code and code not in valid_codes:
            warnings.append("outcome_code_not_in_registry")
            code = None
            a["learning_outcome_text"] = None
        if q.get("topic", "").startswith("GÖRSEL OKUMA"):
            warnings.append("visual_data_not_readable_by_ai")
        if not txt:
            warnings.append("no_text_layer")

        rec = {
            "file": q["file"], "page": q.get("page"), "q": q.get("q_in_test"),
            "section": q.get("test"), "unit": None, "examYear": q.get("examYear", 2023),
            "unitName": q.get("topicFull") or q.get("topic"), "subject": subj_name,
            "answerKeyCandidate": q.get("answer"),
            "status": "NEEDS_REVIEW", "published": False,
            "analysisSource": f"AI_CANDIDATE:{args.model}+PDF_TEXT",
            "analysisMode": "hybrid_text" + ("+image" if img else ""),
            "analyzedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "topic": a.get("topic"),
            "learningOutcomeCode": code,
            "learningOutcomeText": a.get("learning_outcome_text"),
            "skill": a.get("skill"), "questionType": a.get("question_type"),
            "operationStepCount": a.get("operation_step_count"),
            "conceptCount": a.get("concept_count"),
            "cognitiveLoad": a.get("cognitive_load"),
            "reasoningDepth": a.get("reasoning_depth"),
            "visualComplexity": a.get("visual_complexity"),
            "visualKind": a.get("visual_kind"),
            "languageLoad": a.get("language_load"),
            "distractorStrength": a.get("distractor_strength"),
            "pedagogicalDifficulty": a.get("pedagogical_difficulty"),
            "difficultyConfidence": a.get("difficulty_confidence"),
            "pedagogicalRationale": a.get("pedagogical_rationale"),
            "multiSkill": a.get("multi_skill"), "multiOutcome": a.get("multi_outcome"),
            "curriculumMapping": {"framework": "CURRENT_TYMM",
                                  "status": "MAPPED_NEEDS_REVIEW" if code else "UNMAPPED"},
            "analysisWarnings": warnings,
        }
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ok += 1
        rate = (time.time() - t0) / i
        print(f"  [{i}/{len(todo)}] {q['id']:20s} {str(rec['topic'])[:26]:26s} "
              f"{str(code):10s} z{rec['pedagogicalDifficulty']} {str(rec['difficultyConfidence'] or ''):6s} "
              f"{'IMG' if img else 'txt'} {rate:.1f}s/soru")

    print(f"\nbitti: ok={ok} hata={fail} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())