import Link from "next/link";
import { AutoRefresh } from "@/components/auto-refresh";
import { EvidenceExplorer } from "@/components/evidence-explorer";
import { RunNowButton } from "@/components/run-now-button";
import { RunSwitcher } from "@/components/run-switcher";
import { formatAge, formatDateTime, formatDuration, needsFollowUp } from "@/lib/findings";
import { HostedFinding, HostedRun } from "@/lib/types";

const STATUS_LABEL: Record<HostedRun["status"], string> = { RUNNING: "Collecting", COMPLETE: "Complete", FAILED: "Failed" };
const AGE_LABEL: Record<HostedRun["status"], string> = { RUNNING: "Started", COMPLETE: "Collected", FAILED: "Attempted" };

export function RunDetail({ run, findings, runs = [] }: { run: HostedRun | null; findings: HostedFinding[]; runs?: HostedRun[] }) {
  if (!run) {
    return <section className="empty-state">
      <div className="eyebrow">No evidence yet</div>
      <h1>Start your first collection.</h1>
      <p>The collector reads your tenant with the approved application-only Microsoft Graph permissions. It takes a few minutes, changes nothing, and stores findings rather than raw Graph responses.</p>
      <RunNowButton />
    </section>;
  }
  const lastComplete = runs.find((item) => item.id !== run.id && item.status === "COMPLETE");
  const age = formatAge(run.completedAt || run.createdAt);
  const duration = formatDuration(run);
  const pending = needsFollowUp(findings);
  return <>
    <section className="run-header">
      <div className="run-header-main">
        <div className="eyebrow">{run.source === "scheduled" ? "Scheduled collection" : "Manual collection"}</div>
        <h1>{formatDateTime(run.completedAt || run.createdAt)}</h1>
        <p className="run-meta">
          <span className={`status run-${run.status.toLowerCase()}`}>{STATUS_LABEL[run.status]}</span>
          {age ? <span>{AGE_LABEL[run.status]} {age}</span> : null}
          {duration && run.status === "COMPLETE" ? <span>Took {duration}</span> : null}
          <span>Collector {run.collectorVersion}</span>
        </p>
      </div>
      <div className="run-header-actions">
        <RunSwitcher runs={runs} currentId={run.id} />
        <RunNowButton busy={run.status === "RUNNING"} />
      </div>
    </section>
    {run.status === "RUNNING" ? <section className="card progress-card">
      <AutoRefresh />
      <h2>Reading your tenant…</h2>
      <p className="muted">Each control is queried read-only through Microsoft Graph. This page refreshes itself; you can close it and come back later.</p>
    </section> : null}
    {run.status === "FAILED" ? <section className="error-note" role="alert">
      <b>The collection stopped before evidence could be read.</b>
      <p>{run.failureReason || "No reason was recorded."}</p>
      <p>Nothing was changed in your tenant. Check that administrator approval is still in place, then start a new collection.{lastComplete ? <> The last complete run is still available: <Link href={`/runs/${lastComplete.id}`}>{formatDateTime(lastComplete.completedAt || lastComplete.createdAt)}</Link>.</> : null}</p>
    </section> : null}
    {run.status === "COMPLETE" ? <>
      <p className="run-summary">{pending.length === 0 ? "Every evaluated control is evidenced or does not apply to this tenant." : `${pending.length} of ${findings.length} controls need follow-up.`} Each verdict is backed by a rationale and the limits of the check; no aggregate score is calculated.{runs.length > 1 ? <> <Link href="/compare">See what changed since the previous run →</Link></> : null}</p>
      <EvidenceExplorer runId={run.id} findings={findings} />
    </> : null}
  </>;
}
