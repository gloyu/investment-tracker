from datetime import datetime, timezone
from typing import Any, Optional

from .supabase_client import supabase
from .types import DAG_STEP_ORDER, DagStepName


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run() -> dict:
    """
    Creates a new dag_runs row and a pending dag_steps row for every
    step in DAG_STEP_ORDER. Call this once at the start of a pipeline
    execution — individual node functions then call start_step/complete_step/
    fail_step for their own step_name as they run.
    """
    run_response = supabase.table("dag_runs").insert({"status": "pending"}).execute()
    run = run_response.data[0]

    step_rows = [
        {"run_id": run["id"], "step_name": step_name, "status": "pending"}
        for step_name in DAG_STEP_ORDER
    ]
    supabase.table("dag_steps").insert(step_rows).execute()

    return run


def mark_run_started(run_id: str) -> None:
    supabase.table("dag_runs").update(
        {"status": "running", "started_at": _now()}
    ).eq("id", run_id).execute()


def mark_run_finished(run_id: str, status: str) -> None:
    supabase.table("dag_runs").update(
        {"status": status, "finished_at": _now()}
    ).eq("id", run_id).execute()


def start_step(run_id: str, step_name: DagStepName, input_data: Optional[dict] = None) -> None:
    supabase.table("dag_steps").update(
        {"status": "running", "input": input_data, "started_at": _now()}
    ).eq("run_id", run_id).eq("step_name", step_name).execute()


def complete_step(run_id: str, step_name: DagStepName, output: Optional[dict] = None) -> None:
    supabase.table("dag_steps").update(
        {"status": "success", "output": output, "finished_at": _now()}
    ).eq("run_id", run_id).eq("step_name", step_name).execute()


def fail_step(run_id: str, step_name: DagStepName, error: Any) -> None:
    message = str(error)
    try:
        supabase.table("dag_steps").update(
            {"status": "failed", "error": message, "finished_at": _now()}
        ).eq("run_id", run_id).eq("step_name", step_name).execute()
    except Exception as db_error:
        # Don't raise here — we're already in a failure path, just log it.
        print(f"Failed to record failure for step {step_name} on run {run_id}: {db_error}")


def get_next_pending_run() -> Optional[dict]:
    """Fetches the earliest pending run, if any, for the poller to pick up."""
    response = (
        supabase.table("dag_runs")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
