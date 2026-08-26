import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ServiceUnavailable } from "@/components/service-unavailable";
import { RunDetail } from "@/components/run-detail";
import { getFindings, getRun, getRuns, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Run({ params }: { params: Promise<{ id: string }> }) {
  const session = await requireSession();
  const { id } = await params;
  try {
    const [run, findings, runs] = await Promise.all([getRun(session.tenantId, id), getFindings(session.tenantId, id), getRuns(session.tenantId)]);
    return <AppShell><RunDetail run={run} findings={findings} runs={runs} /></AppShell>;
  } catch (error) {
    if (!(error instanceof HostedApiError) || error.status === 404) notFound();
    return <AppShell><ServiceUnavailable error={error} /></AppShell>;
  }
}
