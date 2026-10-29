# Cline için çalışma protokolü (LGS AI Coach projesi)

Bu dosya Cline'a, Hermes Agent'ın görevlendirdiği işlerde uyması gereken protokolü anlatır. Ayrıntılı sürüm: `~/.hermes/skills/autonomous-ai-agents/cline/references/cline-protocol.md`.

## Roller

- **Hermes** = ana çalışma alanı, planlama, kullanıcı iletişimi, doğrulama.
- **Cline** = kod ve kod ajanı işleri (feature, fix, refactor, test, script).
- **İnsan** = publish/push/deploy/VERIFIED onayı.

## Görev formatı

Her görev tek mesajda gelir: `GÖREV / KAPSAM / DEĞİŞMEYECEK / KABUL KRİTERLERİ / PROJE KURALLARI / DOĞRULAMA`. Cline bu mesajı alır almaz uygular, soru sormaz; belirsizse `NEEDS_REVIEW` işaretler.

## Çıktı formatı

```
ÖZET: <1 cümle>
DEĞİŞİKLİKLER:
- <path> — <ne değişti>
TEST: <komut> → <sonuç>
AÇIK NOKTALAR: <NEEDS_REVIEW / karar gerektirenler>
SONRAKİ ADIM: <varsa>
```

## Kurallar

1. Mevcut kod stiline uy; gereksiz refactor/rename yapma.
2. Bağımlılık eklemeden önce manifestleri ve komşu dosyaları oku.
3. Kök nedeni düzelt, belirti yamama.
4. Test/build gerçek sonucu ile raporla; asla uydurma.
5. Emin olunmayan değer/eşleştirme/cevap uydurma → `NEEDS_REVIEW`.
6. **LGS proje değişmezleri:** Resmî MEB kaynağı + SHA-256 otorite. AI yalnızca aday üretir; canonical answer, `VERIFIED`, provenance, curriculum verification **uydurulamaz**. `STRUCTURED_TEXT`/`IMAGE_BACKED`/`HYBRID` ayrımı ve visual provenance korunur. Answer key server-side kalır. Harici disk (`/media/selam/.../Lgs_çalışma_soruları_son`) **dokunulmaz**.

## Yasaklar

- `git push --force`, `git reset --hard`, geçmiş yeniden yazma
- Commit/push/deploy/publish (Product Owner açıkça istemedikçe)
- Secret okuma/yazma veya çıktıya koyma (`.env`, anahtarlar)
- Sistem dizinleri ve harici disk

## İş akışı

1. Hermes görevi yazar, `cline "<görev>" --json --yolo -c /home/selam/roller/web/lgs-ai-coach` ile başlatır.
2. Cline tamamlar, yukarıdaki çıktı formatını üretir.
3. Hermes `git diff` + build/test ile doğrular.
4. Kullanıcıya rapor sunulur; onay gelirse commit/push.