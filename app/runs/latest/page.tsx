import { AppShell } from "@/components/app-shell";
import { RunDetail } from "@/components/run-detail";
import { TenantOnboarding } from "@/components/tenant-onboarding";
import { getFindings, getRuns, getTenantStatus, HostedApiError } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function LatestRun({ searchParams }: { searchParams: Promise<{ onboarding?: string }> }) {
  const session = await requireSession();
  const { onboarding } = await searchParams;
  try {
    const tenant = await getTenantStatus(session.tenantId);
    if (!tenant.consentGranted) return <AppShell><TenantOnboarding failed={onboarding === "failed"} /></AppShell>;
    const [latest] = await getRuns(session.tenantId);
    const findings = latest ? await getFindings(session.tenantId, latest.id) : [];
    return <AppShell><RunDetail run={latest || null} findings={findings} /></AppShell>;
  } catch (error) {
    const detail = error instanceof HostedApiError ? "Check the hosted API connection and try again." : "An unexpected error occurred.";
    return <AppShell><section className="empty-state"><div className="eyebrow">Collection service unavailable</div><h1>Evidence cannot be loaded.</h1><p>{detail}</p></section></AppShell>;
  }
}
