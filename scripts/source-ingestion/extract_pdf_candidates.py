#!/usr/bin/env python3
"""Extract conservative text candidates from a PDF; output is never VERIFIED."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from create_ingestion_manifest import validate_provenance

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

QUESTION_START = re.compile(r"^\s{0,4}(\d{1,2})\.\s+(\S.*)$")
OPTION_MARK = re.compile(r"(?<![A-Za-z0-9ÇĞİÖŞÜçğıöşü])([A-D])\s*\)\s*")
OPTION_LETTERS = "ABCD"
ANSWER_PAIR = re.compile(r"(?<!\w)(\d{1,2})\s*[).:-]\s*([A-D])(?=\s|[,;|]|$)", re.I)

# LGS kitapçıklarında ders başlıkları soru numaralarından önce gelir; numaralandırma
# ders başında 1'den yeniden başlar.
SUBJECT_HEADERS = {
    "MATEMATİK": "MATEMATİK",
    "FEN BİLİMLERİ": "FEN BİLİMLERİ",
    "TÜRKÇE": "TÜRKÇE",
    "SOSYAL BİLGİLER": "SOSYAL BİLGİLER",
    "DİN KÜLTÜRÜ": "DİN KÜLTÜRÜ",
}

# Çoktan seçmeli bir soruda en az bir A-D işareti bulunur; sınav talimatı, kapak
# metni ve cevap anahtarı hiçbir seçenek işareti taşımaz.
MIN_OPTION_LABELS = 1


def parse_options(text):
    """Metindeki A/B/C/D seçeneklerini sıralı bir dizi olarak ayrıştırır.

    Bu kitapçıkta seçenekler hem tek satırda (``A) 8  B) 6  C) 25  D) 10``)
    hem de alt satırlara bölünmüş hâlde bulunur. Yalnız A→B→C→D sırasına
    uyan işaretler kabul edilir; eksik ya da karışık diziler uydurulmaz.
    """
    marks = [(m.start(), m.end(), m.group(1)) for m in OPTION_MARK.finditer(text)]
    best, run, want = [], [], 0
    for start, end, letter in marks:
        if letter == OPTION_LETTERS[want]:
            run.append((start, end, letter))
            want += 1
            if want == 4:
                best = run
                run, want = [], 0
    if not best:
        return {}
    options = {}
    for index, (start, end, letter) in enumerate(best):
        stop = best[index + 1][0] if index + 1 < len(best) else len(text)
        options[letter] = re.sub(r"\s+", " ", text[end:stop]).strip()
    return options


def option_marker_count(text):
    """Blokta kaç farklı A-D işareti geçtiğini sayar (kaçıncı soruya ait olduğunu bilmeden).

    Bir blokun soru sayılabilmesi için en az bir işaret yeterlidir; sınav
    talimatı, kapak metni ve cevap anahtarı hiç işaret taşımaz. Dört seçeneğin
    tamamı ayrıştırılamıyorsa bu aday uyarıyla ``NEEDS_REVIEW`` kalır.
    """
    return len({match.group(1) for match in OPTION_MARK.finditer(text)})


def _first_option_offset(text):
    for match in OPTION_MARK.finditer(text):
        if match.group(1) == "A":
            return match.start()
    return None


def _build_block(lines, question_number):
    body = "\n".join(item[3] for item in lines)
    if option_marker_count(body) < MIN_OPTION_LABELS:
        return None
    options = parse_options(body)
    cut = _first_option_offset(body)
    stem = body[:cut] if cut is not None else body
    stem = re.sub(r"^\s*\d{1,2}\.\s+", "", stem.strip(), count=1)
    stem = re.sub(r"\s+", " ", stem)
    warnings = []
    if len(stem) < 20:
        warnings.append("short_or_incomplete_stem")
    if set(options) != set(OPTION_LETTERS):
        warnings.append("four_options_not_confidently_extracted")
    if len(body) < 45:
        warnings.append("low_text_density_or_scanned_content")
    # Seçenek metni içinde başka bir seçenek işareti varsa sınırlar kaymış demektir
    # (çok sütunlu/ tireli metin). Sessizce bozuk seçenek üretilmez.
    for letter, value in options.items():
        if OPTION_MARK.search(value):
            warnings.append("option_boundary_ambiguous")
            break
    return {
        "subject": lines[0][1],
        "question_number": question_number,
        "stem": stem,
        "options": options,
        "page_start": lines[0][0],
        "page_end": lines[-1][0],
        "extraction_warnings": warnings,
    }


def segment_lines(lines, require_subject_header=True):
    """(sayfa, ders, satır) akışından soru adaylarını çıkarır.

    Kurallar:
      * Ders başlığı görülene kadar satırlar sınav talimatı sayılır (ön kısım).
        ``require_subject_header=False`` ile bu koruma kapatılabilir.
      * Bir blok yeterli seçenek işareti taşımıyorsa soru başlangıcı değildir;
        bu, cevap anahtarı satırlarını ve soru içi alt maddeleri eler.
      * Numarası başlayan bloğun numarasından küçük satırlar alt maddedir ve
        ana sorunun gövdesine eklenir.
      * Seçenek dizisi tamamlanan soru kapanır; sonraki satırlar (sayfa altı,
        cevap anahtarı vb.) o soruya iliştirilmez.
    """
    blocks = []
    buffer = []
    current_number = None
    subject = None
    in_questions = not require_subject_header

    def flush():
        nonlocal buffer, current_number
        if not buffer:
            return
        block = _build_block(buffer, current_number)
        if block:
            blocks.append(block)
        buffer = []

    for page, header_subject, line in lines:
        stripped = line.strip()
        if stripped in SUBJECT_HEADERS:
            flush()
            subject = SUBJECT_HEADERS[stripped]
            current_number = None
            in_questions = True
            continue
        if not in_questions:
            continue
        match = QUESTION_START.match(line)
        if match:
            number = int(match.group(1))
            is_sub_item = current_number is not None and number < current_number
            if not is_sub_item:
                flush()
                current_number = number
                buffer = [(page, subject, stripped, line)]
                continue
        if not buffer:
            continue
        # Seçenekleri tamamlanmış soruya yeni satır eklenmez (kapak/cevap anahtarı
        # metni soruya bulaşmasın).
        if parse_options("\n".join(item[3] for item in buffer)).keys() >= set(OPTION_LETTERS):
            continue
        buffer.append((page, subject, current_number, line))
    flush()
    return blocks


def segment_page(text, page):
    """Tek sayfa için uyumluluk sarmalayıcı (ders başlığı olmayan metinler)."""
    return segment_lines(
        [(page, None, line) for line in (text or "").splitlines()],
        require_subject_header=False,
    )


def extract_text(pdf_path):
    if PdfReader is None:
        raise RuntimeError("pypdf is required for PDF extraction; install it in the project environment")
    reader = PdfReader(str(pdf_path), strict=False)
    pages = []
    for number, page in enumerate(reader.pages, 1):
        try:
            pages.append({"page": number, "text": page.extract_text() or ""})
        except Exception as exc:
            pages.append({"page": number, "text": "", "error": type(exc).__name__})
    return pages


ANSWER_KEY_MARKER = "CEVAP ANAHTAR"
ANSWER_LINE = re.compile(r"^\s{0,4}(\d{1,2})\s*[).:-]\s*([A-D])\s*$")


def parse_answer_key(pages):
    """Resmî cevap anahtarını ``(subject, question_number)`` ile ayrıştırır.

    MEB kitapçık düzeninde ders etiketi cevap bloğunun **altında** yer alır
    (satır etiketi). Bu nedenle her cevap bloğu kendisini izleyen ders etiketiyle
    eşleştirilir; etiket önce gelen düzenlerde önceki etiket kullanılır.

    Güvenlik kuralları:
      * Ders kanıtı yoksa hiçbir cevap eşlenmez.
      * Tanınmayan etiket, aynı numaranın iki kez geçmesi veya iki bloğun aynı
        derse düşmesi hâlinde blok reddedilir; sessiz eşleme yapılmaz.
      * Kaynak yalnızca PDF metnidir: model, soru çözümü veya OCR kullanılmaz.
    """
    by_subject = {}
    diagnostics = []
    mapped_subjects = set()
    ambiguous_subjects = set()
    for entry in pages:
        lines = entry["text"].splitlines()
        if not any(ANSWER_KEY_MARKER in line.upper() for line in lines):
            continue
        page_no = entry["page"]
        marker_line = next((line.strip() for line in lines if ANSWER_KEY_MARKER in line.upper()), "")
        blocks = []
        current = None
        pending_label = None
        for line in lines:
            pair = ANSWER_LINE.match(line)
            if pair:
                if current is None:
                    current = {"pairs": {}, "duplicates": [], "leading_label": pending_label}
                number, letter = int(pair.group(1)), pair.group(2).upper()
                if number in current["pairs"]:
                    current["duplicates"].append(number)
                current["pairs"][number] = letter
                continue
            stripped = line.strip()
            if stripped in SUBJECT_HEADERS:
                subject = SUBJECT_HEADERS[stripped]
                if current is None:
                    pending_label = subject
                else:
                    current["trailing_label"] = subject
                    blocks.append(current)
                    current = None
                    pending_label = None
                continue
            if current is not None and stripped:
                blocks.append(current)
                current = None
                pending_label = None
        if current is not None:
            blocks.append(current)

        for block in blocks:
            labels = {label for label in (block.get("leading_label"), block.get("trailing_label")) if label}
            if not block["pairs"]:
                diagnostics.append(f"page {page_no}: answer block without any pair was ignored")
                continue
            if not labels:
                diagnostics.append(
                    f"page {page_no}: {len(block['pairs'])} answer pairs have no subject evidence; not mapped"
                )
                continue
            if len(labels) > 1:
                diagnostics.append(
                    f"page {page_no}: block carries conflicting subject labels {sorted(labels)}; rejected"
                )
                continue
            if block["duplicates"]:
                diagnostics.append(
                    f"page {page_no}: duplicate answer pairs {sorted(set(block['duplicates']))}; block rejected"
                )
                continue
            subject = labels.pop()
            # Aynı ders için ikinci bir blok gelirse hangisinin doğru olduğu
            # kanıtlanamaz; dersin tüm eşleşmeleri düşürülür.
            if subject in mapped_subjects:
                diagnostics.append(
                    f"page {page_no}: {subject} appears in more than one answer block; all of its pairs rejected"
                )
                ambiguous_subjects.add(subject)
                continue
            mapped_subjects.add(subject)
            by_subject.setdefault(subject, {})
            for number, letter in block["pairs"].items():
                by_subject[subject][number] = {
                    "letter": letter,
                    "page": page_no,
                    "evidence": f"{marker_line} (page {page_no}, subject {subject})",
                }
    for subject in ambiguous_subjects:
        by_subject.pop(subject, None)
    return {"by_subject": by_subject, "diagnostics": diagnostics}


def extract(pdf_path, source, source_file_url, booklet, manifest=None):
    pages = extract_text(pdf_path)
    # Ders başlıkları sayfa akışında takip edilir; numaralandırma ders başında
    # yeniden başladığı için konu bilgisi kayıt kimliğine de yansıtılır.
    stream = []
    subject = None
    for page in pages:
        for line in page["text"].splitlines():
            stripped = line.strip()
            if stripped in SUBJECT_HEADERS:
                subject = SUBJECT_HEADERS[stripped]
            stream.append((page["page"], subject, line))
    blocks = segment_lines(stream)
    all_text = "\n".join(page["text"] for page in pages)
    answer_pairs = [{"question_number": int(number), "candidate": letter.upper()} for number, letter in ANSWER_PAIR.findall(all_text)]
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    provenance = manifest or {}
    # Cevap anahtarı yalnızca resmî sayfadaki kanıtla ve (subject, question_number)
    # anahtarıyla eşleşir; konusuz eşleme yapılmaz.
    answer_key = parse_answer_key(pages)
    subject_answers = answer_key["by_subject"]
    records = []
    for block in blocks:
        subject_label = (block["subject"] or "BILINMIYEN").split()[0]
        record_id = f"{source['id']}:{booklet}:{subject_label}:Q{block['question_number']:02d}"
        subject_answers_for_block = subject_answers.get(block["subject"], {})
        mapped = subject_answers_for_block.get(block["question_number"]) if block["subject"] else None
        answer_map = None
        if mapped:
            answer_map = {
                "source_id": source["id"],
                "booklet": booklet,
                "subject": block["subject"],
                "question_number": block["question_number"],
                "letter": mapped["letter"],
                "page": mapped["page"],
                "evidence": mapped["evidence"],
                "source_sha256": pdf_hash,
            }
        records.append({
            "schema_version": "1.0", "id": record_id,
            "source": {"source_id": source["id"], "source_type": source["type"], "year": source.get("year"), "official_index_url": source["official_index_url"], "source_page_url": provenance.get("source_page_url"), "discovered_from": provenance.get("discovered_from"), "pdf_url": provenance.get("pdf_url", source_file_url), "final_url": provenance.get("final_url", source_file_url), "source_file_url": source_file_url, "redirect_chain": provenance.get("redirect_chain", [source_file_url]), "source_sha256": pdf_hash, "booklet": booklet, "question_number": block["question_number"]},
            "question": {"grade": 8, "subject": block["subject"], "stem": block["stem"], "options": block["options"], "page_start": block["page_start"], "page_end": block["page_end"]},
            "answer_key": {"candidate": answer_map["letter"] if answer_map else None, "answer": None, "authority": "OFFICIAL_MEB_ONLY", "source_verified": False, "answer_key_verified": False},
            "curriculum": {"LGS_REFERENCE_2018_PLUS": {"status": "UNMAPPED", "version": None, "subject": None, "unit": None, "topic": None, "learning_outcome": None, "skill": None, "evidence_url": None}, "CURRENT_TYMM": {"status": "UNMAPPED", "version": None, "subject": None, "unit": None, "topic": None, "learning_outcome": None, "skill": None, "evidence_url": None}},
            "extraction": {"method": "pypdf-text-v1", "retrieved_at": datetime.now(timezone.utc).isoformat(), "confidence": "LOW" if block["extraction_warnings"] else "UNREVIEWED", "warnings": block["extraction_warnings"], "answer_key_candidates": [{"question_number": number, "candidate": row["letter"], "subject": block["subject"], "page": row["page"]} for number, row in sorted(subject_answers_for_block.items())], "answer_key_map": answer_map},
            "solution": None,
            "status": "NEEDS_REVIEW", "checks": {"source_verified": False, "year_verified": False, "booklet_verified": False, "question_number_verified": False, "text_verified": False, "options_verified": False, "answer_key_source_verified": False, "answer_key_verified": False, "curriculum_verified": False, "solution_verified": False, "duplicate_checked": False},
        })
    review_reasons = []
    if not any(page["text"].strip() for page in pages):
        review_reasons.append("no_extractable_text_or_scanned_pdf")
    if any(page.get("error") for page in pages):
        review_reasons.append("page_text_extraction_error")
    if not records:
        review_reasons.append("no_question_candidates_detected")
    if records and any(record["extraction"]["warnings"] for record in records):
        review_reasons.append("question_or_option_extraction_ambiguous")
    if not answer_pairs:
        review_reasons.append("no_answer_key_candidate_detected")
    unmapped = sum(1 for r in records if not r["extraction"]["answer_key_map"])
    conflicts = 0
    for subject in subject_answers:
        for record in (r for r in records if r["question"]["subject"] == subject):
            if record["answer_key"]["candidate"] is None:
                conflicts += 1
    answer_key_summary = {
        "counts": {subject: len(numbers) for subject, numbers in sorted(subject_answers.items())},
        "mapped_candidates": sum(1 for r in records if r["extraction"]["answer_key_map"]),
        "unmapped_candidates": unmapped,
        "subject_conflicts": conflicts,
        "diagnostics": answer_key["diagnostics"],
    }
    if unmapped:
        review_reasons.append("answer_key_mapping_incomplete")
    if answer_key["diagnostics"]:
        review_reasons.append("answer_key_evidence_ambiguous")
    return {
        "schema_version": "1.0", "source_id": source["id"], "source_sha256": pdf_hash,
        "pages": [{"page": row["page"], "text_characters": len(row["text"]), "extraction_error": row.get("error")} for row in pages],
        "candidate_count": len(records), "answer_key_candidate_count": len(answer_pairs), "records": records,
        "answer_key_summary": answer_key_summary,
        "review_reasons": review_reasons, "status": "NEEDS_REVIEW", "published": False,
    }


def validate_manifest_for_pdf(manifest, source, pdf_path):
    source_file_url = manifest.get("source_file_url", "")
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if manifest.get("source_id") != source["id"] or manifest.get("sha256") != pdf_hash or manifest.get("status") != "NEEDS_REVIEW" or manifest.get("published") is not False:
        raise ValueError("manifest source id/hash/status does not match the archived PDF")
    if manifest.get("official_index_url") != source["official_index_url"]:
        raise ValueError("manifest index URL does not match the registered source")
    try:
        validate_provenance(source, manifest)
    except ValueError as exc:
        raise ValueError(f"manifest provenance is invalid: {exc}") from exc
    if manifest.get("source_file_url") != manifest.get("pdf_url"):
        raise ValueError("manifest source PDF URL does not match discovery record")
    if manifest.get("size_bytes") != pdf_path.stat().st_size:
        raise ValueError("manifest size does not match archived PDF")
    if manifest.get("content_type") != "application/pdf":
        raise ValueError("manifest Content-Type is not application/pdf")
    return source_file_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--booklet", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    from download_official_pdfs import registered_source
    from validate_source_registry import official_host
    source = registered_source(args.source_id)
    if source.get("type") == "REAL_LGS" and (not isinstance(source.get("year"), int) or source["year"] < 2018):
        parser.error("pre-2018 REAL_LGS sources cannot enter canonical LGS staging")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        source_file_url = validate_manifest_for_pdf(manifest, source, args.pdf)
        result = extract(args.pdf, source, source_file_url, args.booklet, manifest)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"candidates={result['candidate_count']} answer_key_candidates={result['answer_key_candidate_count']} review_reasons={','.join(result['review_reasons']) or 'none'} status=NEEDS_REVIEW published=false")

if __name__ == "__main__":
    main()
