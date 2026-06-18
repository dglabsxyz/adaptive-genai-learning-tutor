-- Optional migration for deployments that set TUTOR_VECTOR_PROVIDER=pgvector.
-- Do not apply this migration for local demos or JSON-only persistence.

create extension if not exists vector;

create table if not exists corpus_embeddings (
  tenant_id uuid not null references tenants(id) on delete cascade,
  vector_index_id uuid not null references vector_indexes(id) on delete cascade,
  source_id text not null,
  record_type text not null,
  slug text,
  title text not null,
  path text not null,
  content text not null,
  embedding vector(1536),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  primary key (tenant_id, vector_index_id, source_id)
);

create index if not exists idx_corpus_embeddings_embedding
  on corpus_embeddings using ivfflat (embedding vector_cosine_ops);

create or replace function match_corpus_embeddings(
  query_embedding vector(1536),
  match_count integer default 5,
  record_type_filter text default null,
  vector_index_id_filter text default null,
  tenant_id_filter text default null
)
returns table (
  source_id text,
  record_type text,
  slug text,
  title text,
  path text,
  content text,
  metadata jsonb,
  score double precision
)
language sql
stable
as $$
  select
    corpus_embeddings.source_id,
    corpus_embeddings.record_type,
    corpus_embeddings.slug,
    corpus_embeddings.title,
    corpus_embeddings.path,
    corpus_embeddings.content,
    corpus_embeddings.metadata,
    1 - (corpus_embeddings.embedding <=> query_embedding) as score
  from corpus_embeddings
  where (tenant_id_filter is null or corpus_embeddings.tenant_id::text = tenant_id_filter)
    and (vector_index_id_filter is null or corpus_embeddings.vector_index_id::text = vector_index_id_filter)
    and (record_type_filter is null or corpus_embeddings.record_type = record_type_filter)
  order by corpus_embeddings.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;
