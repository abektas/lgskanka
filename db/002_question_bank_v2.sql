-- Question Bank v2 Foundation (TASK-QBANK-001).
--
-- KAPSAM: yalnız veri modeli foundation. Mevcut `questions` /
-- `question_sources` tablolarına dokunulmaz, yeniden oluşturulmaz ve var
-- olan veriye backfill yapılmaz. Tüm yeni tablolar nullable alanlarla
-- eklenir; idempotent ingestion'ı bozmamak için `if not exists` kullanılır.
--
-- Geri alınabilirlik: `db/002_question_bank_v2.down.sql` bu migration'ın
-- tam tersini uygular ve yalnız burada oluşturulan nesneleri düşürür.
--
-- Bağlayıcı kaynaklar:
--   - db/001_question_bank.sql            (mevcut provenance/verification)
--   - scripts/source-ingestion/canonical_schema.json
--   - data/content.ts → errorTypes         (kanonik H1–H7, elle yazılmadı)
--   - tests/canonical-taxonomy/canonical-taxonomy.test.mjs

-- ===========================================================================
-- 4.1 Curriculum foundation
-- ===========================================================================
-- İki katman (`LGS_REFERENCE_2018_PLUS`, `CURRENT_TYMM`) AYRI kayıt olarak
-- yaşar. `units`/`topics` katmana bağlı olduğu için aynı kavram iki katmanda
-- sessizce birleşemez: sınıflandırma için `subjects`, katman bazlı içerik
-- için `units` üzerinden gidilir.

create table if not exists curriculum_layers (
  code text primary key
    check (code in ('LGS_REFERENCE_2018_PLUS','CURRENT_TYMM')),
  description text,
  created_at timestamptz not null default now()
);

insert into curriculum_layers (code, description) values
  ('LGS_REFERENCE_2018_PLUS', 'LGS 2018+ sınav referans müfredatı'),
  ('CURRENT_TYMM', 'Yürürlükteki Türkiye Yüzyılı Maarif Modeli müfredatı')
on conflict (code) do nothing;

create table if not exists subjects (
  id text primary key,
  name text not null,
  created_at timestamptz not null default now(),
  unique (name)
);

create table if not exists units (
  id text primary key,
  layer_code text not null references curriculum_layers(code),
  subject_id text not null references subjects(id),
  name text not null,
  unique (layer_code, subject_id, name)
);

create table if not exists topics (
  id text primary key,
  unit_id text not null references units(id),
  name text not null,
  unique (unit_id, name)
);

create table if not exists learning_outcomes (
  id text primary key,
  topic_id text not null references topics(id),
  statement text not null,
  unique (topic_id, statement)
);

create table if not exists skills (
  id text primary key,
  -- Beceri bilinçli olarak `topic`'e değil `layer`'a bağlıdır: bir beceri
  -- birden çok konuya ait olabilir; konuya bağlansaydı çokluk tablosu gerekirdi.
  layer_code text not null references curriculum_layers(code),
  name text not null,
  description text,
  unique (layer_code, name)
);

-- ===========================================================================
-- 4.2 Question <-> topic/skill/learning outcome (many-to-many)
-- ===========================================================================
-- Üç tabloda aynı sözleşme: `confidence` 0..1 aralığında (güven seviyesi,
-- okuldaki zorluk değil) ve bir soru için EN FAZLA BİR birincil eşleşme.

create table if not exists question_topics (
  question_id text not null references questions(id) on delete cascade,
  topic_id text not null references topics(id) on delete cascade,
  is_primary boolean not null default false,
  confidence numeric(4,3) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  created_at timestamptz not null default now(),
  primary key (question_id, topic_id)
);

create table if not exists question_skills (
  question_id text not null references questions(id) on delete cascade,
  skill_id text not null references skills(id) on delete cascade,
  is_primary boolean not null default false,
  confidence numeric(4,3) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  created_at timestamptz not null default now(),
  primary key (question_id, skill_id)
);

create table if not exists question_learning_outcomes (
  question_id text not null references questions(id) on delete cascade,
  learning_outcome_id text not null references learning_outcomes(id) on delete cascade,
  is_primary boolean not null default false,
  confidence numeric(4,3) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  created_at timestamptz not null default now(),
  primary key (question_id, learning_outcome_id)
);

-- Kısmi unique index: "tek birincil" kuralı DB seviyesinde garanti edilir.
create unique index if not exists uq_question_topics_single_primary
  on question_topics(question_id) where is_primary;
create unique index if not exists uq_question_skills_single_primary
  on question_skills(question_id) where is_primary;
create unique index if not exists uq_question_lo_single_primary
  on question_learning_outcomes(question_id) where is_primary;

-- ===========================================================================
-- 4.3 Pedagogy — kanonik H1–H7
-- ===========================================================================
-- `error_types` tek kaynaktan türetilen referans tablosudur; `data/content.ts`
-- içindeki `errorTypes` ile birebir aynı olmalıdır. Kod listesi ELLE
-- yazılmamıştır: AGENTS.md gereği kanonik sözlük `errorTypes`'tir ve
-- Master Plan §6 ile kilitlidir.

create table if not exists error_types (
  code text primary key check (code in ('H1','H2','H3','H4','H5','H6','H7')),
  name text not null,
  prompt_hint text not null
);

create table if not exists question_pedagogy (
  question_id text primary key references questions(id) on delete cascade,
  primary_error_type text references error_types(code),
  cognitive_level text,
  requires_reading boolean not null default false,
  requires_reasoning boolean not null default false,
  requires_calculation boolean not null default false,
  requires_modeling boolean not null default false,
  requires_information_filtering boolean not null default false,
  solution_strategy text,
  misconception_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- cognitive_level bilinçli olarak serbest metin: görev kapsamında kademe
  -- taksonomisi bağlayıcı bir kaynaktan tanımlı değil. Sözlük tablosu eklemek
  -- mimari karar gerektirir; PENDING olarak not edildi. CHECK kısıtı YOK.
  constraint question_pedagogy_not_empty check (
    primary_error_type is not null
    or solution_strategy is not null
    or misconception_code is not null
    or requires_reading or requires_reasoning or requires_calculation
    or requires_modeling or requires_information_filtering
  )
);

create table if not exists question_secondary_error_types (
  question_id text not null references question_pedagogy(question_id) on delete cascade,
  error_type_code text not null references error_types(code),
  primary key (question_id, error_type_code)
);

-- İkincil hata listesi birincil hatayla AYNI kodu içeremez. PostgreSQL CHECK
-- kısıtı alt sorguya izin vermediği için trigger kullanıldı (bilinçli seçim).
create or replace function reject_secondary_equal_primary() returns trigger
language plpgsql as $$
declare
  primary_code text;
begin
  select qp.primary_error_type into primary_code
  from question_pedagogy qp where qp.question_id = new.question_id;
  if primary_code is not null and new.error_type_code = primary_code then
    raise exception 'ikincil hata birincil hatayla ayni olamaz: %', new.error_type_code
      using errcode = '23514';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_question_secondary_distinct on question_secondary_error_types;
create trigger trg_question_secondary_distinct
  before insert or update on question_secondary_error_types
  for each row execute function reject_secondary_equal_primary();

-- Ters yön: primary_error_type değişirse birincil olan ikincil listede kalamaz.
create or replace function reject_primary_conflicting_secondary() returns trigger
language plpgsql as $$
begin
  if new.primary_error_type is not null and exists (
    select 1 from question_secondary_error_types s
    where s.question_id = new.question_id and s.error_type_code = new.primary_error_type
  ) then
    raise exception 'birincil hata ikincil listede yer aliyor: %', new.primary_error_type
      using errcode = '23514';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_question_pedagogy_primary_distinct on question_pedagogy;
create trigger trg_question_pedagogy_primary_distinct
  before insert or update on question_pedagogy
  for each row execute function reject_primary_conflicting_secondary();

-- ===========================================================================
-- 4.4 Multi-dimensional difficulty
-- ===========================================================================
-- Question difficulty ile student level AYNI kavram değildir; burada yalnız
-- soru özelliği tutulur. Student level bu görevde oluşturulmaz.
-- `overall` toplam değil bağımsız bir ölçümdür: hesaplama kuralı ürün
-- kararı gerektirir, bu yüzden bu tabloda hesaplanmaz.

create table if not exists question_difficulty (
  question_id text primary key references questions(id) on delete cascade,
  conceptual numeric(4,3) check (conceptual is null or conceptual between 0 and 1),
  reading numeric(4,3) check (reading is null or reading between 0 and 1),
  calculation numeric(4,3) check (calculation is null or calculation between 0 and 1),
  reasoning numeric(4,3) check (reasoning is null or reasoning between 0 and 1),
  modeling numeric(4,3) check (modeling is null or modeling between 0 and 1),
  information_density numeric(4,3) check (information_density is null or information_density between 0 and 1),
  time_pressure numeric(4,3) check (time_pressure is null or time_pressure between 0 and 1),
  overall numeric(4,3) check (overall is null or overall between 0 and 1),
  assessment_method text,
  assessed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- assessed_at yalnız değerlendirme yöntemi biliniyorsa anlamlıdır.
  constraint difficulty_assessed_consistent check (
    (assessment_method is null and assessed_at is null)
    or (assessment_method is not null and assessed_at is not null)
  )
);

-- ===========================================================================
-- 4.5 Question relations
-- ===========================================================================

create table if not exists question_relations (
  question_id text not null references questions(id) on delete cascade,
  related_question_id text not null references questions(id) on delete cascade,
  relation_type text not null check (relation_type in (
    'EASIER_VARIANT','HARDER_VARIANT','SAME_CONCEPT','DIFFERENT_CONTEXT',
    'MISCONCEPTION_TARGET','LGS_STYLE_VARIANT','REINFORCEMENT','RETEST','VARIATION'
  )),
  created_at timestamptz not null default now(),
  primary key (question_id, related_question_id, relation_type),
  -- Soru kendisiyle ilişkilenemez.
  constraint question_relation_not_self check (question_id <> related_question_id)
);

-- Ters yön indeksi: "bu soruyla ilişkili sorular" sorgusu tek yönlü indekste
-- pahalı olurdu. İlişki yönü anlamlı olduğu için (EASIER_VARIANT çift yönlü
-- değildir) karşılıklı benzersizlik yalnız aynı yönde uygulanır.
create index if not exists idx_question_relations_reverse
  on question_relations(related_question_id, relation_type);

-- ===========================================================================
-- 4.6 Quality / review foundation
-- ===========================================================================
-- Mevcut `questions.verification` (jsonb) SİLİNMEZ — o kanonik kaynaktır.
-- Bu tablo onu tamamlar. `null` = "henüz değerlendirilmemiş" anlamına gelir
-- (`false` = değerlendirildi ve geçersiz bulundu); ikinci bir doğruluk
-- kaynağı üretmemek için varsayılan değer `null` seçildi.

create table if not exists question_quality (
  question_id text primary key references questions(id) on delete cascade,
  structure_valid boolean,
  answer_valid boolean,
  solution_valid boolean,
  curriculum_valid boolean,
  source_valid boolean,
  duplicate_checked boolean,
  pedagogy_checked boolean,
  quality_status text not null default 'UNREVIEWED' check (quality_status in (
    'UNREVIEWED','IN_REVIEW','APPROVED','CHANGES_REQUESTED','REJECTED'
  )),
  reviewed_by text,
  reviewed_at timestamptz,
  review_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Gözden geçirme kaydı ancak karar verildiyse anlamlıdır.
  constraint quality_review_consistent check (
    (reviewed_by is null and reviewed_at is null)
    or (reviewed_by is not null and reviewed_at is not null)
  ),
  -- İncelenmiş kayıt en az bir inceleme zamanı taşımalıdır; aksi halde
  -- "kim / ne zaman" çifti boş bir onay gibi görünür.
  constraint quality_review_has_content check (
    quality_status in ('UNREVIEWED','IN_REVIEW') or reviewed_at is not null
  )
);

-- ===========================================================================
-- 5. Versioning notu
-- ===========================================================================
-- Soru sürümlemesi için temel kurulur, ancak immutable revision tablosu bu
-- migration'da EKLENMEZ: görev kapsamı "temel oluştur" diyor, geçmiş
-- tablosu ayrı bir karardır. PENDING olarak handoff'a yazıldı.

-- ===========================================================================
-- 7. Indexing — yalnız belirtilen sorgular için
-- ===========================================================================
-- Erken optimizasyon yapılmadı; her indeks bir sorguya karşılık gelir:
--   adaptive selector  : soru -> konu/beceri/kazanım (ters yön)
--   curriculum gezinme: katman -> birim -> konu hiyerarşisi
--   kalite filtresi    : onaylı soruları hızlı çekmek
--   zorluk sıralaması  : overall / time_pressure ile sıralama

create index if not exists idx_question_topics_topic on question_topics(topic_id);
create index if not exists idx_question_skills_skill on question_skills(skill_id);
create index if not exists idx_question_lo_outcome on question_learning_outcomes(learning_outcome_id);
create index if not exists idx_quality_status on question_quality(quality_status);
create index if not exists idx_difficulty_overall on question_difficulty(overall);
create index if not exists idx_difficulty_time_pressure on question_difficulty(time_pressure);
create index if not exists idx_units_curriculum on units(layer_code, subject_id);
create index if not exists idx_topics_unit on topics(unit_id);
create index if not exists idx_skills_layer on skills(layer_code);
create index if not exists idx_pedagogy_primary_error on question_pedagogy(primary_error_type);