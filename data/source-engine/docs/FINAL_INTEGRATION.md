# Ana Projeye Entegrasyon

Bu kaynak motoru final entegrasyon paketidir; ancak ham MEB PDF'leri bu ZIP'e dahil edilmez.

Ana proje hedef yapısı:

lgs-ai-coach/
  data/kaynaklar/
  data/curriculum/
  data/questions/
  scripts/source-ingestion/
  docs/source-system/
  prisma/ veya db/

Önerilen entegrasyon sırası:

1. Bu paketi ayrı klasörde sakla.
2. Ana projede backup/tag oluştur.
3. `data/kaynaklar/00-politika` belgelerini taşı.
4. `config/source-registry.json` içeriğini kaynak tablosuna aktar.
5. ingestion scriptlerini `scripts/source-ingestion` altına taşı.
6. canonical questions yalnızca VERIFIED kayıtlarla oluştur.
7. Supabase/Postgres migration'ını kontrollü uygula.
8. `npm run build`.
9. CI'da source validation testini çalıştır.

Ham PDF'lerin yeniden dağıtımı/ticari kullanımı ayrıca izin/telif incelemesine tabidir.
