import Link from "next/link";
import { Status } from "@/components/status";
import { RunNowButton } from "@/components/run-now-button";
import { HostedFinding, HostedRun } from "@/lib/types";

function formattedDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not available";
}

export function RunDetail({ run, findings }: { run: HostedRun | null; findings: HostedFinding[] }) {
  if (!run) return <section className="empty-state"><div className="eyebrow">No evidence yet</div><h1>Start your first collection.</h1><p>The collector will use the configured application-only Microsoft Graph permissions and retain findings, not raw Graph responses.</p><RunNowButton /></section>;
  return <><section className="hero"><div className="eyebrow">Run detail · {run.source}</div><h1>{formattedDate(run.completedAt || run.createdAt)}</h1><p>{run.status === "COMPLETE" ? `${findings.length} controls were evaluated. Read the evidence per control; no aggregate score is calculated.` : run.status === "FAILED" ? run.failureReason || "The collection failed before evidence could be read." : "Evidence collection is in progress."}</p><RunNowButton /></section>{run.status === "COMPLETE" ? <table className="table"><thead><tr><th>Control</th><th>Verdict</th><th>Rationale</th></tr></thead><tbody>{findings.map((finding) => <tr key={finding.id}><td><Link href={`/runs/${run.id}/findings/${finding.controlId}`}><b>{finding.controlId}</b> — {finding.title}</Link></td><td><Status verdict={finding.verdict}/></td><td>{finding.rationale}</td></tr>)}</tbody></table> : null}</>;
}
