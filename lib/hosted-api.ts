import { ComparisonFinding, HostedFinding, HostedRun, ScopingDeclaration, SectorOption, TenantProfile, TenantStatus } from "@/lib/types";

/** Why a hosted call failed, so the interface can say something more useful than "try again". */
export type HostedApiFailure = "unconfigured" | "unreachable" | "rejected";

export class HostedApiError extends Error {
  constructor(message: string, readonly kind: HostedApiFailure, readonly status?: number) {
    super(message);
  }
}

function getHostedApiConfig() {
  const baseUrl = process.env.NIS2CHECK_API_URL?.replace(/\/$/, "");
  const apiKey = process.env.NIS2CHECK_API_KEY;
  if (!baseUrl || !apiKey) {
    throw new HostedApiError("NIS2CHECK_API_URL and NIS2CHECK_API_KEY are not both set on this deployment.", "unconfigured");
  }
  return { baseUrl, apiKey };
}

async function request<T>(path: string, tenantId?: string, init?: RequestInit): Promise<T> {
  const { baseUrl, apiKey } = getHostedApiConfig();
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        ...init?.headers,
        "X-Nis2check-Api-Key": apiKey,
        ...(tenantId ? { "X-Nis2check-Tenant-Id": tenantId } : {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new HostedApiError("The collection service did not answer.", "unreachable");
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof payload?.detail === "string" ? payload.detail : `Hosted collection service returned ${response.status}.`;
    throw new HostedApiError(detail, "rejected", response.status);
  }
  return response.json() as Promise<T>;
}

export async function getTenantStatus(tenantId: string): Promise<TenantStatus> {
  return request<TenantStatus>(`/v1/tenants/${encodeURIComponent(tenantId)}`);
}

export async function completeTenantOnboarding(tenantId: string): Promise<TenantStatus> {
  return request<TenantStatus>(`/v1/tenants/${encodeURIComponent(tenantId)}/consent`, undefined, { method: "POST" });
}

export async function getRuns(tenantId: string): Promise<HostedRun[]> {
  return (await request<{ runs: HostedRun[] }>("/v1/runs", tenantId)).runs;
}

export async function getRun(tenantId: string, runId: string): Promise<HostedRun> {
  return request<HostedRun>(`/v1/runs/${encodeURIComponent(runId)}`, tenantId);
}

export async function getFindings(tenantId: string, runId: string): Promise<HostedFinding[]> {
  return (await request<{ findings: HostedFinding[] }>(`/v1/runs/${encodeURIComponent(runId)}/findings`, tenantId)).findings;
}

export async function getComparison(tenantId: string, leftRunId: string, rightRunId: string): Promise<ComparisonFinding[]> {
  return (await request<{ findings: ComparisonFinding[] }>(`/v1/runs/${encodeURIComponent(leftRunId)}/compare/${encodeURIComponent(rightRunId)}`, tenantId)).findings;
}

export async function startHostedRun(tenantId: string): Promise<HostedRun> {
  return request<HostedRun>("/v1/runs", tenantId, { method: "POST" });
}

export async function getSectors(): Promise<SectorOption[]> {
  return (await request<{ sectors: SectorOption[] }>("/v1/sectors")).sectors;
}

export async function getTenantProfile(tenantId: string): Promise<TenantProfile> {
  return request<TenantProfile>("/v1/profile", tenantId);
}

export async function saveTenantProfile(tenantId: string, declared: Partial<ScopingDeclaration>): Promise<TenantProfile> {
  return request<TenantProfile>("/v1/profile", tenantId, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sector_key: declared.sectorKey,
      employees: declared.employees ?? null,
      annual_turnover_eur: declared.annualTurnoverEur ?? null,
      balance_sheet_total_eur: declared.balanceSheetTotalEur ?? null,
      sole_provider: declared.soleProvider ?? false,
      critical_entity_cer: declared.criticalEntityCer ?? false,
      designated_as: declared.designatedAs ?? null,
    }),
  });
}

/**
 * The dossier is a file, not JSON, so this returns the raw response for the route to stream on.
 * Both formats are rendered server-side and work on every runtime the API runs on.
 */
export async function fetchDossier(tenantId: string, runId: string, format: "pdf" | "html"): Promise<Response> {
  const { baseUrl, apiKey } = getHostedApiConfig();
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/v1/runs/${encodeURIComponent(runId)}/dossier?format=${format}`, {
      headers: { "X-Nis2check-Api-Key": apiKey, "X-Nis2check-Tenant-Id": tenantId },
      cache: "no-store",
    });
  } catch {
    throw new HostedApiError("The collection service did not answer.", "unreachable");
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof payload?.detail === "string" ? payload.detail : `The dossier could not be built (${response.status}).`;
    throw new HostedApiError(detail, "rejected", response.status);
  }
  return response;
}

export async function startScheduledRuns(): Promise<{ started: number; skipped: number; failed: number }> {
  return request<{ started: number; skipped: number; failed: number }>("/v1/scheduled-runs", undefined, { method: "POST" });
}
