"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabaseClient";

interface DagStep {
  id: string;
  run_id: string;
  step_name: string;
  status: string;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

interface DagRun {
  id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

const STEP_ORDER = ["ingest", "cluster", "enrich", "draft", "assemble"];

function statusColor(status: string): string {
  switch (status) {
    case "success":
      return "#2e7d32";
    case "failed":
      return "#c62828";
    case "running":
      return "#1565c0";
    default:
      return "#999";
  }
}

export default function RunsPage() {
  const [runs, setRuns] = useState<DagRun[]>([]);
  const [stepsByRun, setStepsByRun] = useState<Record<string, DagStep[]>>({});
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    const { data: runData } = await supabase
      .from("dag_runs")
      .select("id, status, started_at, finished_at, created_at")
      .order("created_at", { ascending: false })
      .limit(10);

    const { data: stepData } = await supabase
      .from("dag_steps")
      .select("id, run_id, step_name, status, error, started_at, finished_at");

    setRuns((runData ?? []) as DagRun[]);

    const grouped: Record<string, DagStep[]> = {};
    for (const step of (stepData ?? []) as DagStep[]) {
      if (!grouped[step.run_id]) grouped[step.run_id] = [];
      grouped[step.run_id].push(step);
    }
    for (const runId in grouped) {
      grouped[runId].sort(
        (a, b) => STEP_ORDER.indexOf(a.step_name) - STEP_ORDER.indexOf(b.step_name)
      );
    }
    setStepsByRun(grouped);
  }, []);

  useEffect(() => {
    loadData();

    // Realtime subscription — dag_runs/dag_steps are enabled for
    // realtime in the schema migration (0001_init_schema.sql).
    const channel = supabase
      .channel("dag-progress")
      .on("postgres_changes", { event: "*", schema: "public", table: "dag_runs" }, loadData)
      .on("postgres_changes", { event: "*", schema: "public", table: "dag_steps" }, loadData)
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [loadData]);

  async function triggerRun() {
    setTriggering(true);
    setMessage(null);
    const res = await fetch("/api/trigger-run", { method: "POST" });
    const body = await res.json();
    if (!res.ok) {
      setMessage(`Error: ${body.error}`);
    } else {
      setMessage("Run triggered — worker will pick it up on its next poll.");
    }
    setTriggering(false);
  }

  async function retryRun(runId: string) {
    setMessage(null);
    const res = await fetch("/api/retry-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ runId }),
    });
    const body = await res.json();
    if (!res.ok) {
      setMessage(`Error: ${body.error}`);
    } else {
      setMessage("Run reset to pending — worker will retry it.");
    }
  }

  return (
    <div style={{ maxWidth: 700 }}>
      <h1>Run Status</h1>

      <button onClick={triggerRun} disabled={triggering} style={{ padding: "0.5rem 1rem" }}>
        {triggering ? "Triggering..." : "Run now"}
      </button>
      {message && <p style={{ color: "#555" }}>{message}</p>}

      {runs.length === 0 && <p style={{ marginTop: "1rem" }}>No runs yet.</p>}

      {runs.map((run) => (
        <div
          key={run.id}
          style={{ marginTop: "1.5rem", padding: "1rem", border: "1px solid #eee", borderRadius: 6 }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong style={{ color: statusColor(run.status) }}>{run.status.toUpperCase()}</strong>
              <span style={{ color: "#888", marginLeft: "0.75rem", fontSize: "0.85rem" }}>
                {new Date(run.created_at).toLocaleString()}
              </span>
            </div>
            {run.status === "failed" && (
              <button onClick={() => retryRun(run.id)} style={{ padding: "0.25rem 0.75rem" }}>
                Retry
              </button>
            )}
          </div>

          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
            {(stepsByRun[run.id] ?? []).map((step) => (
              <div
                key={step.id}
                title={step.error ?? undefined}
                style={{
                  padding: "0.35rem 0.7rem",
                  borderRadius: 4,
                  fontSize: "0.85rem",
                  color: "white",
                  background: statusColor(step.status),
                }}
              >
                {step.step_name}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
