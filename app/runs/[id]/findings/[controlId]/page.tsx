import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ServiceUnavailable } from "@/components/service-unavailable";
import { FindingDetail } from "@/components/finding-detail";
import { groupByDomain } from "@/lib/findings";
import { getFindings, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Finding({ params }: { params: Promise<{ id: string; controlId: string }> }) {
  const session = await requireSession();
  const { id, controlId } = await params;
  try {
    const ordered = groupByDomain(await getFindings(session.tenantId, id)).flatMap((group) => group.findings);
    const index = ordered.findIndex((item) => item.controlId === controlId);
    if (index === -1) notFound();
    return <AppShell><FindingDetail runId={id} finding={ordered[index]} previous={ordered[index - 1]} next={ordered[index + 1]} /></AppShell>;
  } catch (error) {
    if (!(error instanceof HostedApiError) || error.status === 404) notFound();
    return <AppShell><ServiceUnavailable error={error} /></AppShell>;
  }
}
