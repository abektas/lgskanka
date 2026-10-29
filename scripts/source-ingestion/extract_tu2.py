#!/usr/bin/env python3
"""TU2-2 PDF extractor — 8. Sınıf Türkçe Çalışma Kitabı (MEB 2023).

Uses the proven crop_page logic from extract_study_workbook.py
adapted for the TU2 format (topics -> TESTs, two-column layout).
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

# Import base functions from extract_study_workbook
sys.path.insert(0, str(Path(__file__).parent))
from extract_study_workbook import (
    drop_page_numbers, page_rects, significant_shapes, anchors,
    crop_column, sha256, DPI, MARGIN_PT, FOOTER_PT, LEFT_KEEP_PT, RIGHT_KEEP_PT
)

# For TU2, we need a permissive filter that allows test restarts
def filter_sequential_tu2(anch):
    """Permissive filter for TU2: allows test restarts (1 after high numbers).
    Only drops clear figure labels: numbers that are very small AND far from previous.
    """
    out = []
    last = 0
    for a in anch:
        # Allow restart if number is 1-5 and last was much higher (test restart)
        if last >= 10 and a["num"] <= 5:
            out.append(a)
            last = max(last, a["num"])
            continue
        # Standard filter: drop if much smaller than running max
        if last >= 3 and a["num"] * 2 < last:
            continue
        out.append(a)
        last = max(last, a["num"])
    return out

def crop_page_tu2(page, page_index, outdir, book):
    """Crop every question on one page with TU2-permissive filter."""
    W, H = page.get_size()
    rects = drop_page_numbers(page_rects(page), W, H)
    shapes = significant_shapes(page, W, H)
    left = filter_sequential_tu2(anchors(rects, W, H, "left"))
    right = filter_sequential_tu2(anchors(rects, W, H, "right"))
    # A right column is real only if its numbers CONTINUE the left column.
    if left and right:
        right = [a for a in right if a["num"] > left[-1]["num"]]
    if not left and not right:
        return []
    img = page.render(scale=DPI / 72).to_pil().convert("RGB")
    sx, sy = img.width / W, img.height / H
    if right and left:
        recs = crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                           left, "left", LEFT_KEEP_PT, W / 2, book)
        recs += crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                            right, "right", W / 2, W - RIGHT_KEEP_PT, book)
        return recs
    return crop_column(rects, shapes, img, W, H, sx, sy, page_index, outdir,
                       left or right, "single", LEFT_KEEP_PT, W - RIGHT_KEEP_PT, book)

SRC_PDF = Path("/home/selam/.hermes/attachments/tu2-2.pdf")
DST_ROOT = Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce")
OUT_PNG_DIR = DST_ROOT

# Topic structure from TOC (page 6) — 1-based page numbers
TOPICS = [
    {"name": "SÖZCÜKTE ANLAM", "start": 8, "end": 19},
    {"name": "SÖZ GRUPLARINDA ANLAM (Kalıplaşmamış Söz Grupları)", "start": 20, "end": 26},
    {"name": "DEYIM VE ATASÖZÜ", "start": 27, "end": 34},
    {"name": "SÖZ SANATLARI", "start": 35, "end": 44},
    {"name": "CÜMLEDE ANLAM", "start": 45, "end": 58},
    {"name": "PARÇADA ANLAM (Ana Düşünce - Ana Duygu - Yardımcı Düşünce - Konu - Başlık)", "start": 59, "end": 98},
    {"name": "PARÇADA ANLAM (Hikâye Unsurları - Metnin Dil ve Anlatım Özellikleri)", "start": 99, "end": 108},
    {"name": "PARÇADA ANLAM (Parça Oluşturma - Parça Tamamlama)", "start": 109, "end": 114},
    {"name": "PARÇADA ANLAM (Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları)", "start": 115, "end": 122},
    {"name": "SÖZEL MANTIK / MUHAKEME", "start": 123, "end": 128},
    {"name": "GÖRSEL OKUMA (Tablo / Grafik / Çizelge)", "start": 129, "end": 150},
    {"name": "FIILIMSILER", "start": 151, "end": 160},
    {"name": "CÜMLENİN ÖGELERİ", "start": 161, "end": 176},
    {"name": "YAZIM KURALLARI", "start": 170, "end": 176},
    {"name": "NOKTALAMA İŞARETLERİ", "start": 178, "end": 185},
]

TOPIC_KEY_MAP = {
    "SÖZCÜKTE ANLAM": "sozcukte-anlam",
    "SÖZ GRUPLARINDA ANLAM (Kalıplaşmamış Söz Grupları)": "soz-gruplarinda-anlam",
    "DEYIM VE ATASÖZÜ": "deyim-ve-atasozu",
    "SÖZ SANATLARI": "soz-sanatlari",
    "CÜMLEDE ANLAM": "cumlede-anlam",
    "PARÇADA ANLAM (Ana Düşünce - Ana Duygu - Yardımcı Düşünce - Konu - Başlık)": "parcada-anlam-1",
    "PARÇADA ANLAM (Hikâye Unsurları - Metnin Dil ve Anlatım Özellikleri)": "parcada-anlam-2",
    "PARÇADA ANLAM (Parça Oluşturma - Parça Tamamlama)": "parcada-anlam-3",
    "PARÇADA ANLAM (Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları)": "parcada-anlam-4",
    "SÖZEL MANTIK / MUHAKEME": "sozel-mantik-muhakeme",
    "GÖRSEL OKUMA (Tablo / Grafik / Çizelge)": "gorsel-okuma",
    "FIILIMSILER": "filimseler",
    "CÜMLENİN ÖGELERİ": "cumlenin-ogeleri",
    "YAZIM KURALLARI": "yazim-kurallari",
    "NOKTALAMA İŞARETLERİ": "noktalama-isaretleri",
}

# Answer key pages (1-based): 192-196
ANSWER_KEY_PAGES = list(range(192, 197))

PAIR_RE = re.compile(r"(\d{1,3})\.\s*([A-D])")

def parse_answer_keys(doc: pdfium.PdfDocument) -> dict:
    """Parse answer keys from pages 192-196."""
    answers = {}  # (topic, test, qnum) -> answer
    current_topic = None
    current_test = None
    
    # PARÇADA ANLAM variants in order of appearance
    PARÇADA_VARIANTS = [
        "PARÇADA ANLAM (Ana Düşünce - Ana Duygu - Yardımcı Düşünce - Konu - Başlık)",
        "PARÇADA ANLAM (Hikâye Unsurları - Metnin Dil ve Anlatım Özellikleri)",
        "PARÇADA ANLAM (Parça Oluşturma - Parça Tamamlama)",
        "PARÇADA ANLAM (Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları)",
    ]
    parça_variant_idx = 0
    
    # Build topic name mapping (normalize Turkish chars for matching)
    def norm(s: str) -> str:
        return s.upper().replace('İ', 'I').replace('Ş', 'S').replace('Ğ', 'G').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C')
    
    # Exact mappings for answer key topic names that differ from TOPICS
    EXACT_TOPIC_MAP = {
        "GÖRSEL OKUMA (TABLO / GRAFIK / ÇIZELGE)": "GÖRSEL OKUMA (Tablo / Grafik / Çizelge)",
    }
    
    topic_norm_to_actual = {}
    for t in TOPICS:
        topic_norm_to_actual[norm(t["name"])] = t["name"]
    
    for page_idx in [p - 1 for p in ANSWER_KEY_PAGES]:  # 0-indexed
        page = doc[page_idx]
        tp = page.get_textpage()
        txt = tp.get_text_bounded(0, 0, page.get_size()[0], page.get_size()[1])
        lines = [l.strip() for l in txt.split('\n') if l.strip() and not l.strip().startswith("CEVAP ANAHTARI") and not l.strip().isdigit()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_norm = norm(line)
            
            # Check for topic header
            matched_topic = None
            
            # First try exact mappings
            for exact_key, actual_name in EXACT_TOPIC_MAP.items():
                if exact_key in line_norm:
                    matched_topic = actual_name
                    break
            
            # Check for PARÇADA ANLAM - need to also check next line for subtitle
            if not matched_topic and "PARCADA ANLAM" in line_norm:
                # Look at next line for subtitle
                subtitle = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_norm = norm(next_line)
                    # Check which variant this subtitle matches
                    if "ANA DÜŞÜNCE" in next_norm:
                        matched_topic = PARÇADA_VARIANTS[0]
                    elif "HIKÂYE UNSURLARI" in next_norm or "HIKAYE UNSURLARI" in next_norm:
                        matched_topic = PARÇADA_VARIANTS[1]
                    elif "PARCA OLUSTURMA" in next_norm or "PARÇA OLUŞTURMA" in next_norm:
                        matched_topic = PARÇADA_VARIANTS[2]
                    elif "ANLATIM BIÇIMLERI" in next_norm or "ANLATIM BICIMLERI" in next_norm:
                        matched_topic = PARÇADA_VARIANTS[3]
                    else:
                        # Fallback to sequence
                        if parça_variant_idx < len(PARÇADA_VARIANTS):
                            matched_topic = PARÇADA_VARIANTS[parça_variant_idx]
                else:
                    if parça_variant_idx < len(PARÇADA_VARIANTS):
                        matched_topic = PARÇADA_VARIANTS[parça_variant_idx]
                
                if matched_topic:
                    parça_variant_idx += 1
            
            # Check for GÖRSEL OKUMA
            if not matched_topic and "GORSEL OKUMA" in line_norm:
                matched_topic = "GÖRSEL OKUMA (Tablo / Grafik / Çizelge)"
            
            # Then try exact mappings
            if not matched_topic:
                for exact_key, actual_name in EXACT_TOPIC_MAP.items():
                    if exact_key in line_norm:
                        matched_topic = actual_name
                        break
            
            # Then try normalized TOPICS
            if not matched_topic:
                for t in TOPICS:
                    if norm(t["name"]) in line_norm:
                        matched_topic = t["name"]
                        break
            
            if matched_topic:
                current_topic = matched_topic
                current_test = None
                i += 1
                continue
            
            # Check for TEST-N header
            m = re.match(r"TEST-(\d+)", line, re.IGNORECASE)
            if m:
                current_test = int(m.group(1))
                i += 1
                continue
            
            # Parse answer pairs
            if current_topic and current_test is not None:
                for q_str, ans in PAIR_RE.findall(line):
                    q_num = int(q_str)
                    key = (current_topic, current_test, q_num)
                    answers[key] = ans
            
            i += 1
    
    return answers

def topic_to_slug(name: str) -> str:
    return TOPIC_KEY_MAP.get(name, name.lower().replace(" ", "-").replace("(", "").replace(")", "").replace(",", ""))

def main():
    OUT_PNG_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Opening {SRC_PDF}")
    doc = pdfium.PdfDocument(SRC_PDF)
    print(f"Total pages: {len(doc)}")
    
    # Compute PDF SHA256
    pdf_sha = sha256(SRC_PDF)
    print(f"PDF SHA256: {pdf_sha}")
    
    # Parse answer keys
    print("Parsing answer keys from pages 192-196...")
    answers = parse_answer_keys(doc)
    print(f"Found {len(answers)} answer entries")
    
    # Build question list from answer keys (they define the complete question set)
    questions = []
    q_counter = 0
    for (topic_name, test_num, q_num), ans in sorted(answers.items()):
        q_counter += 1
        topic_slug = topic_to_slug(topic_name)
        q_id = f"TU2-TURKCE-Q{q_counter:04d}"
        
        questions.append({
            "id": q_id,
            "topic": topic_name,
            "topic_slug": topic_slug,
            "test_num": test_num,
            "question_num": q_num,
            "global_num": q_counter,
            "answer": ans,
            "status": "NEEDS_REVIEW",
            "published": False
        })
    
    print(f"Total questions from answer keys: {q_counter}")
    
    # Now we need to map each question to its PDF page
    # Strategy: For each topic, scan its page range and use crop_page
    # to extract all questions, then match them to answer key entries
    
    all_crops = []
    all_questions = []
    
    for topic in TOPICS:
        topic_name = topic["name"]
        topic_slug = topic_to_slug(topic_name)
        start_idx = topic["start"] - 1  # 0-indexed
        end_idx = topic["end"] - 1
        
        print(f"\nProcessing {topic_name} (pages {topic['start']}-{topic['end']})...")
        
        # Crop all questions in this topic's page range
        topic_crops = []
        for page_idx in range(start_idx, end_idx + 1):
            page = doc[page_idx]
            # Skip empty pages (cover, TOC, etc.)
            tp = page.get_textpage()
            txt = tp.get_text_bounded(0, 0, page.get_size()[0], page.get_size()[1])
            if len(txt.strip()) < 50:
                continue
            
            recs = crop_page_tu2(page, page_idx + 1, OUT_PNG_DIR, f"tu2_{topic_slug}")
            if recs:
                for r in recs:
                    r["topic"] = topic_name
                    r["topic_slug"] = topic_slug
                    r["page_idx"] = page_idx + 1
                topic_crops.extend(recs)
        
        print(f"  Found {len(topic_crops)} question crops")
        all_crops.extend(topic_crops)
    
    print(f"\nTotal crops: {len(all_crops)}")
    
    # Now match crops to answer key entries
    # The answer keys give us the expected count per (topic, test)
    # We need to assign test numbers to the crops
    # Strategy: within each topic, questions are numbered 1..N per test
    # crop_page returns sequential question numbers per column
    
    # Group crops by topic
    crops_by_topic = {}
    for c in all_crops:
        crops_by_topic.setdefault(c["topic"], []).append(c)
    
    # For each topic, match crops to answer key entries
    matched = []
    for topic_name, crops in crops_by_topic.items():
        topic_slug = topic_to_slug(topic_name)
        # Sort crops by page, then column, then vertical position
        crops.sort(key=lambda c: (c["page"], c["column"], c["clipRectPt"][1]))
        
        # Get answer key test counts for this topic
        from collections import Counter
        test_counts = Counter(test for (t, test, q) in answers.keys() if t == topic_name)
        expected_total = sum(test_counts.values())
        if not test_counts:
            print(f"  No answer keys for {topic_name}, skipping")
            continue
        
        # Answer key drives everything: for each (topic, test), take exactly N crops in reading order
        # This avoids relying on per-page question numbers which can be wrong
        # Build a flat list of (topic, test, q_num) in expected order
        expected_questions = []
        for test_num in sorted(test_counts.keys()):
            for q_num in range(1, test_counts[test_num] + 1):
                expected_questions.append((test_num, q_num))
        
        # Take exactly that many crops in reading order
        matched_for_topic = 0
        for i, (test_num, q_num) in enumerate(expected_questions):
            if i >= len(crops):
                print(f"  WARNING: Ran out of crops for {topic_name} (need {len(expected_questions)}, have {len(crops)})")
                break
            c = crops[i]
            
            key = (topic_name, test_num, q_num)
            ans = answers.get(key, None)
            
            q_counter = len(matched) + 1
            q_id = f"TU2-TURKCE-Q{q_counter:04d}"
            
            matched.append({
                "id": q_id,
                "file": c["file"],
                "page": c["page"],
                "q": q_num,
                "test_num": test_num,
                "topic": topic_name,
                "topic_slug": topic_slug,
                "column": c["column"],
                "clipRectPt": c["clipRectPt"],
                "answer": ans,
                "status": "NEEDS_REVIEW",
                "published": False
            })
            matched_for_topic += 1
        
        print(f"  Matched {matched_for_topic}/{expected_total} questions for {topic_name} (tests 1-{max(test_counts.keys()) if test_counts else 0})")
        if matched_for_topic < len(crops):
            print(f"  WARNING: {len(crops) - matched_for_topic} extra crops not matched for {topic_name}")
    
    print(f"\nTotal matched questions: {len(matched)}")
    
    # Save manifest
    manifest = {
        "manifestVersion": "1.0",
        "status": "NEEDS_REVIEW",
        "published": False,
        "source": {
            "sourceId": "TU2-TURKCE",
            "sourceType": "WORKBOOK",
            "fileName": "tu2-2.pdf",
            "sha256": pdf_sha,
            "subject": "Türkçe",
            "grade": 8,
            "topicCount": len(TOPICS),
        },
        "render": {
            "dpi": DPI,
            "margin_pt_all_sides": MARGIN_PT,
            "footer_exclusion_pt": FOOTER_PT,
            "content_aware_bbox_margin_pt": 20.0,
            "reconstructed_from_ocr": False
        },
        "questions": matched
    }
    
    man_file = DST_ROOT / "manifest_tu2.json"
    man_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Manifest saved: {man_file}")
    
    # Save answer keys separately
    ans_file = DST_ROOT / "answer_keys_tu2.json"
    ans_file.write_text(json.dumps({f"{t}|{test}|{q}": a for (t, test, q), a in answers.items()}, ensure_ascii=False, indent=2))
    print(f"Answer keys saved: {ans_file}")
    
    print("\nExtraction complete!")

if __name__ == "__main__":
    main()