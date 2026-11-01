-- LGS KANKA — Supabase şeması
-- Bu dosyayı Supabase Dashboard > SQL Editor'de tek seferde çalıştır.

-- 1) Öğrenciler (profil + giriş)
create table if not exists students (
  id uuid primary key default gen_random_uuid(),
  username text unique not null,
  password_hash text not null,
  name text not null,
  gender text not null default 'boy',
  variant int not null default 0,
  registered_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

-- 2) Cevap kayıtları (günlük çalışma + pekiştirme)
create table if not exists answer_records (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id) on delete cascade,
  question_id text not null,
  subject text not null,
  unit int,
  unit_name text,
  topic text,
  selected_answer text,
  correct boolean not null default false,
  error_reason_code text,
  time_spent_sec int not null default 0,
  source text not null default 'gunluk',
  created_at timestamptz not null default now(),
  unique (student_id, question_id, source)
);
create index if not exists idx_answer_records_student
  on answer_records (student_id, created_at desc);

-- 3) Deneme sonuçları (biten sınavlar)
create table if not exists exam_results (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null references students(id) on delete cascade,
  month int not null,
  month_name text not null,
  correct int not null default 0,
  wrong int not null default 0,
  empty int not null default 0,
  percentage int not null default 0,
  level text not null default '',
  by_subject jsonb,
  details jsonb,
  completed_at timestamptz not null default now()
);
create index if not exists idx_exam_results_student
  on exam_results (student_id, completed_at desc);

-- 4) Yarım kalan denemeler (kaldığın yerden devam et)
create table if not exists exam_sessions (
  student_id uuid not null references students(id) on delete cascade,
  month int not null,
  answers jsonb not null default '{}',
  current_index int not null default 0,
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (student_id, month)
);

-- 5) Günlük çalışma durumu (kaldığın yerden devam et)
create table if not exists study_sessions (
  student_id uuid not null references students(id) on delete cascade,
  session_date date not null,
  solved int not null default 0,
  correct int not null default 0,
  target int not null default 24,
  state jsonb not null default '{}',
  updated_at timestamptz not null default now(),
  primary key (student_id, session_date)
);

-- 6) Pekiştirme görevleri
create table if not exists reinforcement_tasks (
  id text not null,
  student_id uuid not null references students(id) on delete cascade,
  subject text not null,
  unit int,
  unit_name text,
  topic text,
  source text not null default 'gunluk',
  wrong_count int not null default 0,
  question_ids jsonb not null default '[]',
  answers jsonb not null default '{}',
  correctness jsonb not null default '{}',
  status text not null default 'bekliyor',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (id, student_id)
);

-- 7) Oyun ilerlemesi
create table if not exists game_progress (
  student_id uuid not null references students(id) on delete cascade,
  game_type text not null,
  best_score int not null default 0,
  total_plays int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (student_id, game_type)
);

-- 8) Rozetler
create table if not exists badge_progress (
  student_id uuid not null references students(id) on delete cascade,
  badge_id text not null,
  earned boolean not null default false,
  earned_at timestamptz,
  progress int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (student_id, badge_id)
);

-- Güvenlik: tüm tablolarda satır düzeyi koruma.
-- Uygulamanın sunucu API'leri secret key ile çalıştığı için RLS'i atlar;
-- dışarıdan anon anahtarla hiçbir şeye erişilemez.
alter table students enable row level security;
alter table answer_records enable row level security;
alter table exam_results enable row level security;
alter table exam_sessions enable row level security;
alter table study_sessions enable row level security;
alter table reinforcement_tasks enable row level security;
alter table game_progress enable row level security;
alter table badge_progress enable row level security;