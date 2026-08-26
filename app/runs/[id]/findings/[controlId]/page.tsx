import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Status } from "@/components/status";
import { getFindings, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Finding({ params }: { params: Promise<{ id: string; controlId: string }> }) {
  const session = await requireSession();
  const { id, controlId } = await params;
  try {
    const finding = (await getFindings(session.tenantId, id)).find((item) => item.controlId === controlId);
    if (!finding) notFound();
    return <AppShell><article className="detail"><section className="hero"><div className="eyebrow">{finding.domain} · NIS2 article {finding.nis2}</div><h1>{finding.controlId}: {finding.title}</h1><Status verdict={finding.verdict}/></section><section className="card"><h2>Rationale</h2><p>{finding.rationale}</p><p className="muted">Limitation: {finding.limits}</p></section><section><h2>Queried endpoints</h2>{finding.endpoints.map((endpoint) => <code className="endpoint" key={endpoint}>{endpoint}</code>)}</section><section className="card"><h2>Stored evidence summary</h2><p className="muted">Raw Graph responses are not stored. Object references are keyed pseudonyms.</p><dl className="summary-list"><div><dt>Pseudonymous object references</dt><dd>{finding.objectIds.length}</dd></div>{Object.entries(finding.counts).map(([name, count]) => <div key={name}><dt>{name}</dt><dd>{count}</dd></div>)}</dl></section><section><a className="filter" href={finding.remediation}>Open Microsoft remediation guidance →</a></section></article></AppShell>;
  } catch (error) {
    if (!(error instanceof HostedApiError)) notFound();
    return <AppShell><section className="empty-state"><div className="eyebrow">Collection service unavailable</div><h1>Evidence cannot be loaded.</h1></section></AppShell>;
  }
}
