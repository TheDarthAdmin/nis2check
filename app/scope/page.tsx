import { AppShell } from "@/components/app-shell";
import { ScopeForm } from "@/components/scope-form";
import { ScopeSummary } from "@/components/scope-summary";
import { ServiceUnavailable } from "@/components/service-unavailable";
import { getSectors, getTenantProfile } from "@/lib/hosted-api";
import { requireSession } from "@/lib/require-session";

export const dynamic = "force-dynamic";

export default async function Scope() {
  const session = await requireSession();
  try {
    const [sectors, profile] = await Promise.all([getSectors(), getTenantProfile(session.tenantId)]);
    return <AppShell>
      <section className="hero scope-hero">
        <div className="eyebrow">Scope</div>
        <h1>Does NIS2 apply to you?</h1>
        <p>A different question from what your tenant can prove, and the answer does not come from Microsoft Graph. It follows from your sector and your size, under article 2 and article 3 of the directive.</p>
      </section>
      {profile.scoping ? <ScopeSummary scoping={profile.scoping} /> : null}
      <ScopeForm sectors={sectors} declared={profile.declared} />
    </AppShell>;
  } catch (error) {
    return <AppShell><ServiceUnavailable error={error} eyebrow="Scope" /></AppShell>;
  }
}
