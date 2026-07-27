import { NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabaseServer";

// Mirrors worker/src/lib/types.ts DAG_STEP_ORDER. Duplicated here rather
// than shared across packages since dashboard/ and worker/ are separate
// deployables in this monorepo. If this list changes, update both.
const DAG_STEP_ORDER = ["ingest", "cluster", "enrich", "draft", "assemble"] as const;

// Server-side only — uses the service role key via supabaseServer.
// Creates the dag_runs row AND its 5 pending dag_steps rows (same shape
// the worker's own createRun() produces), so the worker's poll loop just
// needs to find a pending run and start updating existing step rows.
export async function POST() {
  const { data: run, error: runError } = await supabaseServer
    .from("dag_runs")
    .insert({ status: "pending" })
    .select()
    .single();

  if (runError || !run) {
    return NextResponse.json({ error: runError?.message ?? "Failed to create run" }, { status: 500 });
  }

  const stepRows = DAG_STEP_ORDER.map((step_name) => ({
    run_id: run.id,
    step_name,
    status: "pending" as const,
  }));

  const { error: stepsError } = await supabaseServer.from("dag_steps").insert(stepRows);

  if (stepsError) {
    return NextResponse.json({ error: stepsError.message }, { status: 500 });
  }

  return NextResponse.json({ run }, { status: 201 });
}
