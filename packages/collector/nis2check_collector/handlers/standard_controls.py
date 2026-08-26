"""Conservative evaluators for the remaining first-release controls.

Each evaluator reports only what its Graph response proves. Missing or malformed data is
allowed to bubble to the engine, which turns it into INCONCLUSIVE evidence.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from ..models import HandlerResult, Verdict
from .registry import register
from .support import integer_param as _integer
from .support import result as _result


def _items(results: dict[str, list[dict[str, Any]]], name: str) -> list[dict[str, Any]]:
    return results[name]


def _ca_block(policy: dict[str, Any]) -> bool:
    grants = policy.get("grantControls", {})
    return policy.get("state") == "enabled" and grants.get("builtInControls") == ["block"]


@register("ca_phishing_resistant_admins")
def ca_phishing_resistant_admins(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    policies = _items(results, "policies")
    protected = [
        policy for policy in policies
        if policy.get("state") == "enabled"
        and (policy.get("grantControls", {}).get("authenticationStrength", {}) or {}).get("id")
        == "00000000-0000-0000-0000-000000000004"
    ]
    verdict = Verdict.PARTIAL if protected else Verdict.FAIL
    return _result(verdict, "A phishing-resistant CA policy was found, but administrator scope cannot be proven." if protected else "No enabled Conditional Access policy uses the phishing-resistant authentication strength.", results)


@register("ca_block_legacy_auth")
def ca_block_legacy_auth(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    legacy = {"exchangeActiveSync", "other"}
    policies = _items(results, "policies")
    matching = [
        policy for policy in policies
        if _ca_block(policy) and legacy.intersection(policy.get("conditions", {}).get("clientAppTypes", []))
    ]
    return _result(Verdict.PASS if matching else Verdict.FAIL, "An enabled CA policy blocks legacy client authentication." if matching else "No enabled CA policy was found that blocks legacy client authentication.", results)


@register("per_user_mfa_remainder")
def per_user_mfa_remainder(results: dict[str, list[dict[str, Any]]], params: dict[str, object]) -> HandlerResult:
    users = _items(results, "users")
    cap = _integer(params, "max_users", 5000)
    if len(users) >= cap:
        return _result(Verdict.INCONCLUSIVE, "The configured per-user MFA inspection cap was reached.", results)
    remnants = [user for user in users if user.get("perUserMfaState") not in (None, "disabled")]
    return _result(Verdict.PASS if not remnants else Verdict.PARTIAL, "No per-user MFA remnants were reported." if not remnants else f"Per-user MFA state remains on {len(remnants)} object(s); migrate these to Conditional Access.", results)


@register("global_admin_count")
def global_admin_count(results: dict[str, list[dict[str, Any]]], params: dict[str, object]) -> HandlerResult:
    standing = _items(results, "standing")
    eligible = _items(results, "eligible")
    maximum = _integer(params, "maximum_standing", 4)
    if len(standing) <= maximum:
        return _result(Verdict.PASS, f"{len(standing)} standing Global Administrator(s); {len(eligible)} eligible PIM assignment(s).", results)
    return _result(Verdict.PARTIAL, f"{len(standing)} standing Global Administrator(s) exceeds the configured maximum of {maximum}; {len(eligible)} eligible PIM assignment(s).", results)


@register("break_glass_exclusions")
def break_glass_exclusions(results: dict[str, list[dict[str, Any]]], params: dict[str, object]) -> HandlerResult:
    minimum = _integer(params, "minimum_accounts", 2)
    excluded = {
        user_id
        for policy in _items(results, "policies")
        for user_id in policy.get("conditions", {}).get("users", {}).get("excludeUsers", [])
    }
    if len(excluded) >= minimum:
        return _result(Verdict.PASS, f"At least {minimum} object IDs are excluded from Conditional Access for emergency access.", results)
    if excluded:
        return _result(Verdict.PARTIAL, "Only one emergency-access object ID is excluded from Conditional Access.", results)
    return _result(Verdict.FAIL, "No excluded emergency-access object IDs were found in Conditional Access policies.", results)


@register("guest_access")
def guest_access(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    policy = _items(results, "authorization")[0]
    invite_setting = policy.get("allowInvitesFrom")
    restricted = {"adminsAndGuestInviters", "none"}
    return _result(Verdict.PASS if invite_setting in restricted else Verdict.PARTIAL, f"Guest invitation setting is '{invite_setting}'.", results)


@register("inactive_accounts")
def inactive_accounts(results: dict[str, list[dict[str, Any]]], params: dict[str, object]) -> HandlerResult:
    threshold = datetime.now(UTC) - timedelta(days=_integer(params, "days", 90))
    inactive = 0
    for user in _items(results, "users"):
        last = user.get("signInActivity", {}).get("lastSignInDateTime")
        if not isinstance(last, str):
            continue
        if datetime.fromisoformat(last.replace("Z", "+00:00")) < threshold and user.get("accountEnabled"):
            inactive += 1
    return _result(Verdict.PASS if inactive == 0 else Verdict.PARTIAL, "No enabled accounts with a recorded sign-in older than the configured threshold." if inactive == 0 else f"{inactive} enabled account(s) have a recorded sign-in older than the configured threshold.", results)


@register("device_encryption")
def device_encryption(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    devices = _items(results, "devices")
    protected = [device for device in devices if device.get("isEncrypted") and device.get("complianceState") == "compliant"]
    if not devices:
        return _result(Verdict.NOT_APPLICABLE, "No managed devices were returned by Intune.", results)
    return _result(Verdict.PASS if len(protected) == len(devices) else Verdict.PARTIAL, f"{len(protected)} of {len(devices)} managed device(s) are encrypted and compliant.", results)


@register("update_rings")
def update_rings(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    rings = _items(results, "rings")
    enforced = [ring for ring in rings if ring.get("deadlineForFeatureUpdatesInDays") is not None]
    return _result(Verdict.PASS if enforced else Verdict.FAIL, "At least one update ring has a feature-update deadline." if enforced else "No update ring with an enforced feature-update deadline was found.", results)


@register("asr_rules")
def asr_rules(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    profiles = _items(results, "profiles")
    block = sum(1 for profile in profiles for value in profile.get("asrRules", {}).values() if value == "block")
    audit = sum(1 for profile in profiles for value in profile.get("asrRules", {}).values() if value == "audit")
    return _result(Verdict.PASS if block else Verdict.PARTIAL if audit else Verdict.FAIL, f"ASR rules: {block} in block mode and {audit} in audit mode.", results)


@register("directory_audit_logs")
def directory_audit_logs(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    return _result(Verdict.PARTIAL, "Directory audit logs are readable through Graph. Unified audit-log availability cannot be verified through Graph, so this control never passes.", results)


@register("security_contact")
def security_contact(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    contacts = _items(results, "organization")[0].get("securityComplianceNotificationMails", [])
    return _result(Verdict.PASS if contacts else Verdict.FAIL, "Security contact address(es) are configured." if contacts else "No security compliance notification address is configured.", results)


@register("high_privilege_apps")
def high_privilege_apps(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    dangerous = {"Directory.ReadWrite.All", "RoleManagement.ReadWrite.Directory", "Application.ReadWrite.All"}
    grants = _items(results, "grants")
    risky = [grant for grant in grants if dangerous.intersection(str(grant.get("scope", "")).split())]
    return _result(Verdict.PASS if not risky else Verdict.PARTIAL, "No delegated high-privilege Graph grants were found." if not risky else f"{len(risky)} high-privilege delegated Graph grant(s) require review.", results)


@register("user_consent")
def user_consent(results: dict[str, list[dict[str, Any]]], _: dict[str, object]) -> HandlerResult:
    policy = _items(results, "authorization")[0]
    assigned = policy.get("defaultUserRolePermissions", {}).get("permissionGrantPoliciesAssigned", [])
    unrestricted = "ManagePermissionGrantsForSelf.microsoft-user-default-legacy" in assigned
    return _result(Verdict.FAIL if unrestricted else Verdict.PASS, "User consent is limited by assigned permission-grant policies." if not unrestricted else "The legacy unrestricted user-consent policy is assigned.", results)
