-- Question Bank v2 Foundation rollback (TASK-QBANK-001).
--
-- Yalnız `db/002_question_bank_v2.sql` dosyasının oluşturduğu nesneleri
-- düşürür. `questions` ve `question_sources` (migration 001) DOKUNULMAZ.
--
-- Sıralama önemlidir. Önce TRIGGER'lar, sonra fonksiyonlar, en son
-- tablolar düşürülür.
--
-- Gözden kaçan nokta: `drop table` bir trigger'ı yanlışlıkla da düşürebilir,
-- ama bu doğru sıralama DEĞİLDİR — trigger tabloya bağlı olduğu için
-- önce tablo düşerse trigger da sessizce gider ve `drop trigger ... on <tablo>`
-- "relation does not exist" uyarısı verir. Bu dosyada önceki sürüm tam olarak
-- bu hatayı yapıyordu (rollback çalışıyordu ama yanlış gerekçeyle).
-- Önce trigger'ları düşürerek sıralamayı açık ve hatasız hale getiriyoruz.
--
-- UYARI: Bu rollback yalnızca 002'den sonra yeni kayıt girilmemişse güvenlidir.
-- Girilmişse önce `db/001_question_bank.sql` içindeki source/provenance
-- disiplini uygulanmalıdır (bkz. handoff).

-- 1) Trigger'lar (tablolar düşürülmeden önce)
drop trigger if exists trg_question_secondary_distinct on question_secondary_error_types;
drop trigger if exists trg_question_pedagogy_primary_distinct on question_pedagogy;

-- 2) Trigger fonksiyonları (trigger'lardan sonra)
drop function if exists reject_secondary_equal_primary();
drop function if exists reject_primary_conflicting_secondary();

-- 3) Tablolar — önce bağımlı olanlar
drop table if exists question_quality;
drop table if exists question_difficulty;
drop table if exists question_relations;
drop table if exists question_secondary_error_types;
drop table if exists question_pedagogy;
drop table if exists error_types;
drop table if exists question_learning_outcomes;
drop table if exists question_skills;
drop table if exists question_topics;
drop table if exists skills;
drop table if exists learning_outcomes;
drop table if exists topics;
drop table if exists units;
drop table if exists subjects;
drop table if exists curriculum_layers;