-- Source Engine v1.0 question bank. Apply manually after provisioning PostgreSQL.
-- No production schema is modified by this integration task.
create table if not exists question_sources (
  id text primary key,
  source_type text not null check (source_type in ('REAL_LGS','MEB_SAMPLE','MEB_BOOK','MEB_CURRICULUM','VERIFIED_EXTERNAL','AI_GENERATED')),
  year int check (year is null or year >= 2018),
  official_index_url text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (id, source_type),
  constraint source_url_official_meb_domain check (
    official_index_url ~ '^https://([a-z0-9-]+\.)*meb\.gov\.tr(/|$)' or
    official_index_url ~ '^https://([a-z0-9-]+\.)*meb\.k12\.tr(/|$)'
  ),
  constraint source_ai_identity check ((source_type = 'AI_GENERATED' and id like 'AI-%') or (source_type <> 'AI_GENERATED' and id not like 'AI-%'))
);

create table if not exists questions (
  id text primary key,
  source_id text not null,
  source_type text not null check (source_type in ('REAL_LGS','MEB_SAMPLE','MEB_BOOK','MEB_CURRICULUM','VERIFIED_EXTERNAL','AI_GENERATED')),
  year int check (year is null or year >= 2018),
  booklet text,
  subject text not null,
  grade int not null check (grade = 8),
  question_number int not null check (question_number > 0),
  stem text not null,
  options jsonb not null,
  answer text,
  solution text,
  status text not null check (status in ('DRAFT','EXTRACTED','AUTO_CHECKED','NEEDS_REVIEW','VERIFIED','REJECTED')),
  curriculum jsonb not null default '{}'::jsonb,
  verification jsonb not null default '{}'::jsonb,
  source_hash text check (source_hash is null or source_hash ~ '^[a-f0-9]{64}$'),
  duplicate_of text references questions(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint question_source_type_fk foreign key (source_id, source_type) references question_sources(id, source_type),
  constraint real_lgs_year_2018_plus check (source_type <> 'REAL_LGS' or (year is not null and year >= 2018)),
  constraint question_ai_identity check ((source_type = 'AI_GENERATED' and id like 'AI-%') or (source_type <> 'AI_GENERATED' and id not like 'AI-%')),
  constraint verified_checks_complete check (
    status <> 'VERIFIED' or (
      coalesce((verification->>'source_verified')::boolean, false)
      and coalesce((verification->>'year_verified')::boolean, false)
      and coalesce((verification->>'booklet_verified')::boolean, false)
      and coalesce((verification->>'question_number_verified')::boolean, false)
      and coalesce((verification->>'text_verified')::boolean, false)
      and coalesce((verification->>'options_verified')::boolean, false)
      and coalesce((verification->>'answer_key_verified')::boolean, false)
      and coalesce((verification->>'curriculum_verified')::boolean, false)
      and coalesce((verification->>'solution_verified')::boolean, false)
      and coalesce((verification->>'duplicate_checked')::boolean, false)
      and answer is not null and solution is not null and source_hash is not null
      and curriculum ?& array['layer','subject','unit','topic','learningOutcome','skill','version']
      and curriculum->>'layer' in ('LGS_REFERENCE_2018_PLUS','CURRENT_TYMM')
    )
  ),
  constraint ai_never_official check ((source_type = 'AI_GENERATED' and source_id like 'AI-%') or (source_type <> 'AI_GENERATED' and source_id not like 'AI-%'))
);

create index if not exists idx_questions_subject on questions(subject);
create index if not exists idx_questions_status on questions(status);
create index if not exists idx_questions_year on questions(year);
create index if not exists idx_questions_source on questions(source_id);
create index if not exists idx_questions_curriculum_layer on questions((curriculum->>'layer'));
