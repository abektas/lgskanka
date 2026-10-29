#!/usr/bin/env python3
"""Standartlaştırma: her ders için TEK manifest.json + TEK answers.json + TEK analysis.jsonl.

Standart düzen:
  manifest.json   → {book, subject, total_questions, answerMappingStatus, questions:[...]}
  answers.json    → düz eşleme { "<png dosya adı>": "<harf>" }  (manifest'ten türetilir)
  analysis.jsonl  → her satır bir soru analizi, file alanı düz dosya adı

Idempotent: manifest.json zaten birleşik ürünse (book == "<SUBJ>_merged") ve başka
manifest*.json yoksa işlem atlanır. Bu sayede script tekrar çalıştırılabilir.
"""
import json, os, re, hashlib, shutil, datetime, sys
from pathlib import Path

WS = Path('/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları')
SUBJ = ['fen','matematik','turkce','din-kulturu','ingilizce','inkilap-tarihi']

def safe_int(v, d=0):
    try: return int(v) if v is not None else d
    except Exception: return d

def sha256_file(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest()

def normalize_question(q, subject):
    f = os.path.basename(str(q.get('file','')))
    page = safe_int(q.get('page'))
    qnum = safe_int(q.get('q') or q.get('questionNumber'))
    unit = q.get('unit')
    unit = safe_int(unit) if unit is not None else None
    unitName = q.get('unitName') or None
    # tu2 için unitName yoksa topic'i kullan
    if unitName is None and q.get('topic'):
        unitName = q['topic']
    m = re.match(r'^((?:cal|nuli|mu|tu)\d+)', f)
    sourceBook = m.group(1).upper() if m else 'UNKNOWN'
    section = q.get('section')
    if section not in ('UNIT','EXAM','TOPIC'):
        section = 'TOPIC' if (subject in ('turkce','matematik') and unit is None) else 'UNIT'
    examYear = q.get('examYear') or None
    answer = q.get('answer') or None
    answerSource = 'OFFICIAL_KEY'
    status = q.get('status') or 'NEEDS_REVIEW'
    published = q.get('published')
    published = True if published is None else bool(published)
    cancelledInSource = bool(q.get('cancelledInSource', False))
    sha256 = q.get('sha256')
    if not sha256:
        try: sha256 = sha256_file(WS/subject/f)
        except Exception: sha256 = None
    clipRectPt = q.get('clipRectPt') or None
    out = {
        'id': f"{subject.upper()}-{f[:-4].upper() if f.lower().endswith('.png') else f.upper()}",
        'file': f, 'page': page, 'q': qnum,
        'unit': unit, 'unitName': unitName,
        'sourceBook': sourceBook, 'section': section, 'examYear': examYear,
        'answer': answer, 'answerSource': answerSource,
        'status': status, 'published': published, 'cancelledInSource': cancelledInSource,
        'sha256': sha256, 'clipRectPt': clipRectPt,
    }
    # opsiyonel ek alanlar (tu2 konu yapısı)
    for k in ('topic','topic_slug','test_num','column'):
        if q.get(k) is not None:
            out[k] = q[k]
    return out

def merge_manifests(subject):
    d = WS/subject
    manifest_files = sorted(d.glob('manifest*.json'))
    if not manifest_files:
        return None, 0, 'no-manifest'
    # idempotence: tek manifest.json varsa ve zaten birleşik ürünse atla
    if len(manifest_files) == 1 and manifest_files[0].name == 'manifest.json':
        try:
            root = json.loads(manifest_files[0].read_text(encoding='utf-8'))
            if root.get('book') == subject.upper() + '_merged':
                return manifest_files[0], len(root.get('questions',[])), 'already-merged'
        except Exception:
            pass
    all_q = []
    for mp in manifest_files:
        data = json.loads(mp.read_text(encoding='utf-8'))
        qs = data.get('questions', []) if isinstance(data, dict) else data
        all_q.extend(qs)
    # tekilleştir: aynı file alanını birden çok manifest taşımışsa bir kez al
    seen, uniq = set(), []
    for q in all_q:
        key = os.path.basename(str(q.get('file','')))
        if key in seen: continue
        seen.add(key)
        uniq.append(q)
    uniq.sort(key=lambda q: (safe_int(q.get('page')), safe_int(q.get('q') or q.get('questionNumber'))))
    questions = [normalize_question(q, subject) for q in uniq]
    unified = {
        'book': subject.upper() + '_merged',
        'subject': subject,
        'total_questions': len(questions),
        'answerMappingStatus': f"{sum(1 for q in questions if q['answer'])}/{len(questions)}",
        'questions': questions,
    }
    out = d/'manifest.json'
    out.write_text(json.dumps(unified, ensure_ascii=False, indent=2), encoding='utf-8')
    return out, len(questions), 'merged'

def build_answers_json(subject):
    """answers.json = { dosya adı: harf } — manifest'ten türetilir (standart)."""
    d = WS/subject
    mp = d/'manifest.json'
    if not mp.exists(): return None, 0
    qs = json.loads(mp.read_text(encoding='utf-8'))['questions']
    answers = { q['file']: q['answer'] for q in qs if q.get('answer') }
    out = d/'answers.json'
    out.write_text(json.dumps(answers, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    return out, len(answers)

def merge_analysis(subject):
    d = WS/subject
    files = sorted(d.glob('analysis*.jsonl'))
    if not files: return None, 0
    if len(files) == 1 and files[0].name == 'analysis.jsonl':
        return files[0], sum(1 for l in files[0].read_text(encoding='utf-8').splitlines() if l.strip()), 'single'
    best = {}
    prio = {'PDF_TEXT': 0, 'gemma3:4b': 1, 'minicpm-v': 2, 'llama-3.2-11b': 3}
    for af in files:
        for line in af.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line: continue
            try: rec = json.loads(line)
            except Exception: continue
            rec['file'] = os.path.basename(str(rec.get('file','')))
            if not rec['file']: continue
            src = str(rec.get('analysisSource',''))
            rank = next((v for k,v in prio.items() if k in src), 9)
            key = (rank, str(rec.get('analyzedAt','')))
            cur = best.get(rec['file'])
            if cur is None or key < cur[0]:
                best[rec[ 'file']] = (key, rec)
    recs = [r for _, r in best.values()]
    recs.sort(key=lambda r: (safe_int(r.get('page')), safe_int(r.get('q')), r.get('file','')))
    out = d/'analysis.jsonl'
    with open(out,'w',encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False)+'\n')
    return out, len(recs), 'merged'

def backup_originals(subject):
    d = WS/subject
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bdir = WS/f'_standart_yedek_{subject}_{ts}'
    bdir.mkdir(parents=True, exist_ok=True)
    for pat in ('manifest*.json','*answers*.json','analysis*.jsonl'):
        for p in d.glob(pat):
            shutil.copy2(p, bdir/p.name)
    return bdir

def main():
    only = sys.argv[1:] or SUBJ
    for s in only:
        print(f'=== {s} ===')
        bdir = backup_originals(s)
        print(f'  yedek: {bdir.name}')
        mp, nq, how = merge_manifests(s)
        print(f'  manifest.json: {nq} soru ({how})')
        ap, na = build_answers_json(s)
        print(f'  answers.json: {na} kayıt (dosya adı → harf)')
        al, nr, how2 = merge_analysis(s)
        print(f'  analysis.jsonl: {nr} kayıt ({how2})')
        # eski bölünmüş dosyaları temizle (manifest.json ve analysis.jsonl KORUNUR)
        d = WS/s
        removed = []
        for p in sorted(d.iterdir()):
            if p.name in ('manifest.json','answers.json','analysis.jsonl'): continue
            if re.match(r'^manifest.*\.json$', p.name) or re.match(r'^.*answers.*\.json$', p.name) or re.match(r'^analysis.*\.jsonl$', p.name):
                p.unlink(); removed.append(p.name)
        if removed: print(f'  silinen: {", ".join(removed)}')
        print(f'  {s} tamam')

if __name__ == '__main__':
    main()
