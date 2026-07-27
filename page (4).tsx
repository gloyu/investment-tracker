# Render deployment blueprint.
# Docs: https://render.com/docs/blueprint-spec
#
# Two services from the worker/ package:
#   1. A long-running background worker (the poll loop in src/index.ts)
#   2. A cron job that seeds a new pending run on a schedule, which the
#      background worker then picks up
#
# Env vars (ALPHA_VANTAGE_API_KEY, NEWS_API_KEY, OPENAI_API_KEY,
# ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) are marked
# sync: false — set their real values in the Render dashboard, don't
# commit them here. See worker/.env.example for the full list.

services:
  - type: worker
    name: investment-tracker-worker
    runtime: python
    rootDir: worker
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: ALPHA_VANTAGE_API_KEY
        sync: false
      - key: NEWS_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: POLL_INTERVAL_MS
        value: "30000"

  - type: cron
    name: investment-tracker-scheduled-run
    runtime: python
    rootDir: worker
    schedule: "0 21 * * 1-5" # weekdays, ~4pm ET after US market close (UTC, adjust for DST)
    buildCommand: pip install -r requirements.txt
    startCommand: python scripts/schedule_run.py
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
