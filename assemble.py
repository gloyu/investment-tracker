import os
import time
from typing import Callable, TypeVar

from dotenv import load_dotenv

load_dotenv()

from lib.dag_tracker import (
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

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_MS", "30000")) / 1000

T = TypeVar("T")


def _run_step(run_id: str, step_name: DagStepName, work: Callable[[], tuple[T, dict]]) -> T:
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
    Runs the full DAG for a given run, threading each step's output into
    the next (cluster IDs -> enrichment map -> drafted sections -> report).
    Every step's status/output is written to dag_steps as it completes so
    the dashboard's realtime subscription reflects live progress.
    """
    from datetime import datetime, timezone

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
        # Specific step already recorded its own failure via _run_step/fail_step
        # above — this just marks the overall run as failed.
        mark_run_finished(run_id, "failed")


def poll() -> None:
    """Main poll loop — checks for a pending run every POLL_INTERVAL_SECONDS."""
    print(f"Worker starting. Polling every {POLL_INTERVAL_SECONDS}s for pending runs...")
    while True:
        try:
            run = get_next_pending_run()
            if run:
                execute_run(run["id"])
        except Exception as err:
            print(f"Poll loop error: {err}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    poll()
