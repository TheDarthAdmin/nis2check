import { HostedFinding, HostedRun, Verdict } from "@/lib/types";

/** Follow-up first: an auditor opens a run to find what is not evidenced, not to read a score. */
export const VERDICT_ORDER: Verdict[] = ["FAIL", "PARTIAL", "INCONCLUSIVE", "PASS", "NOT_APPLICABLE"];
export const FOLLOW_UP: Verdict[] = ["FAIL", "PARTIAL", "INCONCLUSIVE"];

export const VERDICT_LABEL: Record<Verdict, string> = { FAIL: "Fail", PARTIAL: "Partial", INCONCLUSIVE: "Inconclusive", PASS: "Pass", NOT_APPLICABLE: "Not applicable" };

export const VERDICT_HINT: Record<Verdict, string> = {
  FAIL: "The evidence contradicts the control.",
  PARTIAL: "The control is only partly evidenced.",
  INCONCLUSIVE: "The evidence could not be read; nothing was assumed.",
  PASS: "The evidence supports the control.",
  NOT_APPLICABLE: "The control does not apply to this tenant.",
};

export function domainLabel(domain: string): string {
  const label = domain.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function verdictTally(findings: HostedFinding[]): { verdict: Verdict; count: number }[] {
  return VERDICT_ORDER.map((verdict) => ({ verdict, count: findings.filter((finding) => finding.verdict === verdict).length }));
}

export function needsFollowUp(findings: HostedFinding[]): HostedFinding[] {
  return sortFindings(findings).filter((finding) => FOLLOW_UP.includes(finding.verdict));
}

export function sortFindings(findings: HostedFinding[]): HostedFinding[] {
  return [...findings].sort((left, right) => VERDICT_ORDER.indexOf(left.verdict) - VERDICT_ORDER.indexOf(right.verdict) || left.controlId.localeCompare(right.controlId));
}

export function groupByDomain(findings: HostedFinding[]): { domain: string; findings: HostedFinding[] }[] {
  const domains = new Map<string, HostedFinding[]>();
  for (const finding of sortFindings(findings)) domains.set(finding.domain, [...(domains.get(finding.domain) || []), finding]);
  return [...domains.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([domain, items]) => ({ domain, findings: items }));
}

/** Always UTC and always labelled: evidence timestamps are read by people in other time zones. */
export function formatDateTime(value: string | null): string {
  if (!value) return "Not available";
  return `${new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value))} UTC`;
}

/** Rendered on the server only, so the client never disagrees about "now". */
export function formatAge(value: string | null, now: number = Date.now()): string | null {
  if (!value) return null;
  const days = Math.floor((now - new Date(value).getTime()) / 86_400_000);
  if (days < 0) return null;
  if (days === 0) return "today";
  return days === 1 ? "yesterday" : `${days} days ago`;
}

export function formatDuration(run: HostedRun): string | null {
  if (!run.createdAt || !run.completedAt) return null;
  const seconds = Math.round((new Date(run.completedAt).getTime() - new Date(run.createdAt).getTime()) / 1000);
  if (seconds < 0) return null;
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export function runLabel(run: HostedRun): string {
  return `${formatDateTime(run.completedAt || run.createdAt)} · ${run.source === "scheduled" ? "Scheduled" : "Manual"}`;
}
