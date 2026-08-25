"""Conditional Access control handlers."""

from typing import Any

from ..models import HandlerResult, Verdict
from .registry import register


def _has_mfa(policy: dict[str, Any]) -> bool:
    grants = policy.get("grantControls")
    return isinstance(grants, dict) and "mfa" in grants.get("builtInControls", [])


def _all_users(policy: dict[str, Any]) -> bool:
    conditions = policy.get("conditions")
    if not isinstance(conditions, dict):
        return False
    users = conditions.get("users")
    return isinstance(users, dict) and "All" in users.get("includeUsers", [])


def _all_apps(policy: dict[str, Any]) -> bool:
    conditions = policy.get("conditions")
    if not isinstance(conditions, dict):
        return False
    applications = conditions.get("applications")
    return isinstance(applications, dict) and "All" in applications.get("includeApplications", [])


@register("ca_mfa_all_users")
def ca_mfa_all_users(
    results: dict[str, list[dict[str, Any]]], params: dict[str, object]
) -> HandlerResult:
    """Evaluate whether an enabled CA policy requires MFA for every user and app."""
    policies = results["policies"]
    enabled_mfa = [
        policy
        for policy in policies
        if policy.get("state") == "enabled" and _has_mfa(policy)
    ]
    require_all_apps = params.get("require_all_apps") is True

    covered = [
        policy
        for policy in enabled_mfa
        if _all_users(policy) and (not require_all_apps or _all_apps(policy))
    ]
    if covered:
        return HandlerResult(
            verdict=Verdict.PASS,
            rationale=(
                "An enabled Conditional Access policy requires MFA for all users and all apps."
            ),
            raw_evidence={"policies": policies},
        )
    has_partial_coverage = any(
        _all_users(policy) or (require_all_apps and _all_apps(policy))
        for policy in enabled_mfa
    )
    if has_partial_coverage:
        return HandlerResult(
            verdict=Verdict.PARTIAL,
            rationale=(
                "MFA is enforced by Conditional Access, but no enabled policy covers both all "
                "users and all required apps."
            ),
            raw_evidence={"policies": policies},
        )
    return HandlerResult(
        verdict=Verdict.FAIL,
        rationale="No enabled Conditional Access policy requires MFA for all users.",
        raw_evidence={"policies": policies},
    )
