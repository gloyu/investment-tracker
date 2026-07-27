-- ============================================================
-- Investing Recap Dashboard — Initial Schema
-- TICKET-1.1
-- ============================================================

-- Required for embeddings (RAG)
create extension if not exists vector;

-- ------------------------------------------------------------
-- watchlist: tickers/indexes being tracked
-- ------------------------------------------------------------
create table if not exists watchlist (
  id uuid primary key default gen_random_uuid(),
  symbol text not null unique,
  type text not null check (type in ('stock', 'index')),
  name text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- raw_items: raw ingested data per source, with embeddings
-- ------------------------------------------------------------
create table if not exists raw_items (
  id uuid primary key default gen_random_uuid(),
  symbol text not null references watchlist(symbol) on delete cascade,
  source text not null check (source in ('price', 'sec_filing', 'news')),
  content text not null,
  url text,
  published_at timestamptz,
  embedding vector(1536),
  fetched_at timestamptz not null default now()
);

create index if not exists idx_raw_items_symbol on raw_items(symbol);
create index if not exists idx_raw_items_source on raw_items(source);
create index if not exists idx_raw_items_fetched_at on raw_items(fetched_at);

-- vector similarity index (added after enough rows exist to be useful,
-- but safe to create now — ivfflat needs ANALYZE after bulk inserts)
create index if not exists idx_raw_items_embedding
  on raw_items using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ------------------------------------------------------------
-- dag_runs: one row per pipeline execution
-- ------------------------------------------------------------
create table if not exists dag_runs (
  id uuid primary key default gen_random_uuid(),
  status text not null default 'pending'
    check (status in ('pending', 'running', 'success', 'failed')),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- dag_steps: per-step state within a run (drives live dashboard view)
-- ------------------------------------------------------------
create table if not exists dag_steps (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references dag_runs(id) on delete cascade,
  step_name text not null
    check (step_name in ('ingest', 'cluster', 'enrich', 'draft', 'assemble')),
  status text not null default 'pending'
    check (status in ('pending', 'running', 'success', 'failed', 'skipped')),
  input jsonb,
  output jsonb,
  error text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_dag_steps_run_id on dag_steps(run_id);

-- ------------------------------------------------------------
-- clusters: grouped raw_items by symbol/theme, per run
-- ------------------------------------------------------------
create table if not exists clusters (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references dag_runs(id) on delete cascade,
  symbol text not null,
  theme text,
  item_ids uuid[] not null default '{}',
  embedding vector(1536),
  created_at timestamptz not null default now()
);

create index if not exists idx_clusters_run_id on clusters(run_id);
create index if not exists idx_clusters_symbol on clusters(symbol);

-- ------------------------------------------------------------
-- reports: final assembled output per run
-- ------------------------------------------------------------
create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references dag_runs(id) on delete cascade,
  generated_at timestamptz not null default now(),
  sections jsonb not null default '[]'
  -- sections shape: [{ symbol, headline, body, metrics, source_item_ids }]
);

create index if not exists idx_reports_run_id on reports(run_id);

-- ------------------------------------------------------------
-- Realtime: enable so the dashboard can subscribe to live run progress
-- ------------------------------------------------------------
alter publication supabase_realtime add table dag_runs;
alter publication supabase_realtime add table dag_steps;
