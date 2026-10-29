#!/usr/bin/env python3
"""Cross-check cal01 fen answers: manifest vs raw PDF key pages."""
import sys, json, re
from pathlib import Path
sys.path.insert(0, "/home/selam/roller/web/lgs-ai-coach/scripts/source-ingestion")
import pypdfium2 as pdfium

SRC = Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal01.pdf")
MAN = Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/fen/manifest.json")
d = json.load(open(MAN))
doc = pdfium.PdfDocument(str(SRC))

# --- unit key from raw text ---
uk = {}
unit = None
for kp in (306, 307, 308):
    for line in doc[kp-1].get_textpage().get_text_range().split("\n"):
        line = line.strip()
        m = re.match(r"^(\d)\.\s*Ünite$", line)
        if m:
            unit = int(m.group(1)); uk.setdefault(unit, {}); continue
        if unit:
            for n, l in re.findall(r"(\d{1,3})\.\s*([A-D])", line):
                uk[unit][int(n)] = l

# --- exam keys from raw text ---
ek = {}
for yi, (yr, kp) in enumerate([("2018-2019",320),("2019-2020",334),("2020-2021",344),
                               ("2021-2022",356),("2022-2023",369),("2023-2024",385),
                               ("2024-2025",402)]):
    t = doc[kp-1].get_textpage().get_text_range()
    ek[yr] = {int(n): l for n, l in re.findall(r"(\d{1,2})\.\s*([A-D])", t)}

# --- compare ---
mismatch = []
checked = 0
for q in d["questions"]:
    exp = None
    if q["section"] == "UNIT":
        exp = uk.get(q["unit"], {}).get(q["q"])
    else:
        exp = ek.get(q["examYear"], {}).get(q["q"])
    if exp is None and q["answer"] is None:
        continue
    checked += 1
    if exp != q["answer"]:
        mismatch.append((q["file"], q["section"], q["unit"] or q["examYear"], q["q"],
                         "manifest=" + str(q["answer"]), "raw=" + str(exp)))

print(f"kontrol edilen: {checked}")
print(f"uyumsuzluk: {len(mismatch)}")
for m in mismatch[:30]:
    print("  ", m)

# spot-check first 5 of each
print("\n--- ÖRNEK DOĞRULAMA ---")
for sec, key in [("UNIT",1),("UNIT",2),("EXAM","2018-2019")]:
    qs = [q for q in d["questions"] if q["section"]==sec and (q["unit"]==key if sec=="UNIT" else q["examYear"]==key)][:5]
    for q in qs:
        exp = (uk if sec=="UNIT" else ek)[key][q["q"]]
        print(f'  {q["file"]:22} q{q["q"]:3} manifest={q["answer"]} raw={exp} {"OK" if q["answer"]==exp else "MISMATCH"}')
