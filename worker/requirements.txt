-- ============================================================
-- Similarity search functions
-- TICKET-3.2 / TICKET-3.3
-- Supabase-js can't express `<=>` (cosine distance) queries directly
-- through the query builder, so these are exposed as RPC-callable
-- Postgres functions instead.
-- ============================================================

-- Finds raw_items for a symbol most similar to a query embedding,
-- optionally restricted to items fetched before a given timestamp
-- (used by the enrich node to only pull *historical* context, not
-- items from the current run).
create or replace function match_raw_items(
  query_embedding vector(1536),
  match_symbol text,
  before_timestamp timestamptz,
  match_count int default 5
)
returns table (
  id uuid,
  content text,
  source text,
  published_at timestamptz,
  similarity float
)
language sql
stable
as $$
  select
    raw_items.id,
    raw_items.content,
    raw_items.source,
    raw_items.published_at,
    1 - (raw_items.embedding <=> query_embedding) as similarity
  from raw_items
  where raw_items.symbol = match_symbol
    and raw_items.fetched_at < before_timestamp
    and raw_items.embedding is not null
  order by raw_items.embedding <=> query_embedding
  limit match_count;
$$;

-- Finds raw_items belonging to a specific run window (fetched at or
-- after a given timestamp), used by the cluster node to gather the
-- current run's items per symbol without needing a run_id column on
-- raw_items itself.
create or replace function raw_items_since(
  match_symbol text,
  since_timestamp timestamptz
)
returns table (
  id uuid,
  content text,
  source text,
  embedding vector(1536)
)
language sql
stable
as $$
  select id, content, source, embedding
  from raw_items
  where symbol = match_symbol
    and fetched_at >= since_timestamp
$$;
