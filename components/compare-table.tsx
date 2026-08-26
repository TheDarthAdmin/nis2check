"use client";

import Link from "next/link";
import { useState } from "react";
import { Status } from "@/components/status";
import { ComparisonFinding } from "@/lib/types";

const CHANGE_LABEL: Record<ComparisonFinding["change"], string> = { NEW: "New control", REMOVED: "No longer collected", CHANGED: "Verdict changed", UNCHANGED: "Unchanged" };
const CHANGE_ORDER: ComparisonFinding["change"][] = ["CHANGED", "NEW", "REMOVED", "UNCHANGED"];

export function CompareTable({ findings, currentRunId }: { findings: ComparisonFinding[]; currentRunId: string }) {
  const changed = findings.filter((finding) => finding.change !== "UNCHANGED");
  const [changesOnly, setChangesOnly] = useState(changed.length > 0);
  const ordered = [...findings].sort((left, right) => CHANGE_ORDER.indexOf(left.change) - CHANGE_ORDER.indexOf(right.change) || left.controlId.localeCompare(right.controlId));
  const visible = changesOnly ? ordered.filter((finding) => finding.change !== "UNCHANGED") : ordered;
  return <>
    <div className="toolbar">
      <label className="check"><input type="checkbox" checked={changesOnly} onChange={(event) => setChangesOnly(event.target.checked)} disabled={changed.length === 0} /> Only show changes</label>
      <span className="result-count" role="status" aria-live="polite">{changed.length === 0 ? `No verdict changed across ${findings.length} controls` : `${changed.length} of ${findings.length} controls changed`}</span>
    </div>
    {visible.length === 0 ? <p className="empty-filter">Every control kept its previous verdict.</p> : <table className="table">
      <thead><tr><th scope="col">Control</th><th scope="col">Previous</th><th scope="col">Current</th><th scope="col">Change</th></tr></thead>
      <tbody>
        {visible.map((finding) => (
          <tr key={finding.controlId}>
            <td>{finding.current ? <Link className="control-link" href={`/runs/${currentRunId}/findings/${finding.controlId}`}><b>{finding.controlId}</b> {finding.current.title}</Link> : <span><b>{finding.controlId}</b> {finding.previous?.title}</span>}</td>
            <td>{finding.previous ? <Status verdict={finding.previous.verdict} /> : <span className="muted">—</span>}</td>
            <td>{finding.current ? <Status verdict={finding.current.verdict} /> : <span className="muted">—</span>}</td>
            <td><span className={`change change-${finding.change.toLowerCase()}`}>{CHANGE_LABEL[finding.change]}</span></td>
          </tr>
        ))}
      </tbody>
    </table>}
  </>;
}
