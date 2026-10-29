import json, re, importlib.util
from pathlib import Path
import pypdfium2 as pdfium
spec=importlib.util.spec_from_file_location("ex","scripts/source-ingestion/extract_study_workbook.py")
ex=importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
PDF=Path("/home/selam/roller/web/kaynak dosyalar/lgs_çalışma_soruları/cal14.pdf")
OUT=Path("/home/selam/roller/web/lgs-ai-coach/lgs_çalışma_soruları/turkce_cal14")
OUT.mkdir(parents=True,exist_ok=True)

topics_raw=[
("SÖZCÜKTE ANLAM",7),("SÖZ GRUPLARINDA ANLAM (Kalıplaşmamış Söz Grupları)",21),
("DEYİM VE ATASÖZÜ",27),("SÖZ SANATLARI",35),("CÜMLEDE ANLAM",45),
("PARÇADA ANLAM (Ana Düşünce - Ana Duygu - Yardımcı Düşünce - Konu - Başlık)",59),
("PARÇADA ANLAM (Hikâye Unsurları - Metnin Dil ve Anlatım Özellikleri)",99),
("PARÇADA ANLAM (Parça Oluşturma - Parça Tamamlama)",109),
("PARÇADA ANLAM (Anlatım Biçimleri ve Düşünceyi Geliştirme Yolları)",115),
("SÖZEL MANTIK / MUHAKEME",123),("GÖRSEL OKUMA (Tablo / Grafik / Çizelge)",129),
("FIILIMSILER",151),("CÜMLENİN ÖGELERİ",161),("YAZIM KURALLARI",169),
("NOKTALAMA İŞARETLERİ",177),("METİN TÜRLERİ",187)]
topic_pages=[]
for idx,(name,s) in enumerate(topics_raw,1):
    end=topics_raw[idx][1]-1 if idx<len(topics_raw) else 191
    topic_pages.append({"idx":idx,"name":name,"start":s,"end":end})

doc=pdfium.PdfDocument(str(PDF))
total=0; recs_all=[]
for tp in topic_pages:
    cur_test=None
    for pno in range(tp["start"],tp["end"]+1):
        page=doc[pno-1]
        txt=page.get_textpage().get_text_range()
        for mm in re.finditer(r"TEST-(\d+)",txt):
            nt=int(mm.group(1))
            if cur_test is None or nt>=cur_test:
                cur_test=nt
        rlist=ex.crop_page(page,pno,OUT,"cal14")
        for r in rlist:
            r["unit"]=tp["idx"]; r["unitName"]=tp["name"]; r["test"]=cur_test
            r["section"]="UNIT"; r["examYear"]=None
            r["sourceBook"]="cal14"; r["page"]=pno
            r["answer"]=None; r["answerSource"]="NEEDS_REVIEW"
            recs_all.append(r); total+=1
        page.close()
doc.close()

manifest={"book":"cal14","subject":"turkce_cal14","questions":recs_all,
 "answerMappingStatus":"NEEDS_REVIEW (answer-key parser not yet implemented for cal14 dialect)"}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(OUT/"answers.json").write_text(json.dumps({},ensure_ascii=False,indent=2),encoding="utf-8")
print("topics:",len(topic_pages))
print("crops:",total)
print(" PNGs on disk:", len(list(OUT.glob('*.png'))))
