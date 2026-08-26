export type Verdict = "PASS" | "PARTIAL" | "FAIL" | "NOT_APPLICABLE" | "INCONCLUSIVE";

export type TenantStatus = {
  tenantId: string;
  consentGranted: boolean;
  consentedAt: string | null;
};

export type HostedRun = {
  id: string;
  status: "RUNNING" | "COMPLETE" | "FAILED";
  source: "manual" | "scheduled";
  collectorVersion: string;
  createdAt: string | null;
  completedAt: string | null;
  failureReason: string | null;
};

export type HostedFinding = {
  id: string;
  controlId: string;
  nis2: string;
  domain: string;
  title: string;
  verdict: Verdict;
  rationale: string;
  endpoints: string[];
  remediation: string;
  limits: string;
  objectIds: string[];
  counts: Record<string, number>;
};

export type ComparisonFinding = {
  controlId: string;
  previous: HostedFinding | null;
  current: HostedFinding | null;
  change: "NEW" | "REMOVED" | "UNCHANGED" | "CHANGED";
};
