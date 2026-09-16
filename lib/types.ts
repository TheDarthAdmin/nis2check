export type Verdict = "PASS" | "PARTIAL" | "FAIL" | "NOT_APPLICABLE" | "INCONCLUSIVE";

/** Scoping answers a different question than a verdict does, so it has its own outcomes. */
export type Classification = "ESSENTIAL" | "IMPORTANT" | "OUT_OF_SCOPE" | "UNDETERMINED";

export type SizeClass = "MICRO" | "SMALL" | "MEDIUM" | "LARGE" | "UNDETERMINED";

export type SectorOption = {
  key: string;
  annex: string;
  annexPoint: string;
  sector: string;
  subsector: string;
};

export type ScopingResult = {
  classification: Classification;
  size: SizeClass;
  /** Whether the directive applies at all. null when the declared figures do not settle it. */
  inScope: boolean | null;
  rationale: string;
  legalBasis: string[];
  supervision: string[];
  sector: SectorOption | null;
};

/** What the organisation declared about itself. Never collected, never read from Graph. */
export type ScopingDeclaration = {
  sectorKey: string;
  employees: number | null;
  annualTurnoverEur: number | null;
  balanceSheetTotalEur: number | null;
  soleProvider: boolean;
  criticalEntityCer: boolean;
  designatedAs: Classification | null;
  updatedAt: string | null;
};

export type TenantProfile = { declared: ScopingDeclaration | null; scoping: ScopingResult | null };

export type TenantStatus = {
  tenantId: string;
  consentGranted: boolean;
  consentedAt: string | null;
  /** Graph permissions the current catalogue needs, what this tenant approved, and the gap. */
  requiredScopes: string[];
  consentedScopes: string[];
  missingScopes: string[];
  consentCurrent: boolean;
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
  remediationSteps: string[];
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
