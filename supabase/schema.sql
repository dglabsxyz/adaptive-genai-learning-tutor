-- Enterprise schema for the Adaptive GenAI Learning Tutor.
-- Apply with a migration runner or Supabase SQL editor. Local development
-- continues to use JSON files unless Supabase settings are explicitly enabled.

create extension if not exists pgcrypto;

create table if not exists tenants (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  external_id text not null unique,
  email text,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists tenant_memberships (
  tenant_id uuid not null references tenants(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('learner', 'educator', 'admin')),
  cohort_id text,
  created_at timestamptz not null default now(),
  primary key (tenant_id, user_id)
);

create table if not exists learner_profiles (
  tenant_id uuid not null references tenants(id) on delete cascade,
  learner_id text not null,
  user_id uuid references users(id),
  goals jsonb not null default '[]'::jsonb,
  active_exercise_id text,
  study_plan jsonb not null default '[]'::jsonb,
  history jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (tenant_id, learner_id)
);

create table if not exists skill_progress (
  tenant_id uuid not null references tenants(id) on delete cascade,
  learner_id text not null,
  skill text not null,
  proficiency numeric(5, 4) not null default 0,
  status text not null check (status in ('exposure', 'developing', 'proficient', 'mastered', 'review')),
  attempts integer not null default 0,
  correct_streak integer not null default 0,
  last_reviewed timestamptz,
  next_review date,
  evidence jsonb not null default '[]'::jsonb,
  status_reason text,
  next_review_reason text,
  last_change jsonb,
  updated_at timestamptz not null default now(),
  primary key (tenant_id, learner_id, skill),
  foreign key (tenant_id, learner_id) references learner_profiles(tenant_id, learner_id) on delete cascade
);

create table if not exists study_plans (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  learner_id text not null,
  goal text not null,
  modules jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  foreign key (tenant_id, learner_id) references learner_profiles(tenant_id, learner_id) on delete cascade
);

create table if not exists exercises (
  tenant_id uuid not null references tenants(id) on delete cascade,
  id text not null,
  learner_id text not null,
  skill text not null,
  exercise_type text not null,
  difficulty text not null,
  prompt text not null,
  choices jsonb not null default '[]'::jsonb,
  answer_key jsonb not null default '[]'::jsonb,
  expected_points jsonb not null default '[]'::jsonb,
  rubric text not null,
  hints jsonb not null default '[]'::jsonb,
  source_refs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  primary key (tenant_id, id),
  foreign key (tenant_id, learner_id) references learner_profiles(tenant_id, learner_id) on delete cascade
);

create table if not exists answers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  learner_id text not null,
  exercise_id text not null,
  answer_hash text,
  answer_length integer not null default 0,
  score numeric(5, 4),
  verdict text,
  covered_points jsonb not null default '[]'::jsonb,
  missed_points jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  foreign key (tenant_id, learner_id) references learner_profiles(tenant_id, learner_id) on delete cascade,
  foreign key (tenant_id, exercise_id) references exercises(tenant_id, id) on delete cascade
);

create table if not exists source_refs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  owner_type text not null,
  owner_id text not null,
  source_id text not null,
  record_type text not null,
  slug text,
  title text not null,
  path text not null,
  citations jsonb not null default '[]'::jsonb,
  snippet text,
  corpus_version_id uuid,
  vector_index_id uuid,
  last_researched_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists corpus_versions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  corpus_checksum text not null,
  document_count integer not null,
  file_count integer not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (tenant_id, corpus_checksum)
);

create table if not exists vector_indexes (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  corpus_version_id uuid references corpus_versions(id),
  provider text not null,
  index_checksum text,
  document_count integer not null,
  metadata jsonb not null default '{}'::jsonb,
  built_at timestamptz not null default now()
);

create table if not exists graph_checkpoints (
  tenant_id uuid not null references tenants(id) on delete cascade,
  thread_id text not null,
  checkpoint_id text not null,
  checkpoint jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  primary key (tenant_id, thread_id, checkpoint_id)
);

create table if not exists audit_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  event_id text not null unique,
  request_id text,
  user_id text,
  role text,
  learner_id text,
  event_type text not null,
  outcome text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists mcp_tool_calls (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  user_id text,
  learner_id text,
  tool_name text not null,
  outcome text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_memberships_role on tenant_memberships(tenant_id, role);
create index if not exists idx_progress_status on skill_progress(tenant_id, status);
create index if not exists idx_exercises_learner on exercises(tenant_id, learner_id);
create index if not exists idx_answers_exercise on answers(tenant_id, exercise_id);
create index if not exists idx_source_refs_owner on source_refs(tenant_id, owner_type, owner_id);
create index if not exists idx_audit_events_tenant_type on audit_events(tenant_id, event_type, created_at desc);
create index if not exists idx_mcp_tool_calls_tenant_tool on mcp_tool_calls(tenant_id, tool_name, created_at desc);
