# LGS AI Coach — GitHub Collaboration Handshake

**Tarih:** 2026-10-02 · **Tür:** Reconnaissance (OBSERVE → VERIFY → REPORT → STOP)
**Kapsam dışı:** kod değişikliği, refactor, dependency, UI, migration, push.

Etiketler: **VERIFIED** (çalıştırıldı/okundu) · **OBSERVED** (kod okunarak görüldü) · **NOT VERIFIED** (test edilmedi).

## 1. Repository identity

| Alan | Değer | Etiket |
|---|---|---|
| Remote | `https://github.com/abektas/lgs-ai-coach.git` | VERIFIED |
| Depo | `abektas/lgs-ai-coach` — **public**, default branch `main`, ~4.1 MB | VERIFIED |
| Kaynak | GitHub = source of truth | VERIFIED |
| Push durumu | `codex/profile-3d-avatars` remote ile eşit (`efd6096`) | VERIFIED |

## 2. Current branch

- **Aktif:** `codex/profile-3d-avatars` @ `efd6096`, upstream ile senkron. **VERIFIED**
- `main` @ `efa2509` → aktif branch'in **4 commit** gerisinde. **VERIFIED**
- Ek worktree: `agents/greeting-in-turkish` @ `efa2509`. **VERIFIED**

## 3. Git status

Çalışma ağacı **tamamen temiz**: uncommitted değişiklik yok, untracked dosya yok. **VERIFIED**

## 4. Recent commits

```
efd6096 feat(source-engine): harden ingestion, quarantine bad artifact, subject-aware answer key
644ce4b feat(ai): add OpenAI to the provider chain and refresh smoke tests
a14dc38 feat(dev-env): canonicalize H1-H7 and add project skills and agents
4f9bec7 chore: remove repository junk and harden env handling
efa2509 feat: add MEB source ingestion pipeline and question bank API  (origin/main)
0c790e4 Add server-graded LGS Runner game
680a3fe Match 2048 Tetris drop and merge mechanics
ea683e2 Add Pomodoro study timer to dashboard
923c1e4 Add LGS exam result analysis cards
8244ed2 Add falling-tile 2048 game variant
910523a feat: use 3D student profile avatars
012373f docs: add project agent instructions
58c8076 chore: LGS AI Coach UI v2 baslangic surumu
```
**VERIFIED**

## 5. Project structure

| Dizin | Dosya | İçerik |
|---|---|---|
| `app/` | 24 | 11 sayfa + 3 API rotası + `globals.css` (3191 satır) |
| `components/` | 19 | dashboard, StudyFlow, oyunlar, ses kaydı, profil, nav |
| `data/` | 17 | `content.ts` (demo bank + taksonomi), `nav.ts`, `questions/questions.json` (**boş**), `source-engine/` |
| `lib/` | 0 | **boş dizin** |
| `tests/` | 14 | source-ingestion (Python) + API sözleşme (node) + taxonomy |
| `scripts/` | 36 | `source-ingestion/` (8 py) + smoke testi + pilot verisi |
| `db/` | 2 | SQL şema + down migration (**uygulanmamış**) |
| `docs/` | 3 | source-engine entegrasyonu, devralma raporu, pilot planı |

**VERIFIED** (dosya sayıları ölçüldü)

## 6. Runtime / framework

| Bileşen | Beyan | Gerçek |
|---|---|---|
| Next.js | `16.3.6` | 16.3.6 — **VERIFIED** |
| React | `19.1.0` | **VERIFIED** (build) |
| TypeScript | `^5.8.3` | ⚠️ kurulu **7.0.2** — **VERIFIED** (uyumsuzluk) |
| Node | — | v22.20.0 — **VERIFIED** |
| Runtime deps | next, react, react-dom | **3**, harici bağımlılık yok — **VERIFIED** |
| Python | — | 3.10.12; pipeline stdlib + `pypdf` 6.15.0 — **VERIFIED** |

## 7. Existing scripts

```
dev / build / start / lint
test:ai          → node scripts/ai-providers.smoke.mjs        (19 test, stub tabanlı)
test:source      → python3 unittest discover + node --test api-contract (83 + 3 test)
test:taxonomy    → node --test tests/canonical-taxonomy/…      (5 test)

## 8. Current question-bank architecture

**Kod gerçeği (OBSERVED):**
- Depo: `data/questions/questions.json` → **`[]` (0 kayıt)**. VERIFIED
- Şema: `canonical_schema.json` (status lifecycle, iki curriculum katmanı, 11 kontrol). OBSERVED
- Yaşam döngüsü kapısı: `validate_canonical.transition()` — `NEEDS_REVIEW → VERIFIED` yalnız 11 kontrolün tamamı `true` ise. OBSERVED
- Yayın: `publish_verified.publish()` — yalnız hâlihazırda VERIFIED olanları API satırına çevirir; cevap anahtarı sunucuda kalır. OBSERVED

**OFFICIAL/VERIFIED ile AI_GENERATED gerçekten ayrılıyor mu? — KODDA EVET, VERİDE TEST EDİLMEDİ:**
- `app/api/questions/route.ts:29` → `AI_GENERATED` kayıtları `AI-` öneki taşımak zorunda; diğer türler `AI-` ile **başlayamaz**. OBSERVED
- `db/001_question_bank.sql:15,40,58` → aynı kural üç CHECK kısıtı. OBSERVED
- `validate_source_registry.py:11` → tür listesi AI_GENERATED'ı içerir; registry'de **AI_GENERATED kaynak yok** (6 kayıt resmî MEB). VERIFIED
- ⚠️ **NOT VERIFIED:** Bu ayrım **hiçbir gerçek kayıtla çalıştırılmadı** (banka boş) ve kod tabanında **AI_GENERATED kayıt üreten bir yol yok**. Ayrım şu an yalnızca kapı olarak duruyor.

**Sunucu tarafı değerlendirme (OBSERVED):**
- `POST /api/questions` → `timingSafeEqual`, yalnız `{correct}` döner, cevabı sızdırmaz. VERIFIED (kod) / **NOT VERIFIED** (gerçek veriyle çalıştırılmadı)
- `POST /api/games/runner` → demo `questionBank` üzerinde sunucuda değerlendirme. OBSERVED

## 9. Source-ingestion architecture

- Registry: 6 resmî kayıt (`MEB-LGS-2022…2026`, `MEB-SAMPLE-ARCHIVE`), tümü `meb.gov.tr` altında HTTPS. VERIFIED
- Pipeline modülleri (8): download, manifest, extract, review-queue, validate-canonical, publish, source-trust, registry validator. OBSERVED
- Kaynak-trust: `source_trust.py` + `SafeRedirect` ile MEB/CDN allowlist ve redirect doğrulaması. OBSERVED
- Hash: SHA-256 manifestta; `validate_manifest_for_pdf` indirmeden önce hash/boyut/Content-Type/provenance doğruluyor. OBSERVED
- **Gerçek MEB pilotu:** `MEB-LGS-2022 / SAYISAL`, sha256 `8a1c6526…`, 33 sayfa, 7.98 MB, `NEEDS_REVIEW`, `published: false`. VERIFIED
- **Karantina:** 6 manifest (aynı sertifika PDF'i; 5'i yanlış `REAL_LGS` iddiası) `REJECTED` + gerekçe/reviewer/tarih; artifact'ler silinmedi. VERIFIED
- **Extraction:** 111 → **34 aday** (33'ü 4 seçenekli), konu bazlı kimlik. VERIFIED
- **Cevap anahtarı:** sayfa 33'ten `(subject, question_number)` ile eşleme; 34/34 eşlendi, 0 çakışma; `answer` null. VERIFIED
- **Duplicate:** SHA-256 parmak izi + `publish_verified` reddi. OBSERVED
- **Immutable:** var olan dosya değiştirilmez; atomik geçici dosya + `os.link`. OBSERVED

**Doküman ↔ kod:** `docs/source-engine-integration.md` "store is currently empty → `{items: [], count: 0}`" ifadesi **kodla uyumlu** (VERIFIED). Aynı dokümanın pipeline bölümü güncel durumu (kitapçık seçimi, karantina, 34 aday) yansıtmıyor — **eksik, yanlış değil**. OBSERVED

## 10. AI provider architecture

- Zincir (kod): **openai → gemini → openrouter**. VERIFIED
- `AI_PROVIDER` birincili seçer, `AI_FALLBACK_ORDER` sırayı değiştirir, anahtarsız sağlayıcı zincire girmez. OBSERVED
- Ortak sonuç: `{provider, model, text}`; hata `ProviderError.status` + `AllProvidersFailed` (502) + `attempts[]`. OBSERVED
- Timeout 45 s, prompt 4000 karakter, görsel 8 MB. OBSERVED
- `/api/ai` sözleşmesi: `{answer, provider, model}`; hata `{error}` / `{error, attempts}`. OBSERVED
- `.env.local` (**yalnız anahtar adları kontrol edildi, değerler okunmadı**): `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `AI_FALLBACK_ORDER`, `AI_TIMEOUT_MS`, `AI_MAX_PROMPT_CHARS`, `AI_MAX_IMAGE_BYTES`, `LOCAL_AI_BASE_URL` **tanımlı**; `NEXT_PUBLIC_SITE_URL` **yok**. VERIFIED (isim düzeyi)
- ⚠️ **Çelişki:** README `local` sağlayıcıyı ve `gemini → openrouter → local` sırasını anlatıyor; **kodda `local` yok**. `.env.local`'deki `LOCAL_AI_BASE_URL` ölü ayardır. VERIFIED
- ⚠️ **NOT VERIFIED:** Hiçbir sağlayıcı canlı çağrıyla doğrulanmadı; `test:ai` stub tabanlıdır.

## 11. API routes

| Method | Path | Amaç | UI kullanıyor mu |
|---|---|---|---|
| POST | `/api/ai` | AI teşhis/koç | ✅ `study-flow.tsx` |
| POST | `/api/games/runner` | LGS Runner | ✅ `lgs-runner.tsx` (demo banka) |
| GET | `/api/questions` | VERIFIED soru listesi | ❌ **hiçbir UI çağrısı yok** |
| POST | `/api/questions` | sunucuda değerlendirme | ❌ (`timingSafeEqual`) |

**VERIFIED** (`grep 'api/questions' app components` → boş)

## 12. Database state

- **Sürücü yok:** Prisma/Supabase/Postgres/SQLite bağımlılığı veya bağlantısı yok. VERIFIED
- `db/001_question_bank.sql` + `.down.sql` yalnızca **şema dokümanı**; migration çalıştırılmamış. OBSERVED
- Kalıcılık: tarayıcı `localStorage` (`lgs-ai-coach-profile`, `-tasks`, `-settings`, `-game-session`, `-pomodoro-v*`). VERIFIED
- **Auth yok**, öğrenci izolasyonu yok. VERIFIED

validate:sources → python3 validate_source_registry.py          (6 kayıt)
```
Genel `npm test` **yok**; `lint` script'i var, CI'a bağlı değil. **VERIFIED**


## 13. Privacy / KVKK observations

| Konu | Gözlem | Etiket |
|---|---|---|
| Ses | `MediaRecorder` + Web Speech; blob `revokeObjectURL` ile temizleniyor | OBSERVED |
| Kalıcı medya | Sunucuya yazılmıyor; reset'te `setPhoto(null)` / `setVoiceTranscript("")` | OBSERVED |
| Profil | Yalnız ad/cinsiyet/avatar tercihi `localStorage`'da | OBSERVED |
| Dış aktarım | Soru metni, öğrenci cevabı, "neden", transcript, isteğe bağlı görsel → LLM sağlayıcıya | OBSERVED |
| Veli onayı akışı | **Yok** | VERIFIED (yok) |
| Saklama süresi / silme talebi | **Tanımlı değil** | VERIFIED (yok) |
| Loglama | Öğrenci içeriği loglanmıyor (HANDOFF'a göre sunucu günlüğü 5 satır) | **NOT VERIFIED** |
| Gerçek PII | Bulunmadı | VERIFIED |

## 14. Security observations

| Alan | Durum |
|---|---|
| Auth/authorization | ❌ Yok (`middleware.ts` yok) — OBSERVED |
| Rate limit / kota | ❌ Yok — OBSERVED |
| Girdi doğrulama | ✅ `/api/ai` ve `/api/questions` sınırlı — VERIFIED (kod) |
| Prompt injection | 🟡 `body.prompt` doğrudan istemin içine giriyor; rol izolasyonu yok — OBSERVED |
| Cevap anahtarı sızıntısı | ✅ `toPublicQuestion` ile 3 alan soyuluyor — VERIFIED (kod) |
| **Demo bankada anahtar istemcide** | 🔴 `data/content.ts` `correct`/`explain` client bundle'ında — VERIFIED |
| Secret yönetimi | ✅ `.env*` ignore; `.env.example` temiz — VERIFIED |
| Kalan secret riski | ⚠️ Eski `refs/cline/checkpoints/*` commit'lerinde anahtar izleri (GitHub'a **gitmedi**) — OBSERVED |
| CORS | Varsayılan aynı-kaynak — **NOT VERIFIED** |

## 15. Test results

| Komut | Sonuç | Etiket |
|---|---|---|
| `npm run test:source` | **83 Python OK** + **3 node API sözleşme OK** | VERIFIED |
| `npm run test:ai` | **19/19** (stub tabanlı) | VERIFIED |
| `npm run test:taxonomy` | **5/5** | VERIFIED |
| `npx tsc --noEmit` | 0 hata | VERIFIED |
| `npm run validate:sources` | `OK: 6 official source records` | VERIFIED |

**Testlerin gerçekten ölçtüğü:**
- Python testleri gerçek fonksiyonları çalıştırır; ikisi gerçek 7,7 MB PDF'i kullanır. VERIFIED
- `api-contract.test.mjs` **çalışma zamanı değil, kaynak metni regex kontrolü** → HTTP davranışı test edilmiyor. VERIFIED (yöntem)
- `ai-providers.smoke.mjs` sahte sunucular kullanır → gerçek kimlik doğrulama testi değil. VERIFIED
- **Test edilmeyen:** UI/bileşen, e2e, gerçek `/api/questions` isteği, auth/rate-limit, persistans. VERIFIED (yok)

## 16. Build result

`npm run build` → **EXIT 0**; 16 rota: 11 statik sayfa + `/api/ai`, `/api/questions`, `/api/games/runner` dinamik. **VERIFIED**

## 17. Documentation/code inconsistencies

1. **README ↔ provider kodu:** README `local` + `gemini → openrouter → local` anlatıyor; kod `openai → gemini → openrouter`. VERIFIED
2. **README "Next integration" maddeleri** hâlâ geçerli. VERIFIED
3. **HANDOFF.md bayat:** "Git repo yok" diyor; repo mevcut ve senkron. VERIFIED
4. **`.env.local` ölü ayar:** `LOCAL_AI_BASE_URL` tanımlı, kodda `local` yok. VERIFIED
5. **`review-queue-pilot.json` bayat:** 111 kalem; güncel staging 34 aday. Commit edilmiş tutarsızlık. VERIFIED
6. **TypeScript sürüm farkı:** `package.json ^5.8.3` ↔ kurulu 7.0.2. VERIFIED
7. **AGENTS.md ↔ kod:** canonicalize, testle kilitli, uyumlu. VERIFIED

## 18. Current risks

| # | Risk | Etki |
|---|---|---|
| R1 | Soru bankası **boş**; UI demo sorular kullanıyor | Ürün gerçek içerik göstermiyor |
| R2 | Demo cevap anahtarı **istemci bundle'ında** | Gerçek bankaya geçişte doğrudan ihlal |
| R3 | `/api/questions` **UI'dan çağrılmıyor** | Kaynak motoru ↔ runtime köprüsü yok |
| R4 | `/api/ai` **auth + rate limit yok** | Kota kötüye kullanımı; onaysız çocuk verisi |
| R5 | İlerleme kalıcı değil (`localStorage`) | Kişiselleştirme kaybolur |
| R6 | 34 adayda `curriculum`/`solution` boş → 0 VERIFIED | Yayın yolu kapalı |

## 19. What is already working

- **VERIFIED:** Tüm test paketleri (110 kontrol) ve üretim build'i yeşil; çalışma ağacı temiz; branch remote ile senkron.
- **VERIFIED:** Source Engine gerçek MEB kaynağında uçtan uca çalışıyor: keşif → indirme → hash → manifest → extraction (34 aday) → resmî cevap anahtarı eşleme (34/34) → **0 yayın, 0 VERIFIED** (doğru davranış).
- **VERIFIED:** Provenance bütünlüğü: 11 kapı, `OFFICIAL_MEB_ONLY` otoritesi, 2018+ sınırı (4 noktada), AI_GENERATED kimlik ayrımı, karantina mekanizması.
- **VERIFIED:** Konusuz cevap eşleme kapatıldı (Matematik Q20=B, Fen Q20=D kanıtlandı).
- **VERIFIED:** Sınav talimatı / cevap anahtarı / alt maddeler artık sahte soru üretmiyor (111 → 34).
- **VERIFIED:** Öğrenciye görünen H1–H7 metinleri ile AGENTS.md canonical sözlüğü testle kilitli.

## 20. What is incomplete

- Soru bankası boş; UI `/api/questions` kullanmıyor; sunucu-tarafı değerlendirme gerçek bankayla hiç çalıştırılmadı. **VERIFIED**
- Curriculum mapping: depoda yalnız 6 ders **adı** var; kazanım/beceri kodu ve kanıt URL'si yok → otomatik eşleme mümkün değil. **VERIFIED**
- `solution` hiç dolmadı; `duplicate_checked`/`curriculum_verified` hiçbir kayıtta true değil. **VERIFIED**
- Auth, rate limit, veli onayı, saklama/silme politikası yok. **VERIFIED**
- AI sağlayıcıları canlı doğrulanmadı. **NOT VERIFIED**
- Bileşen/e2e testleri yok. **VERIFIED (yok)**

## 21. Recommended next task

**NEXT TASK (tek öneri): "Doğrulama kanıt paketi" — `build_review_packet.py` + testleri**

Kapsam (yalnız ekleme; hiçbir mevcut davranış değişmez):
1. `scripts/source-ingestion/build_review_packet.py`: staging + resmî PDF'i okuyup kayıt başına **kanıt** üretir — parmak izi ve duplicate grubu, `answer_key_map` (sayfa/ders/numara/kanıt), resmî anahtarın **bağımsız ikinci parse ile teyidi**, `validate_canonical.validate_record(require_verified=True)` çıktısından **bloker listesi**, curriculum/solution eksikleri.
2. Kayıtları **asla değiştirmez**: status `NEEDS_REVIEW` kalır; `answer`/`solution`/checks yazılmaz; `VERIFIED` üretilmez; `published=false`.
3. `tests/source-ingestion/test_review_packet.py`: duplicate gruplama, kanıt teyidi, girdi kaydının değişmediği, hiçbir kaydın doğrulanmadığı, gerçek 2022 PDF ile entegrasyon (34 aday, 34 teyitli cevap, `verifiable_now: 0`).

**Neden bu görev:** VERIFIED'e giden tek yol insan incelemesidir; incelemeyi mümkün kılan şey kanıttır. Mevcut çalışan sistemi bozmaz, uydurma üretmez, tek başına doğrulanabilir ve 34 adayın gerçek incelemesini açar.
**DoD:** `npm run test:source` yeşil · `npx tsc --noEmit` temiz · çıktıda `verifiable_now: 0` · hiçbir kayıtta `status != NEEDS_REVIEW` · `published: false`.

## 22. Files inspected

`AGENTS.md`, `README.md`, `HANDOFF.md`, `LGS_AI_COACH_MASTER_PROJE_PLANI_v2.0.md`, `package.json`, `.gitignore`, `.env.example` (yapı), `docs/source-engine-integration.md`, `docs/proje-devralma-2026-10-01.md`, `docs/superpowers/plans/2026-09-30-meb-source-ingestion-pilot.md`, `app/api/questions/route.ts`, `app/api/ai/route.ts`, `app/api/ai/providers.ts`, `app/dersler/page.tsx`, `components/study-flow.tsx`, `components/voice-recorder.tsx`, `components/profile-provider.tsx`, `data/content.ts`, `data/nav.ts`, `data/questions/questions.json`, `data/source-engine/config/source-registry.json`, `data/source-engine/data/curriculum-registry.json`, `db/001_question_bank.sql`, `scripts/source-ingestion/*.py` (8), `scripts/ai-providers.smoke.mjs`, `tests/source-ingestion/*`, `tests/canonical-taxonomy/*`, pilot manifest/staging/review/published JSON'ları.

**Not:** `.env.local` **içeriği okunmadı**; yalnızca anahtar adlarının varlığı kontrol edildi ve `.env.local` git'e izlenmiyor.

## 23. Git status after inspection

Bu raporun dışında **hiçbir değişiklik yapılmadı**. Yalnızca bu rapor dosyası eklendi ve §20 kuralına göre tek, odaklı commit ile kaydedilecek:
`docs: add github collaboration handshake`
**Push / merge / rebase / reset / clean yapılmadı.**

| R7 | API sözleşme testleri statik regex | Sözleşme bozulması yakalanmaz |
| R8 | TypeScript sürüm uyuşmazlığı | CI/ortam farkı |

---

# CURRENT PROJECT STATE

**FOUNDATION**
Next.js 16.3.6 + React 19 + TypeScript, sıfır harici runtime bağımlılığı; repo herkese açık, branch `codex/profile-3d-avatars` remote ile senkron, çalışma ağacı temiz, üretim build'i geçiyor. **VERIFIED**

**QUESTION BANK**
Şema ve 11 kapı mevcut ve sıkı; **depo boş (0 kayıt)**, UI demo `questionBank`'i kullanıyor, `/api/questions` hiçbir UI tarafından çağrılmıyor. OFFICIAL/AI_GENERATED ayrımı kodda var ama **gerçek kayıtla hiç çalıştırılmadı**. **VERIFIED** (mevcut durum)

**SOURCE INGESTION**
Gerçek MEB LGS 2022 SAYISAL pilotu uçtan uca çalışıyor: resmî sayfa → CDN PDF (7,7 MB, sha256 doğrulandı) → manifest → 34 aday → resmî cevap anahtarı eşleme (34/34, 0 çakışma) → **0 yayın**. Altı hatalı manifest `REJECTED` karantinada. **VERIFIED**

**AI PROVIDERS**
openai → gemini → openrouter zinciri, ortak `{provider, model, text}` sonucu, `attempts[]` hata sözleşmesi, timeout/limitler tanımlı. Üç sağlayıcı anahtarı `.env.local`'de tanımlı (**değerler okunmadı**). Canlı çağrı doğrulanmadı; README hâlâ kaldırılmış `local` sağlayıcıyı anlatıyor. **VERIFIED** (yapı) / **NOT VERIFIED** (canlı)

**SERVER-SIDE GRADING**
`POST /api/questions` `timingSafeEqual` ile sunucuda karşılaştırıp yalnız `{correct}` döndürüyor; `/api/games/runner` sunucuda değerlendiriyor ama demo banka kullanıyor. Gerçek bankayla hiç çalıştırılmadı. **VERIFIED** (kod) / **NOT VERIFIED** (çalışma zamanı)

**STUDENT LEARNING LOOP**
UI akışı uçtan uca çalışıyor (soru → cevap → neden → AI teşdisi), ancak **hiçbir şey kalıcı değil** (yalnız `localStorage`); H1–H7 sonucu yapılandırılmış değil, ilerleme/analitik demo veriden geliyor. **VERIFIED**

**ERROR TAXONOMY H1-H7**
Canonical sözlük (Master Plan §6 = runtime) `AGENTS.md`'ye işlendi; `data/content.ts` tek teknik kaynak; istem sözlüğü türetiliyor; 5 test kilitli. Kod–sözlük ayrışması **yok**. **VERIFIED**

**PRIVACY / KVKK**
Ses/fotoğraf kalıcı saklanmıyor, blob'lar revoke ediliyor, öğrenci profili yalnız tercih. Eksikler: veli onayı, saklama/silme politikası, auth, rate limit. **VERIFIED**

**TESTING**
110 kontrol yeşil: 83 Python (source ingestion, karantina, extraction, answer key — ikisi gerçek PDF ile), 3 API sözleşme (statik regex), 19 AI smoke (stub), 5 taxonomy. **Eksik:** UI/e2e, gerçek `/api/questions` isteği, güvenlik testi, persistans testi. **VERIFIED**

**PRODUCTION READINESS**
**Uygun değil.** Banka boş, UI bankaya bağlı değil, auth/rate limit yok, demo cevap anahtarı istemcide, müfredat/solution eksik. **VERIFIED**

| R9 | Eski checkpoint commit'lerinde anahtar izleri | Rotasyon gerekli |
