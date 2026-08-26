import Link from "next/link";
import { Status } from "@/components/status";
import { VERDICT_HINT, domainLabel } from "@/lib/findings";
import { HostedFinding } from "@/lib/types";

export function FindingDetail({ runId, finding, previous, next }: { runId: string; finding: HostedFinding; previous?: HostedFinding; next?: HostedFinding }) {
  return <article className="detail">
    <nav className="crumbs" aria-label="Breadcrumb"><Link href={`/runs/${runId}`}>Evidence run</Link><span aria-hidden="true">/</span><span>{domainLabel(finding.domain)}</span><span aria-hidden="true">/</span><span className="current">{finding.controlId}</span></nav>
    <section className="hero detail-hero">
      <div className="eyebrow">{domainLabel(finding.domain)} · NIS2 article {finding.nis2}</div>
      <h1>{finding.controlId}: {finding.title}</h1>
      <p className="verdict-line"><Status verdict={finding.verdict} /> <span className="muted">{VERDICT_HINT[finding.verdict]}</span></p>
    </section>
    <section className="card"><h2>Rationale</h2><p>{finding.rationale}</p></section>
    <section className="note"><b>What this check cannot tell you</b><p>{finding.limits}</p></section>
    <section>
      <h2>Queried endpoints</h2>
      <p className="muted">The read-only Microsoft Graph requests behind this verdict.</p>
      {finding.endpoints.map((endpoint) => <code className="endpoint" key={endpoint}>GET {endpoint}</code>)}
    </section>
    <section className="card">
      <h2>Stored evidence summary</h2>
      <p className="muted">Raw Graph responses are not retained. Object references are keyed pseudonyms, so no user principal names or mailbox addresses are stored.</p>
      <dl className="summary-list">
        <div><dt>Pseudonymous object references</dt><dd>{finding.objectIds.length}</dd></div>
        {Object.entries(finding.counts).map(([name, count]) => <div key={name}><dt>{name.replace(/_/g, " ")}</dt><dd>{count}</dd></div>)}
      </dl>
    </section>
    <section className="detail-actions">
      <a className="primary-button" href={finding.remediation} target="_blank" rel="noreferrer">Open Microsoft remediation guidance ↗</a>
      <Link className="secondary-button" href={`/runs/${runId}`}>Back to all controls</Link>
    </section>
    <nav className="detail-nav" aria-label="Other controls in this run">
      {previous ? <Link className="detail-nav-link" href={`/runs/${runId}/findings/${previous.controlId}`}><span className="muted">← Previous control</span><span>{previous.controlId} {previous.title}</span></Link> : <span />}
      {next ? <Link className="detail-nav-link align-end" href={`/runs/${runId}/findings/${next.controlId}`}><span className="muted">Next control →</span><span>{next.controlId} {next.title}</span></Link> : null}
    </nav>
  </article>;
}
