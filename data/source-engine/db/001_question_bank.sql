create table if not exists question_sources (
  id text primary key,
  source_type text not null,
  year int,
  official_index_url text,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists questions (
  id text primary key,
  source_id text not null references question_sources(id),
  source_type text not null,
  year int,
  booklet text,
  subject text not null,
  grade int not null check (grade = 8),
  question_number int not null,
  stem text not null,
  options jsonb not null default '{}'::jsonb,
  answer text,
  status text not null,
  curriculum jsonb not null default '{}'::jsonb,
  verification jsonb not null default '{}'::jsonb,
  source_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_questions_subject on questions(subject);
create index if not exists idx_questions_status on questions(status);
create index if not exists idx_questions_year on questions(year);
create index if not exists idx_questions_source on questions(source_id);
