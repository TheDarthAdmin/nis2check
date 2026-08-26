"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Status } from "@/components/status";
import { VERDICT_HINT, VERDICT_LABEL, domainLabel, groupByDomain, verdictTally } from "@/lib/findings";
import { HostedFinding, Verdict } from "@/lib/types";

function searchable(finding: HostedFinding): string {
  return [finding.controlId, finding.title, finding.rationale, finding.domain, finding.nis2, ...finding.endpoints].join(" ").toLowerCase();
}

export function EvidenceExplorer({ runId, findings }: { runId: string; findings: HostedFinding[] }) {
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [domain, setDomain] = useState("");
  const [query, setQuery] = useState("");
  const tally = useMemo(() => verdictTally(findings), [findings]);
  const groups = useMemo(() => groupByDomain(findings), [findings]);
  const needle = query.trim().toLowerCase();
  const filtered = verdicts.length > 0 || domain !== "" || needle !== "";
  const matches = (finding: HostedFinding) => (verdicts.length === 0 || verdicts.includes(finding.verdict)) && (domain === "" || domain === finding.domain) && (needle === "" || searchable(finding).includes(needle));
  const shownPerDomain = groups.map((group) => ({ ...group, shown: group.findings.filter(matches) }));
  const visible = shownPerDomain.reduce((total, group) => total + group.shown.length, 0);

  function toggleVerdict(verdict: Verdict) {
    setVerdicts((current) => (current.includes(verdict) ? current.filter((item) => item !== verdict) : [...current, verdict]));
  }

  function clearFilters() {
    setVerdicts([]);
    setDomain("");
    setQuery("");
  }

  return (
    <>
      <section className="tally" aria-label="Verdicts in this run">
        {tally.map(({ verdict, count }) => (
          <button key={verdict} type="button" className={`tile ${verdict.toLowerCase()}`} aria-pressed={verdicts.includes(verdict)} onClick={() => toggleVerdict(verdict)} title={`${VERDICT_HINT[verdict]} Select to filter.`}>
            <span className="tile-count">{count}</span>
            <span className="tile-label">{VERDICT_LABEL[verdict]}</span>
            <span className="tile-hint">{VERDICT_HINT[verdict]}</span>
          </button>
        ))}
      </section>
      <div className="toolbar">
        <input className="field" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search control, rationale or endpoint" aria-label="Search evidence" />
        <select className="field" value={domain} onChange={(event) => setDomain(event.target.value)} aria-label="Filter by domain">
          <option value="">All domains</option>
          {groups.map((group) => <option key={group.domain} value={group.domain}>{domainLabel(group.domain)} ({group.findings.length})</option>)}
        </select>
        {filtered ? <button type="button" className="quiet-button nav-button" onClick={clearFilters}>Clear filters</button> : null}
        <span className="result-count" role="status" aria-live="polite">{filtered ? `${visible} of ${findings.length} controls shown` : `${findings.length} controls evaluated`}</span>
      </div>
      {shownPerDomain.map(({ shown, ...group }) => {
        if (shown.length === 0) return null;
        return (
          <section className="domain-block" key={group.domain}>
            <div className="section-head">
              <h2>{domainLabel(group.domain)}</h2>
              <span className="muted">{shown.length === group.findings.length ? `${group.findings.length} controls` : `${shown.length} of ${group.findings.length} controls`}</span>
            </div>
            <table className="table">
              <thead><tr><th scope="col">Control</th><th scope="col">Verdict</th><th scope="col">What the evidence shows</th></tr></thead>
              <tbody>
                {shown.map((finding) => (
                  <tr key={finding.id}>
                    <td><Link className="control-link" href={`/runs/${runId}/findings/${finding.controlId}`}><b>{finding.controlId}</b> {finding.title}<span className="control-meta">NIS2 article {finding.nis2}</span></Link></td>
                    <td><Status verdict={finding.verdict} /></td>
                    <td>{finding.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        );
      })}
      {visible === 0 ? <p className="empty-filter">No control matches the current filters. <button type="button" className="quiet-button nav-button" onClick={clearFilters}>Clear filters</button></p> : null}
    </>
  );
}
