import { NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabaseServer";

// Resets a failed run so the worker's poll loop picks it back up.
//
// NOTE on "resume from last completed step": the current worker
// (worker/src/index.ts) always re-runs the full pipeline top to bottom
// when it picks up a pending run — it does not skip steps that already
// succeeded. True step-level resume would require the worker to check
// each step's existing status before running it and skip anything
// already "success". That's a worker-side change, not a dashboard-side
// one — flagging here since this route's name implies more than the
// current worker behavior actually does. Fine for v1 given how cheap
// re-running ingest/cluster/enrich/draft/assemble is at this scale.
export async function POST(request: Request) {
  const { runId } = (await request.json()) as { runId?: string };

  if (!runId) {
    return NextResponse.json({ error: "runId is required" }, { status: 400 });
  }

  const { error: stepsError } = await supabaseServer
    .from("dag_steps")
    .update({ status: "pending", error: null, output: null, started_at: null, finished_at: null })
    .eq("run_id", runId)
    .in("status", ["failed", "skipped"]);

  if (stepsError) {
    return NextResponse.json({ error: stepsError.message }, { status: 500 });
  }

  const { error: runError } = await supabaseServer
    .from("dag_runs")
    .update({ status: "pending", finished_at: null })
    .eq("id", runId);

  if (runError) {
    return NextResponse.json({ error: runError.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
