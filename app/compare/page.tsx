import { AppShell } from "@/components/app-shell";
import { Status } from "@/components/status";
import { getComparison, getRuns, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Compare() {
  await requireSession();
  try {
    const runs = await getRuns();
    if (runs.length < 2) return <AppShell><section className="empty-state"><div className="eyebrow">Run comparison</div><h1>Two completed runs are needed.</h1><p>Run the collection twice to compare changes in evidence over time.</p></section></AppShell>;
    const [current, previous] = runs;
    const findings = await getComparison(previous.id, current.id);
    return <AppShell><section className="hero"><div className="eyebrow">Run comparison</div><h1>Changes, not scores.</h1><p>Compare two evidence collections to focus on what has appeared, improved, or needs follow-up.</p></section><div className="compare"><div className="card"><b>{previous.completedAt || previous.createdAt}</b><p className="muted">Previous run</p></div><div className="arrow">→</div><div className="card"><b>{current.completedAt || current.createdAt}</b><p className="muted">Current run</p></div></div><table className="table"><thead><tr><th>Control</th><th>Previous</th><th>Current</th><th>Change</th></tr></thead><tbody>{findings.map((finding) => <tr key={finding.controlId}><td>{finding.current?.title || finding.previous?.title || finding.controlId}</td><td>{finding.previous ? <Status verdict={finding.previous.verdict} /> : "—"}</td><td>{finding.current ? <Status verdict={finding.current.verdict} /> : "—"}</td><td>{finding.change}</td></tr>)}</tbody></table></AppShell>;
  } catch (error) {
    const detail = error instanceof HostedApiError ? "Check the hosted API connection and try again." : "An unexpected error occurred.";
    return <AppShell><section className="empty-state"><div className="eyebrow">Collection service unavailable</div><h1>Runs cannot be compared.</h1><p>{detail}</p></section></AppShell>;
  }
}
