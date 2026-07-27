# ============================================================
# Worker (Render background service) — environment variables
# Copy this file to .env and fill in real values.
# Never commit the actual .env file.
# ============================================================

# Supabase — service role key needed here since the worker writes
# directly to raw_items, dag_runs, dag_steps, clusters, reports
# (bypasses Row Level Security, so keep this key server-side only)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Anthropic API — used by the draft node (TICKET-4.1)
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Price/volume data source (TICKET-2.2)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key-here

# News data source (TICKET-2.3)
NEWS_API_KEY=your-news-api-key-here

# Embedding model provider (TICKET-3.1)
# Using OpenAI's embedding API here as an example — swap for whichever
# provider you choose (Voyage AI is another common pairing with Claude).
OPENAI_API_KEY=your-openai-api-key-here

# Worker behavior
# How often (ms) the worker polls dag_runs for a new pending run
POLL_INTERVAL_MS=30000

# EDGAR (SEC filings) — phase 2, no key required (public API) but
# a descriptive User-Agent header is required by SEC's usage policy
EDGAR_USER_AGENT="YourName YourEmail@example.com"
