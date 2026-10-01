-- Reversible rollback for db/001_question_bank.sql.
-- Run only after backing up any records written after this migration.
drop table if exists questions;
drop table if exists question_sources;
