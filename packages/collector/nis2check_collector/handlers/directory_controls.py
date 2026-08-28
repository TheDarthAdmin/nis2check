"""Evaluators for tenant defaults, third-party access and privileged-role governance.

They read what the directory grants by default, who outside the organisation holds standing
access, and what a privileged role actually demands before it can be used.
"""

from typing import Any

from ..models import HandlerResult, Verdict
from .registry import register
from .support import Results, result, single_object, string_list_param, unreadable

#: Documented role template IDs for the directory role a guest receives.
GUEST_ROLES = {
    "2af84b1e-32c8-42b7-82bc-daa82404023b": ("restricted guest", Verdict.PASS),
    "10dae51f-b6af-4016-8d66-8c2a99b929b3": ("guest", Verdict.PARTIAL),
    "a0b1b346-4d3e-4e8b-98f8-753987be4970": ("the same as a member", Verdict.FAIL),
}
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
NO_AUTO_EXTEND = "PT0S"


@register("default_user_permissions")
def default_user_permissions(results: Results, _: dict[str, object]) -> HandlerResult:
    """C23 — what every member of the directory may do without being granted a role."""
    policy = single_object(results, "authorization")
    permissions = policy.get("defaultUserRolePermissions") if policy else None
    if not isinstance(permissions, dict):
        return unreadable("The authorization policy returned no defaultUserRolePermissions.", results)
    allowed = [
        label
        for key, label in (("allowedToCreateApps", "register applications"), ("allowedToCreateTenants", "create tenants"))
        if permissions.get(key) is True
    ]
    groups = " Members may also create security groups." if permissions.get("allowedToCreateSecurityGroups") is True else ""
    if not allowed:
        return result(Verdict.PASS, f"Members cannot register applications or create tenants.{groups}", results)
    if len(allowed) == 1:
        return result(Verdict.PARTIAL, f"Every member of the directory may {allowed[0]}.{groups}", results)
    return result(Verdict.FAIL, f"Every member of the directory may {' and '.join(allowed)}.{groups}", results)


@register("guest_directory_access")
def guest_directory_access(results: Results, _: dict[str, object]) -> HandlerResult:
    """C24 — how much of the directory a guest account can read."""
    policy = single_object(results, "authorization")
    role = str(policy.get("guestUserRoleId", "")).lower() if policy else ""
    if role not in GUEST_ROLES:
        return unreadable(f"The authorization policy reported an unrecognised guestUserRoleId '{role}'.", results)
    label, verdict = GUEST_ROLES[role]
    return result(verdict, f"Guest accounts get directory access {label}.", results)


@register("application_graph_permissions")
def application_graph_permissions(results: Results, params: dict[str, object]) -> HandlerResult:
    """C25 — which applications hold Microsoft Graph permissions of their own."""
    graph_app = single_object(results, "graph_app")
    roles = graph_app.get("appRoles") if graph_app else None
    if not isinstance(roles, list):
        return unreadable("The Microsoft Graph service principal returned no appRoles, so permission IDs could not be resolved.", results)
    names = {str(role.get("id")): str(role.get("value")) for role in roles if isinstance(role, dict)}
    escalation = set(string_list_param(params, "escalation", []))
    high = set(string_list_param(params, "high", []))
    granted_escalation: set[str] = set()
    granted_high: set[str] = set()
    applications: set[str] = set()
    for assignment in results["assignments"]:
        if assignment.get("principalType") != "ServicePrincipal":
            continue
        permission = names.get(str(assignment.get("appRoleId")))
        if permission in escalation:
            granted_escalation.add(permission)
            applications.add(str(assignment.get("principalId")))
        elif permission in high:
            granted_high.add(permission)
            applications.add(str(assignment.get("principalId")))
    if granted_escalation:
        return result(Verdict.FAIL, f"{len(applications)} application(s) hold Graph permissions that can grant further privilege: {', '.join(sorted(granted_escalation))}.", results)
    if granted_high:
        return result(Verdict.PARTIAL, f"{len(applications)} application(s) hold high-privilege Graph write permissions: {', '.join(sorted(granted_high))}.", results)
    return result(Verdict.PASS, "No application holds one of the listed high-privilege Microsoft Graph permissions.", results)


@register("delegated_admin_relationships")
def delegated_admin_relationships(results: Results, params: dict[str, object]) -> HandlerResult:
    """C26 — partners holding delegated administrative access to this tenant."""
    global_administrator = str(params.get("global_administrator_role", "")).lower()
    active = [item for item in results["relationships"] if str(item.get("status", "")).lower() == "active"]
    if not active:
        return result(Verdict.PASS, "No partner holds an active delegated administrative relationship.", results)
    privileged = [item for item in active if global_administrator in _role_ids(item)]
    extending = [item for item in active if str(item.get("autoExtendDuration", NO_AUTO_EXTEND)) not in ("", NO_AUTO_EXTEND)]
    if privileged:
        return result(Verdict.FAIL, f"{len(privileged)} of {len(active)} active partner relationship(s) include the Global Administrator role.", results)
    if extending:
        return result(Verdict.FAIL, f"{len(extending)} of {len(active)} active partner relationship(s) extend themselves automatically, so they never come back for a decision.", results)
    return result(Verdict.PARTIAL, f"{len(active)} active partner relationship(s) hold delegated administrative access; each one needs a periodic review.", results)


@register("privileged_activation_controls")
def privileged_activation_controls(results: Results, _: dict[str, object]) -> HandlerResult:
    """C27 — what the Global Administrator role demands before it can be activated."""
    assignments = results["assignments"]
    rules = _activation_rules(assignments[0]) if assignments else None
    if rules is None:
        return unreadable("No Privileged Identity Management activation policy was returned for the Global Administrator role.", results)
    enabled = {str(item).lower() for item in rules.get("enabledRules", [])}
    missing = [
        label
        for key, label in (("multifactorauthentication", "multifactor authentication"), ("justification", "justification"))
        if key not in enabled
    ]
    if not rules.get("isApprovalRequired"):
        missing.append("approval")
    if not missing:
        return result(Verdict.PASS, "Activating Global Administrator requires multifactor authentication, justification and approval.", results)
    if len(missing) == 3:
        return result(Verdict.FAIL, "Activating Global Administrator requires neither multifactor authentication, justification nor approval.", results)
    return result(Verdict.PARTIAL, f"Activating Global Administrator does not require {' or '.join(missing)}.", results)


@register("risk_based_conditional_access")
def risk_based_conditional_access(results: Results, _: dict[str, object]) -> HandlerResult:
    """C28 — a detected risk means nothing unless a policy acts on it."""
    acting = [policy for policy in results["policies"] if _acts_on_risk(policy) and policy.get("state") == "enabled"]
    reporting = [policy for policy in results["policies"] if _acts_on_risk(policy) and policy.get("state") == "enabledForReportingButNotEnforced"]
    if acting:
        return result(Verdict.PASS, f"{len(acting)} enabled Conditional Access policy(ies) act on user or sign-in risk.", results)
    if reporting:
        return result(Verdict.PARTIAL, f"{len(reporting)} risk-based Conditional Access policy(ies) exist but run in report-only mode.", results)
    return result(Verdict.FAIL, "No Conditional Access policy responds to a user or sign-in risk level.", results)


def _role_ids(relationship: dict[str, Any]) -> set[str]:
    access = relationship.get("accessDetails")
    roles = access.get("unifiedRoles", []) if isinstance(access, dict) else []
    return {str(role.get("roleDefinitionId", "")).lower() for role in roles if isinstance(role, dict)}


def _activation_rules(assignment: dict[str, Any]) -> dict[str, Any] | None:
    """Merge the end-user activation rules of one role management policy into a flat view."""
    policy = assignment.get("policy")
    rules = policy.get("rules") if isinstance(policy, dict) else None
    if not isinstance(rules, list):
        return None
    merged: dict[str, Any] = {}
    for rule in rules:
        if not isinstance(rule, dict) or not _is_end_user_activation(rule):
            continue
        if "enabledRules" in rule:
            merged["enabledRules"] = rule.get("enabledRules") or []
        setting = rule.get("setting")
        if isinstance(setting, dict) and "isApprovalRequired" in setting:
            merged["isApprovalRequired"] = setting.get("isApprovalRequired")
    return merged or None


def _is_end_user_activation(rule: dict[str, Any]) -> bool:
    target = rule.get("target")
    if not isinstance(target, dict):
        return False
    return str(target.get("caller", "")).lower() == "enduser" and str(target.get("level", "")).lower() == "assignment"


def _acts_on_risk(policy: dict[str, Any]) -> bool:
    conditions = policy.get("conditions")
    if not isinstance(conditions, dict):
        return False
    levels = [
        level
        for key in ("userRiskLevels", "signInRiskLevels")
        for level in (conditions.get(key) or [])
        if str(level).lower() not in ("none", "unknownfuturevalue")
    ]
    grants = policy.get("grantControls")
    return bool(levels) and isinstance(grants, dict) and bool(grants.get("builtInControls") or grants.get("authenticationStrength"))
