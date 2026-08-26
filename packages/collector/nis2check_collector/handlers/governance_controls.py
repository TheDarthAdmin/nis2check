"""Evaluators for risk, continuity, maintenance, governance and cryptography controls.

These cover the NIS2 article 21(2) points that identity and device controls do not reach:
(a) risk analysis, (c) continuity, (e) maintenance and vulnerability handling,
(f) assessing the effectiveness of the measures, and (h) cryptography.
"""

from datetime import UTC, datetime
from typing import Any

from ..models import HandlerResult, Verdict
from .registry import register
from .support import (
    Results,
    integer_param,
    result,
    single_object,
    string_list_param,
    timestamp,
    unreadable,
)

SHARING_STRICT = {"disabled", "existingExternalUserSharingOnly"}
SHARING_AUTHENTICATED = {"externalUserSharingOnly"}
SHARING_ANONYMOUS = {"externalUserAndGuestSharing"}


@register("risky_users")
def risky_users(results: Results, params: dict[str, object]) -> HandlerResult:
    """C16 — users Entra ID Protection still considers at risk have not been dealt with."""
    users = results["risky"]
    cap = integer_param(params, "max_users", 2000)
    if len(users) >= cap:
        return unreadable(f"The inspection cap of {cap} risk records was reached, so the tenant was not read completely.", results)
    at_risk = [user for user in users if user.get("riskState") == "atRisk"]
    high = [user for user in at_risk if user.get("riskLevel") == "high"]
    if not at_risk:
        return result(Verdict.PASS, f"No user is left in the at-risk state; {len(users)} risk record(s) were read.", results)
    if high:
        return result(Verdict.FAIL, f"{len(high)} user(s) at high risk and {len(at_risk) - len(high)} at lower risk are still unresolved.", results)
    return result(Verdict.PARTIAL, f"{len(at_risk)} user(s) are still in the at-risk state, none of them at high risk.", results)


@register("onedrive_retention")
def onedrive_retention(results: Results, params: dict[str, object]) -> HandlerResult:
    """C17 — how long a departed user's OneDrive survives the account deletion."""
    settings = single_object(results, "settings")
    days = settings.get("deletedUserPersonalSiteRetentionPeriodInDays") if settings else None
    if not isinstance(days, int):
        return unreadable("The tenant did not return deletedUserPersonalSiteRetentionPeriodInDays, so retention could not be read.", results)
    minimum = integer_param(params, "minimum_days", 90)
    if days >= minimum:
        return result(Verdict.PASS, f"A deleted user's OneDrive is retained for {days} days, at or above the {minimum}-day threshold used here.", results)
    if days > 0:
        return result(Verdict.PARTIAL, f"A deleted user's OneDrive is retained for {days} days, below the {minimum}-day threshold used here.", results)
    return result(Verdict.FAIL, "A deleted user's OneDrive is not retained at all.", results)


@register("application_credentials")
def application_credentials(results: Results, params: dict[str, object]) -> HandlerResult:
    """C18 — expired or long-lived application secrets show credentials are not maintained."""
    applications = results["applications"]
    if not applications:
        return result(Verdict.NOT_APPLICABLE, "This tenant owns no application registrations.", results)
    maximum = integer_param(params, "max_lifetime_days", 365)
    now = datetime.now(UTC)
    total = expired = long_lived = 0
    for application in applications:
        for credential in _credentials(application):
            end = timestamp(credential.get("endDateTime"))
            if end is None:
                continue
            total += 1
            start = timestamp(credential.get("startDateTime"))
            if end < now:
                expired += 1
            elif start is not None and (end - start).days > maximum:
                long_lived += 1
    if total == 0:
        return result(Verdict.PASS, f"None of the {len(applications)} application registration(s) carries a secret or certificate with an expiry date.", results)
    if long_lived:
        return result(Verdict.FAIL, f"{long_lived} of {total} credential(s) are valid for longer than {maximum} days; {expired} have already expired.", results)
    if expired:
        return result(Verdict.PARTIAL, f"{expired} of {total} credential(s) have expired and were left on the registration.", results)
    return result(Verdict.PASS, f"All {total} application credential(s) are current and valid for at most {maximum} days.", results)


@register("privileged_access_reviews")
def privileged_access_reviews(results: Results, _: dict[str, object]) -> HandlerResult:
    """C19 — an access review that actually covers privileged roles, not only groups."""
    definitions = results["definitions"]
    privileged = [item for item in definitions if _reviews_privileged_access(item)]
    if privileged:
        return result(Verdict.PASS, f"{len(privileged)} of {len(definitions)} access review(s) are scoped to privileged role assignments.", results)
    if definitions:
        return result(Verdict.PARTIAL, f"{len(definitions)} access review(s) exist, none of them scoped to privileged role assignments.", results)
    return result(Verdict.FAIL, "No access review is defined in this tenant.", results)


@register("weak_authentication_methods")
def weak_authentication_methods(results: Results, params: dict[str, object]) -> HandlerResult:
    """C20 — phone and email one-time codes are still an accepted factor."""
    policy = single_object(results, "methods")
    configurations = policy.get("authenticationMethodConfigurations") if policy else None
    if not isinstance(configurations, list):
        return unreadable("The authentication methods policy returned no authenticationMethodConfigurations.", results)
    states = {str(item.get("id")): str(item.get("state")) for item in configurations if isinstance(item, dict)}
    weak = [name for name in string_list_param(params, "weak", ["Sms", "Voice", "Email"]) if states.get(name) == "enabled"]
    strong = [name for name in string_list_param(params, "strong", ["Fido2", "X509Certificate"]) if states.get(name) == "enabled"]
    if weak:
        return result(Verdict.FAIL, f"Weak authentication method(s) are enabled tenant-wide: {', '.join(weak)}.", results)
    if not strong:
        return result(Verdict.PARTIAL, "No weak method is enabled, but no phishing-resistant method (FIDO2 or certificate-based) is enabled either.", results)
    return result(Verdict.PASS, f"Weak methods are disabled and phishing-resistant method(s) are enabled: {', '.join(strong)}.", results)


@register("sharepoint_legacy_auth")
def sharepoint_legacy_auth(results: Results, _: dict[str, object]) -> HandlerResult:
    """C21 — SharePoint and OneDrive still accept clients without modern authentication."""
    settings = single_object(results, "settings")
    enabled = settings.get("isLegacyAuthProtocolsEnabled") if settings else None
    if not isinstance(enabled, bool):
        return unreadable("The tenant did not return isLegacyAuthProtocolsEnabled, so the setting could not be read.", results)
    if enabled:
        return result(Verdict.FAIL, "SharePoint and OneDrive still accept apps that do not use modern authentication.", results)
    return result(Verdict.PASS, "Apps that do not use modern authentication are blocked for SharePoint and OneDrive.", results)


@register("external_sharing")
def external_sharing(results: Results, _: dict[str, object]) -> HandlerResult:
    """C22 — how far tenant content can travel outside the organisation."""
    settings = single_object(results, "settings")
    capability = settings.get("sharingCapability") if settings else None
    if not isinstance(capability, str):
        return unreadable("The tenant did not return sharingCapability, so the sharing level could not be read.", results)
    resharing = " External users may reshare what they receive." if settings and settings.get("isResharingByExternalUsersEnabled") is True else ""
    if capability in SHARING_STRICT:
        return result(Verdict.PASS, f"Tenant sharing level is '{capability}': content cannot be shared with new external people.{resharing}", results)
    if capability in SHARING_AUTHENTICATED:
        return result(Verdict.PARTIAL, f"Tenant sharing level is '{capability}': every external person must authenticate, but any of them can be invited.{resharing}", results)
    if capability in SHARING_ANONYMOUS:
        return result(Verdict.FAIL, f"Tenant sharing level is '{capability}': anonymous 'Anyone' links are allowed.{resharing}", results)
    return unreadable(f"The tenant reported an unrecognised sharing level '{capability}'.", results)


def _credentials(application: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for key in ("passwordCredentials", "keyCredentials"):
        value = application.get(key)
        if isinstance(value, list):
            found.extend(item for item in value if isinstance(item, dict))
    return found


def _reviews_privileged_access(definition: dict[str, Any]) -> bool:
    scope = definition.get("scope")
    query = str(scope.get("query", "")) if isinstance(scope, dict) else ""
    return "rolemanagement" in query.lower() or "roleassignmentschedule" in query.lower()
