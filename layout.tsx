# Investing Recap Dashboard

A dashboard that automatically generates **factual** market recaps for a watchlist
of tickers/indexes, using a RAG-grounded, DAG-orchestrated pipeline.

v1 is strictly factual (price moves, filings, news) — **no opinions, predictions,
or buy/sell recommendations**. Opinionated analysis is a planned phase 2, gated
behind human review / disclaimers given investment-advice concerns.

## Stack
- **Frontend**: Vercel (Next.js) — dashboard, watchlist management, live run status, reports
- **Database**: Supabase (Postgres + pgvector) — see `supabase/migrations/`
- **Worker**: Render — background service executing the DAG
  (ingest → cluster → enrich → draft → assemble), written in Python
- **LLM**: Anthropic API — draft node

## Repo structure
```
supabase/
  migrations/     # schema SQL, applied via Supabase CLI or dashboard
  seed.sql        # starter watchlist for local dev
dashboard/        # Next.js app (Vercel)
  app/
  components/
  lib/
worker/           # DAG orchestration service (Render, Python)
  main.py         # poll loop entrypoint
  nodes/          # one file per DAG step (ingest, cluster, enrich, draft, assemble)
  lib/            # shared helpers (Supabase client, DAG run/step tracking, embeddings)
  scripts/        # one-off scripts (e.g. scheduled run trigger for cron)
```

## Pipeline (DAG)
1. **Ingest** — pull price/volume + news per watchlist symbol → `raw_items`
2. **Cluster** — group same-run items by symbol/theme via embedding similarity
3. **Enrich** — RAG: pull related historical context via vector search
4. **Draft** — LLM call per cluster, facts-only prompt → section text
5. **Assemble** — combine sections into a `reports` row

Every step writes progress to `dag_steps` so the dashboard can show live status.

## Setup (once you have Supabase/Vercel/Render accounts)
1. Create a Supabase project, run `supabase/migrations/0001_init_schema.sql`
2. Optionally run `supabase/seed.sql` for a starter watchlist
3. Copy `.env.example` → `.env` in both `dashboard/` and `worker/`, fill in keys
4. `dashboard/`: deploy to Vercel
5. `worker/`: deploy to Render as a background worker

## Status
Scaffold only — see ticket backlog for build order. Not yet deployed.
