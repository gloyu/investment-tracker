import { supabase } from "@/lib/supabaseClient";

interface ReportSection {
  symbol: string;
  headline: string;
  body: string;
  metrics: Record<string, string>;
}

interface Report {
  id: string;
  generated_at: string;
  sections: ReportSection[];
}

// Server component — fetches fresh on every request. Fine for this
// dashboard's traffic level; revisit with caching if usage grows.
async function getLatestReport(): Promise<Report | null> {
  const { data, error } = await supabase
    .from("reports")
    .select("id, generated_at, sections")
    .order("generated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    console.error("Failed to fetch latest report:", error.message);
    return null;
  }

  return data as Report | null;
}

export default async function HomePage() {
  const report = await getLatestReport();

  if (!report) {
    return (
      <div>
        <h1>No reports yet</h1>
        <p>
          Once a DAG run completes, its report will show up here. Check{" "}
          <a href="/runs">run status</a> to see if one is in progress.
        </p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <h1>Market Recap</h1>
      <p style={{ color: "#666" }}>
        Generated {new Date(report.generated_at).toLocaleString()}
      </p>

      {report.sections.length === 0 && <p>No sections in this report.</p>}

      {report.sections.map((section) => (
        <section
          key={section.symbol}
          style={{ marginTop: "1.5rem", paddingBottom: "1.5rem", borderBottom: "1px solid #eee" }}
        >
          <h2 style={{ marginBottom: "0.25rem" }}>
            {section.symbol} — {section.headline}
          </h2>
          <p>{section.body}</p>
          {Object.keys(section.metrics).length > 0 && (
            <dl style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", fontSize: "0.9rem" }}>
              {Object.entries(section.metrics).map(([key, value]) => (
                <div key={key}>
                  <dt style={{ color: "#888" }}>{key}</dt>
                  <dd style={{ margin: 0, fontWeight: 600 }}>{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      ))}
    </div>
  );
}
