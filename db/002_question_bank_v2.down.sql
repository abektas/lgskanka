-- Question Bank v2 Foundation rollback (TASK-QBANK-001).
--
-- Yalnız `db/002_question_bank_v2.sql` dosyasının oluşturduğu nesneleri
-- düşürür. `questions` ve `question_sources` (migration 001) DOKUNULMAZ.
--
-- Sıralama önemlidir: önce bağımlı tablolar, sonra trigger fonksiyonları,
-- en son dayanan tablolar (questions'a referans verdikleri için drop edilemez).
--
-- UYARI: Bu rollback yalnızca 002'den sonra yeni kayıt girilmemişse güvenlidir.
-- Girilmişse önce `db/001_question_bank.sql` içindeki source/provenance
-- disiplini uygulanmalıdır (bkz. handoff).

drop table if exists question_quality;
drop table if exists question_difficulty;
drop table if exists question_relations;
drop table if exists question_secondary_error_types;
drop table if exists question_pedagogy;
drop trigger if exists trg_question_pedagogy_primary_distinct on question_pedagogy;
drop function if exists reject_primary_conflicting_secondary();
drop function if exists reject_secondary_equal_primary();
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