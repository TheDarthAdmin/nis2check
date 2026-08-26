import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { RunDetail } from "@/components/run-detail";
import { getFindings, getRun, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Run({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireSession();
  const { id } = await params;
  try {
    const [run, findings] = await Promise.all([getRun(session.tenantId, id), getFindings(session.tenantId, id)]);
    return <AppShell><RunDetail run={run} findings={findings} /></AppShell>;
  } catch (error) {
    if (!(error instanceof HostedApiError)) notFound();
    return <AppShell><section className="empty-state"><div className="eyebrow">Collection service unavailable</div><h1>Evidence cannot be loaded.</h1><p>Check the hosted API connection and try again.</p></section></AppShell>;
  }
}
