# LGS MEB SOURCE ENGINE FINAL v1.0

Bu paket, v1.0/v1.1/v1.2 ingestion çalışmalarının birleşik kaynak motorudur.

İçerir:
- resmi MEB kaynak registry
- 2018+ LGS kaynak politikası
- tarihsel LGS/current curriculum ayrımı
- canonical question ID stratejisi
- review queue standardı
- pipeline manifest
- Postgres/Supabase question bank migration
- source registry validation
- review queue generator
- entegrasyon planı

Önemli:
Ham MEB PDF'leri pakete dahil değildir.
Kaynak URL + metadata + hash yaklaşımı kullanılır.
VERIFIED olmayan sorular canonical bankaya yayınlanmaz.

Sonraki iş: gerçek MEB PDF'lerini bu pipeline üzerinden işlemek ve review kuyruğunu
doldurmak; ardından doğrulanmış kayıtları ana LGS AI Coach veritabanına aktarmaktır.
