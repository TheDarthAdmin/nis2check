/**
 * Controls added after a tenant approved access need permissions that tenant never agreed to.
 * Evidence stays visible; the controls that need the new permissions report INCONCLUSIVE until
 * an administrator approves again.
 */
export function ConsentRenewal({ missing }: { missing: string[] }) {
  return <section className="note consent-renewal" role="status">
    <b>New read-only permissions need an administrator's approval</b>
    <p>Nis2Check now checks controls that read {missing.length === 1 ? "one Microsoft Graph permission" : `${missing.length} Microsoft Graph permissions`} this tenant has not approved yet. Until then, those controls report <b>inconclusive</b> rather than evidence — nothing else changes.</p>
    <ul className="scope-list">{missing.map((scope) => <li key={scope}><code>{scope}</code></li>)}</ul>
    <p className="consent-renewal-actions"><a className="primary-button" href="/api/onboarding/admin-consent">Approve the updated permissions</a></p>
    <p className="muted">All of them are read permissions. Nis2Check never asks for a write permission, and approval has to be given by a tenant administrator.</p>
  </section>;
}
