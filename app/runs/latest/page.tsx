import { AppShell } from "@/components/app-shell";
import { ServiceUnavailable } from "@/components/service-unavailable";
import { RunDetail } from "@/components/run-detail";
import { TenantOnboarding } from "@/components/tenant-onboarding";
import { getFindings, getRuns, getTenantStatus } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function LatestRun({ searchParams }: { searchParams: Promise<{ onboarding?: string }> }) {
  const session = await requireSession();
  const { onboarding } = await searchParams;
  try {
    const tenant = await getTenantStatus(session.tenantId);
    if (!tenant.consentGranted) return <AppShell><TenantOnboarding failed={onboarding === "failed"} /></AppShell>;
    const runs = await getRuns(session.tenantId);
    const [latest] = runs;
    const findings = latest ? await getFindings(session.tenantId, latest.id) : [];
    return <AppShell><RunDetail run={latest || null} findings={findings} runs={runs} /></AppShell>;
  } catch (error) {
    return <AppShell><ServiceUnavailable error={error} /></AppShell>;
  }
}
