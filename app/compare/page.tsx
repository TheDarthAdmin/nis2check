import { AppShell } from "@/components/app-shell";
import { ComparePicker } from "@/components/compare-picker";
import { CompareTable } from "@/components/compare-table";
import { getComparison, getRuns, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Compare({ searchParams }: { searchParams: Promise<{ from?: string; to?: string }> }) {
  const session = await requireSession();
  const { from, to } = await searchParams;
  try {
    const runs = (await getRuns(session.tenantId)).filter((run) => run.status === "COMPLETE");
    if (runs.length < 2) return <AppShell><section className="empty-state"><div className="eyebrow">Run comparison</div><h1>Two completed runs are needed.</h1><p>Run the collection twice to see which controls changed verdict between collections.</p></section></AppShell>;
    const later = runs.find((run) => run.id === to)?.id || runs[0].id;
    const laterIndex = runs.findIndex((run) => run.id === later);
    const older = runs[laterIndex + 1] || runs.find((run) => run.id !== later);
    const earlier = runs.find((run) => run.id === from && run.id !== later)?.id || older!.id;
    const findings = await getComparison(session.tenantId, earlier, later);
    return <AppShell>
      <section className="hero"><div className="eyebrow">Run comparison</div><h1>Changes, not scores.</h1><p>Compare two evidence collections to see what has appeared, improved, or needs follow-up again.</p></section>
      <ComparePicker runs={runs} from={earlier} to={later} />
      <CompareTable findings={findings} currentRunId={later} />
    </AppShell>;
  } catch (error) {
    const detail = error instanceof HostedApiError ? "Check the hosted API connection and try again." : "An unexpected error occurred.";
    return <AppShell><section className="empty-state"><div className="eyebrow">Collection service unavailable</div><h1>Runs cannot be compared.</h1><p>{detail}</p></section></AppShell>;
  }
}
