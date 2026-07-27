"""
Single-shot entrypoint for the DAG pipeline. Runs as a Render Cron Job
on a schedule (see render.yaml) — no standing background worker needed.

Behavior:
- If a pending run already exists (e.g. someone clicked "Run now" on the
  dashboard since the last cron tick), pick that one up and run it.
- Otherwise, create a new run and execute it immediately.
- Either way, run exactly one DAG execution, then exit.

This replaces the old main.py (which polled forever) and
scripts/schedule_run.py (which only seeded a pending row for a separate
poller to later pick up) — this script does both in one process.

NOTE on the "Run now" dashboard button: since there's no standing worker
polling anymore, clicking "Run now" queues a pending run but it won't
execute until the next scheduled cron tick (or until you manually hit
"Trigger Run" on the cron job in the Render dashboard). This is a
deliberate tradeoff for daily-recap use cases — not suited to workloads
needing near-instant runs.
"""

import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from lib.dag_tracker import (
    create_run,
    get_next_pending_run,
    mark_run_started,
    mark_run_finished,
    start_step,
    complete_step,
    fail_step,
)
from lib.types import DagStepName
from nodes.ingest import ingest
from nodes.cluster import cluster_raw_items
from nodes.enrich import enrich_clusters
from nodes.draft import draft_sections
from nodes.assemble import assemble_report


def _run_step(run_id: str, step_name: DagStepName, work):
    """Wraps a step's work with consistent start/complete/fail tracking."""
    start_step(run_id, step_name)
    try:
        result, output = work()
        complete_step(run_id, step_name, output)
        print(f'[run {run_id}] step "{step_name}" completed')
        return result
    except Exception as err:
        fail_step(run_id, step_name, err)
        print(f'[run {run_id}] step "{step_name}" failed: {err}')
        raise


def execute_run(run_id: str) -> None:
    """
    Runs the full DAG once for a given run, threading each step's output
    into the next (cluster IDs -> enrichment map -> drafted sections ->
    report). Every step's status/output is written to dag_steps so the
    dashboard's realtime subscription reflects progress even though this
    process exits when it's done.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    mark_run_started(run_id)
    print(f"[run {run_id}] started")

    try:
        _run_step(run_id, "ingest", lambda: (None, ingest()))

        cluster_ids = _run_step(
            run_id, "cluster", lambda: cluster_raw_items(run_id, started_at)
        )

        enrichment_map = _run_step(
            run_id, "enrich", lambda: enrich_clusters(run_id, cluster_ids, started_at)
        )

        sections = _run_step(
            run_id, "draft", lambda: draft_sections(cluster_ids, enrichment_map)
        )

        _run_step(run_id, "assemble", lambda: assemble_report(run_id, sections))

        mark_run_finished(run_id, "success")
        print(f"[run {run_id}] finished successfully")
    except Exception:
        # Specific step already recorded its own failure via _run_step/fail_step.
        mark_run_finished(run_id, "failed")
        raise


def main() -> None:
    run = get_next_pending_run()
    if run:
        print(f"Found existing pending run {run['id']}, executing it.")
        run_id = run["id"]
    else:
        print("No pending run found, creating a new one.")
        run = create_run()
        run_id = run["id"]

    execute_run(run_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"Run failed: {err}")
        sys.exit(1)
