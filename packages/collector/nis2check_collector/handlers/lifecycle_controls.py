"""Evaluators for what happens to an identity over time.

Where the conditional access handlers read the rules a tenant wrote down, these read the
state those rules were supposed to produce: who was offboarded, who actually registered a
second factor, and where a sign-in is decided at all.
"""

from ..models import HandlerResult, Verdict
from .registry import register
from .support import Results, integer_param, result, string_param, unreadable

#: Statuses of a domain whose authentication this tenant does not decide.
FEDERATED = "Federated"


@register("leaver_workflows")
def leaver_workflows(results: Results, params: dict[str, object]) -> HandlerResult:
    """C29 — an automated offboarding workflow that is both enabled and scheduled."""
    workflows = results["workflows"]
    category = string_param(params, "category", "leaver")
    if not workflows:
        return result(Verdict.FAIL, "No lifecycle workflow is defined, so leaving the organisation revokes nothing automatically.", results)
    leavers = [workflow for workflow in workflows if workflow.get("category") == category]
    if not leavers:
        return result(Verdict.FAIL, f"{len(workflows)} lifecycle workflow(s) exist, none of them in the {category} category.", results)
    enabled = [workflow for workflow in leavers if workflow.get("isEnabled") is True]
    if not enabled:
        return result(Verdict.FAIL, f"All {len(leavers)} {category} workflow(s) are disabled.", results)
    scheduled = [workflow for workflow in enabled if workflow.get("isSchedulingEnabled") is True]
    if not scheduled:
        return result(Verdict.PARTIAL, f"{len(enabled)} of {len(leavers)} {category} workflow(s) are enabled, but none of them is scheduled, so every run has to be started by hand.", results)
    return result(Verdict.PASS, f"{len(scheduled)} of {len(leavers)} {category} workflow(s) are enabled and run on a schedule.", results)


@register("mfa_registration_coverage")
def mfa_registration_coverage(results: Results, params: dict[str, object]) -> HandlerResult:
    """C30 — how many users could actually pass multifactor authentication, not how many should."""
    registrations = results["registrations"]
    if not registrations:
        return unreadable("The authentication methods registration report returned no users, so coverage could not be read.", results)
    cap = integer_param(params, "max_users", 5000)
    if len(registrations) >= cap:
        return unreadable(f"The inspection cap of {cap} registration records was reached, so the tenant was not read completely.", results)
    capable = [record for record in registrations if record.get("isMfaCapable") is True]
    administrators = [record for record in registrations if record.get("isAdmin") is True]
    admin_gap = [record for record in administrators if record.get("isMfaCapable") is not True]
    gap = len(registrations) - len(capable)
    if admin_gap:
        return result(Verdict.FAIL, f"{len(admin_gap)} of {len(administrators)} administrator(s) cannot pass multifactor authentication; {gap} of {len(registrations)} user(s) are unregistered in total.", results)
    if gap:
        return result(Verdict.PARTIAL, f"{gap} of {len(registrations)} user(s) have no registered multifactor method; every one of the {len(administrators)} administrator(s) has.", results)
    return result(Verdict.PASS, f"All {len(registrations)} user(s) have a registered multifactor method.", results)


@register("federated_domains")
def federated_domains(results: Results, _: dict[str, object]) -> HandlerResult:
    """C31 — a federated domain moves the sign-in decision outside everything else measured here."""
    domains = results["domains"]
    if not domains:
        return unreadable("No domain was returned, so the authentication type could not be read.", results)
    verified = [domain for domain in domains if domain.get("isVerified") is True]
    if not verified:
        return unreadable(f"None of the {len(domains)} domain(s) returned is verified, so no authentication type could be established.", results)
    federated = [domain for domain in verified if domain.get("authenticationType") == FEDERATED]
    if not federated:
        return result(Verdict.PASS, f"All {len(verified)} verified domain(s) authenticate in the tenant itself, so the authentication evidence in this report covers them.", results)
    if len(federated) == len(verified):
        return result(Verdict.PARTIAL, f"All {len(verified)} verified domain(s) are federated: an external identity provider decides every sign-in, and none of the multifactor or Conditional Access evidence in this report reaches it.", results)
    return result(Verdict.PARTIAL, f"{len(federated)} of {len(verified)} verified domain(s) are federated; for those, the authentication evidence in this report proves nothing.", results)
