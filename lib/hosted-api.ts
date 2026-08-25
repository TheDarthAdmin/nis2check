import { ComparisonFinding, HostedFinding, HostedRun } from "@/lib/types";

class HostedApiError extends Error {}

function getHostedApiConfig() {
  const baseUrl = process.env.NIS2CHECK_API_URL?.replace(/\/$/, "");
  const apiKey = process.env.NIS2CHECK_API_KEY;
  if (!baseUrl || !apiKey) {
    throw new HostedApiError("The hosted collection service has not been configured.");
  }
  return { baseUrl, apiKey };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { baseUrl, apiKey } = getHostedApiConfig();
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { ...init?.headers, "X-Nis2check-Api-Key": apiKey },
    cache: "no-store",
  });
  if (!response.ok) throw new HostedApiError(`Hosted collection service returned ${response.status}.`);
  return response.json() as Promise<T>;
}

export async function getRuns(): Promise<HostedRun[]> {
  return (await request<{ runs: HostedRun[] }>("/v1/runs")).runs;
}

export async function getRun(runId: string): Promise<HostedRun> {
  return request<HostedRun>(`/v1/runs/${encodeURIComponent(runId)}`);
}

export async function getFindings(runId: string): Promise<HostedFinding[]> {
  return (await request<{ findings: HostedFinding[] }>(`/v1/runs/${encodeURIComponent(runId)}/findings`)).findings;
}

export async function getComparison(leftRunId: string, rightRunId: string): Promise<ComparisonFinding[]> {
  return (await request<{ findings: ComparisonFinding[] }>(`/v1/runs/${encodeURIComponent(leftRunId)}/compare/${encodeURIComponent(rightRunId)}`)).findings;
}

export async function startHostedRun(source: "manual" | "scheduled" = "manual"): Promise<HostedRun> {
  return request<HostedRun>(`/v1/runs?source=${source}`, { method: "POST" });
}

export { HostedApiError };
