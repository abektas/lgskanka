#!/usr/bin/env python3
"""LGS 18-26 TEXT-FIRST HYBRID ANALYSER (no OCR, no reading text from pixels).

WHY: local VLM cannot read Turkish question text from crops at any resize.
PDFs have exact text layer, so semantic fields (topic, learning outcome, type,
language load, distractor strength) come from TEXT — exact and far cheaper.
Image attached ONLY for questions that actually contain a figure, where coarse
visual structure (diagram / table / graph) matters for visual_complexity.

GÖRSEL OKUMA / visual-dependent questions marked NEEDS_REVIEW with explicit
warning: their answer depends on reading data out of a figure, which the model
must not fabricate.

Usage:
  python3 analyze_lgs18_26_text.py --manifest-dir <lgs_18_26> --output <out.jsonl> \
      --subject turkce --model gemma3:4b --limit 10
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

REPO = Path("/home/selam/roller/web/lgs-ai-coach")
CURRIC = REPO / "data/curriculum/meb-2018-grade8-outcomes.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
SUBJECT_KEY = {
    "turkce": "turkce", "matematik": "matematik", "fen-bilimleri": "fen",
    "ingilizce": "ingilizce", "din-kulturu": "din", "inkilap-tarihi": "inkilap"
}

STOP = {"ve", "ile", "bir", "bu", "şu", "o", "da", "de", "ki", "mi", "mı", "mu", "mü",
        "için", "gibi", "kadar", "daha", "çok", "en", "her", "tüm", "bütün", "olarak",
        "ise", "ama", "fakat", "ancak", "ya", "hem", "ne", "the", "a", "an", "of",
        "to", "in", "on", "at", "by", "for", "and", "or", "is", "are", "be", "hangi",
        "hangisidir", "aşağıdaki", "yukarıdaki", "verilen", "ilgili", "soru", "soruda"}
TOKEN = re.compile(r"[a-zçğıöşüâîû0-9]+", re.IGNORECASE)


def _norm(s):
    return "".join(c for c in __import__("unicodedata").normalize("NFKD", s or "")
                   if not __import__("unicodedata").combining(c))


def _stem(t):
    return t[:5] if len(t) >= 5 else t


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


def load_outcomes(subject_key):
    d = json.loads(CURRIC.read_text(encoding="utf-8"))
    subj = d["subjects"][subject_key]
    return subj["subject"], subj["outcomes"]


def outcome_list_text(outcomes):
    return "\n".join(f'- {o["code"]}: {o["text"]}' for o in outcomes)


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


SYSTEM = "LGS analiz asistanı. Sadece JSON üret."

PROMPT = """{subject} | {topic}
{visual_note}
Kazanımlar:
{outcome_list}
Soru:
{question_text[:5000]}
JSON."""


def build_prompt(subject, topic, visual_note, outcomes, question_text):
    return PROMPT.format(subject=subject, topic=topic, visual_note=visual_note,
                         outcome_list=outcome_list_text(outcomes),
                         question_text=question_text[:6000])


def extract_question_text(pdf_path: Path, page_num: int, clip_rect: dict) -> str:
    """Extract text from PDF text layer within the question's clip rect."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_path)
    page = doc[page_num - 1]
    tp = page.get_textpage()
    H = page.get_size()[1]
    x0, y0, x1, y1 = clip_rect['x0'], clip_rect['y0'], clip_rect['x1'], clip_rect['y1']
    b = H - y1
    t = H - y0
    return tp.get_text_bounded(x0, b, x1, t).strip()


def needs_visual(txt: str) -> bool:
    """Heuristic: options are just A) B) C) D) with no text."""
    lines = txt.strip().split('\n')
    option_lines = [l for l in lines if l.strip().startswith(('A)', 'B)', 'C)', 'D)'))]
    for opt in option_lines:
        if len(opt.strip()) <= 3:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest-dir", required=True, help="lgs_18_26 root (contains turkce/, matematik/, etc)")
    ap.add_argument("--pdf-source-dir", required=True, help="Kaynak PDF'lerin olduğu dizin (Lgs_soruları)")
    ap.add_argument("--output", required=True)
    ap.add_argument("--subject", required=True, choices=list(SUBJECT_KEY.keys()))
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated question ids")
    args = ap.parse_args()

    manifest_dir = Path(args.manifest_dir)
    pdf_source_dir = Path(args.pdf_source_dir)
    subject = args.subject
    subj_upper = {"turkce": "TURKCE", "matematik": "MATEMATIK", "fen-bilimleri": "FEN",
                  "ingilizce": "INGILIZCE", "din-kulturu": "DIN", "inkilap-tarihi": "INKILAP"}[subject]
    subj_pdf_name = {"turkce": "Türkçe", "matematik": "Matematik", "fen-bilimleri": "Fen Bilimleri",
                     "ingilizce": "İngilizce", "din-kulturu": "Din Kültürü", "inkilap-tarihi": "İnkılap Tarihi"}[subject]

    # Load all manifests for this subject
    questions = []
    for man_file in sorted(manifest_dir.glob(f"{subject}/manifest_*.json")):
        man = json.loads(man_file.read_text(encoding="utf-8"))
        for q in man.get("questions", []):
            questions.append(q)

    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        questions = [q for q in questions if q.get("id") in want]
    if args.limit:
        questions = questions[:args.limit]

    out_path = Path(args.output)
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["file"])
                except Exception:
                    pass

    subj_name, all_outcomes = load_outcomes(SUBJECT_KEY[subject])
    valid_codes = {o["code"] for o in all_outcomes}

    todo = [q for q in questions if q.get("file") not in done]
    print(f"manifest: {len(questions)} soru | biten: {len(done)} | bu koşu: {len(todo)}")
    print(f"model: {args.model} | görsel-gerektiren: {sum(1 for q in todo if needs_visual(q.get('questionText','')))}")

    ok = fail = 0
    t0 = time.time()
    for i, q in enumerate(todo, 1):
        # Extract text from PDF if not already in manifest
        txt = q.get("questionText", "")
        if not txt:
            # Find the PDF for this year
            fid = q.get("id", "")
            year = fid[8:12] if fid.startswith("MEB-LGS-") else "2018"
            year_dir = f"Lgs_{year}" if year != "2024" else "Lgs-2024"
            # 2018-2023: hyphen, 2024-2025: en-dash, 2026: combined PDFs handled separately
            if int(year) >= 2024:
                sep = " – "
            else:
                sep = " "
            pdf_path = pdf_source_dir / year_dir / f"{year} LGS{sep}{subj_pdf_name}.pdf"
            if pdf_path.exists():
                txt = extract_question_text(pdf_path, q["page"], q["visual"]["clipRectPt"])
                q["questionText"] = txt  # cache for potential re-run

        has_fig = needs_visual(txt)
        topic = q.get("topic", "-")
        visual_note = ("Bu soruda GÖRSEL/ŞEKİL/FORMÜL vardır; görsel ayrıca eklenmiştir. "
                       "Görselin türünü ve karmaşıklığını değerlendir, verisini okumaya çalışma."
                       if has_fig else "Bu soruda görsel yok; yalnızca metne göre değerlendir.")
        outcomes = filter_outcomes(topic, all_outcomes)
        prompt = build_prompt(subj_name, topic, visual_note, outcomes, txt)
        img = None
        if has_fig:
            p = manifest_dir / subject / q["file"]
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
        if q.get("topic", "").startswith("GÖRSEL OKUMA") or needs_visual(txt):
            warnings.append("visual_data_not_readable_by_ai")
        if not txt:
            warnings.append("no_text_layer")

        rec = {
            "file": q["file"], "page": q.get("page"), "q": q.get("questionNumber"),
            "id": q.get("id"), "examYear": q.get("examYear") or (int(q["id"][8:12]) if q.get("id", "").startswith("MEB-LGS-") else None),
            "subject": subj_name,
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
        print(f"  [{i}/{len(todo)}] {q['id']:28s} {str(rec['topic'])[:24]:24s} "
              f"{str(code):10s} z{rec['pedagogicalDifficulty']} {rec['difficultyConfidence']:6s} "
              f"{'IMG' if img else 'txt'} {rate:.1f}s/soru")

    print(f"\nbitti: ok={ok} hata={fail} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())