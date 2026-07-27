-- ============================================================
-- Row Level Security policies
-- Required because the dashboard's browser client uses the public
-- anon/publishable key directly for reads/writes on some tables.
-- ============================================================

alter table watchlist enable row level security;
alter table raw_items enable row level security;
alter table clusters enable row level security;
alter table dag_runs enable row level security;
alter table dag_steps enable row level security;
alter table reports enable row level security;

-- watchlist: dashboard manages this directly from the browser
-- (app/watchlist/page.tsx does select/insert/update/delete with anon key)
create policy "public can manage watchlist" on watchlist
  for all using (true) with check (true);

-- dag_runs / dag_steps: dashboard reads + subscribes via realtime
-- (app/runs/page.tsx) — read-only from the browser, writes only happen
-- server-side via the secret key (worker, trigger-run, retry-run routes)
create policy "public can read dag_runs" on dag_runs
  for select using (true);

create policy "public can read dag_steps" on dag_steps
  for select using (true);

-- reports: dashboard reads the latest report (app/page.tsx)
create policy "public can read reports" on reports
  for select using (true);

-- raw_items and clusters: NO policies — only the worker (using the
-- secret key, which bypasses RLS entirely) ever touches these.
-- Leaving them policy-less means the anon key gets zero access, which
-- is correct — the dashboard never reads/writes these directly.
