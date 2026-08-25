import { AppShell } from "@/components/app-shell";
import { RunDetail } from "@/components/run-detail";
import { getFindings, getRuns, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function LatestRun() {
  await requireSession();
  try {
    const [latest] = await getRuns();
    const findings = latest ? await getFindings(latest.id) : [];
    return <AppShell><RunDetail run={latest || null} findings={findings} /></AppShell>;
  } catch (error) {
    const detail = error instanceof HostedApiError ? "Check the hosted API connection and try again." : "An unexpected error occurred.";
    return <AppShell><section className="empty-state"><div className="eyebrow">Collection service unavailable</div><h1>Evidence cannot be loaded.</h1><p>{detail}</p></section></AppShell>;
  }
}
