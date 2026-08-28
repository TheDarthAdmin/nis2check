"""Verdict paths of the tenant-default, third-party access and privileged-role controls."""

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from nis2check_catalog import ControlDefinition, load_control
from nis2check_collector.engine import CollectorEngine
from nis2check_collector.graph import AsyncGraphClient
from nis2check_collector.models import Finding, Verdict

CONTROLS = Path("packages/catalog/controls")
BASE = "https://graph.microsoft.com"
GLOBAL_ADMINISTRATOR = "62e90394-69f5-4237-9190-012177145e10"
RESTRICTED_GUEST = "2af84b1e-32c8-42b7-82bc-daa82404023b"
GUEST = "10dae51f-b6af-4016-8d66-8c2a99b929b3"
MEMBER = "a0b1b346-4d3e-4e8b-98f8-753987be4970"


def control(control_id: str) -> ControlDefinition:
    return load_control(CONTROLS / f"{control_id}.yaml")


def path_of(definition: ControlDefinition, name: str) -> str:
    return definition.queries[name].endpoint.split("?")[0]


async def evaluate(definition: ControlDefinition, payloads: dict[str, Any]) -> Finding:
    # Longest path first: C25 queries a service principal and a collection beneath it, and a
    # prefix route registered first would answer both.
    for name in sorted(definition.queries, key=lambda item: len(path_of(definition, item)), reverse=True):
        respx.get(url__startswith=BASE + path_of(definition, name)).respond(200, json=payloads[name])
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [definition])
    return run.findings[0]


def authorization(**properties: Any) -> dict[str, Any]:
    return {"id": "authorizationPolicy", **properties}


def permissions(apps: bool = False, tenants: bool = False, groups: bool = False) -> dict[str, Any]:
    return authorization(
        defaultUserRolePermissions={
            "allowedToCreateApps": apps,
            "allowedToCreateTenants": tenants,
            "allowedToCreateSecurityGroups": groups,
        }
    )


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (permissions(), Verdict.PASS),
        (permissions(apps=True), Verdict.PARTIAL),
        (permissions(apps=True, tenants=True), Verdict.FAIL),
        (authorization(), Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c23_default_user_permissions(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C23"), {"authorization": payload})).verdict is expected


@respx.mock
async def test_c23_mentions_security_group_creation() -> None:
    finding = await evaluate(control("C23"), {"authorization": permissions(groups=True)})

    assert "security groups" in finding.rationale


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (RESTRICTED_GUEST, Verdict.PASS),
        (GUEST, Verdict.PARTIAL),
        (MEMBER, Verdict.FAIL),
        ("00000000-0000-0000-0000-000000000000", Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c24_guest_directory_access(role: str, expected: Verdict) -> None:
    payload = authorization(guestUserRoleId=role)

    assert (await evaluate(control("C24"), {"authorization": payload})).verdict is expected


GRAPH_ROLES = {
    "id": "graph-sp",
    "appRoles": [
        {"id": "role-escalation", "value": "RoleManagement.ReadWrite.Directory"},
        {"id": "role-high", "value": "Mail.ReadWrite"},
        {"id": "role-read", "value": "User.Read.All"},
    ],
}


def assignment(role_id: str, principal_type: str = "ServicePrincipal") -> dict[str, Any]:
    return {"appRoleId": role_id, "principalId": f"sp-{role_id}", "principalType": principal_type}


@pytest.mark.parametrize(
    ("assignments", "expected"),
    [
        ([], Verdict.PASS),
        ([assignment("role-read")], Verdict.PASS),
        ([assignment("role-high")], Verdict.PARTIAL),
        ([assignment("role-escalation")], Verdict.FAIL),
        ([assignment("role-escalation", principal_type="User")], Verdict.PASS),
    ],
)
@respx.mock
async def test_c25_application_graph_permissions(assignments: list[dict[str, Any]], expected: Verdict) -> None:
    payloads = {"graph_app": GRAPH_ROLES, "assignments": {"value": assignments}}

    assert (await evaluate(control("C25"), payloads)).verdict is expected


@respx.mock
async def test_c25_cannot_resolve_permissions_without_the_graph_app_roles() -> None:
    payloads = {"graph_app": {"id": "graph-sp"}, "assignments": {"value": []}}

    assert (await evaluate(control("C25"), payloads)).verdict is Verdict.INCONCLUSIVE


def relationship(status: str = "active", roles: list[str] | None = None, auto_extend: str = "PT0S") -> dict[str, Any]:
    return {
        "id": "relationship-1",
        "status": status,
        "autoExtendDuration": auto_extend,
        "accessDetails": {"unifiedRoles": [{"roleDefinitionId": role} for role in (roles or ["29232cdf-9323-42fd-ade2-1d097af3e4de"])]},
    }


@pytest.mark.parametrize(
    ("relationships", "expected"),
    [
        ([], Verdict.PASS),
        ([relationship(status="terminated")], Verdict.PASS),
        ([relationship()], Verdict.PARTIAL),
        ([relationship(auto_extend="P180D")], Verdict.FAIL),
        ([relationship(roles=[GLOBAL_ADMINISTRATOR])], Verdict.FAIL),
    ],
)
@respx.mock
async def test_c26_delegated_admin_relationships(relationships: list[dict[str, Any]], expected: Verdict) -> None:
    assert (await evaluate(control("C26"), {"relationships": {"value": relationships}})).verdict is expected


def activation(rules: list[str], approval: bool) -> dict[str, Any]:
    target = {"caller": "EndUser", "level": "Assignment"}
    return {
        "value": [
            {
                "roleDefinitionId": GLOBAL_ADMINISTRATOR,
                "policy": {
                    "rules": [
                        {"@odata.type": "#microsoft.graph.unifiedRoleManagementPolicyEnablementRule", "id": "Enablement_EndUser_Assignment", "enabledRules": rules, "target": target},
                        {"@odata.type": "#microsoft.graph.unifiedRoleManagementPolicyApprovalRule", "id": "Approval_EndUser_Assignment", "setting": {"isApprovalRequired": approval}, "target": target},
                        {"@odata.type": "#microsoft.graph.unifiedRoleManagementPolicyEnablementRule", "id": "Enablement_Admin_Eligibility", "enabledRules": [], "target": {"caller": "Admin", "level": "Eligibility"}},
                    ]
                },
            }
        ]
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (activation(["MultiFactorAuthentication", "Justification"], approval=True), Verdict.PASS),
        (activation(["MultiFactorAuthentication", "Justification"], approval=False), Verdict.PARTIAL),
        (activation(["MultiFactorAuthentication"], approval=False), Verdict.PARTIAL),
        (activation([], approval=False), Verdict.FAIL),
        ({"value": []}, Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c27_privileged_activation_controls(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C27"), {"assignments": payload})).verdict is expected


def risk_policy(state: str = "enabled", condition: str = "userRiskLevels", levels: list[str] | None = None, grant: bool = True) -> dict[str, Any]:
    return {
        "id": "policy-1",
        "state": state,
        "conditions": {condition: levels if levels is not None else ["high"]},
        "grantControls": {"builtInControls": ["mfa"]} if grant else {},
    }


@pytest.mark.parametrize(
    ("policies", "expected"),
    [
        ([risk_policy()], Verdict.PASS),
        ([risk_policy(condition="signInRiskLevels")], Verdict.PASS),
        ([risk_policy(state="enabledForReportingButNotEnforced")], Verdict.PARTIAL),
        ([risk_policy(levels=[])], Verdict.FAIL),
        ([risk_policy(grant=False)], Verdict.FAIL),
        ([], Verdict.FAIL),
    ],
)
@respx.mock
async def test_c28_risk_based_conditional_access(policies: list[dict[str, Any]], expected: Verdict) -> None:
    assert (await evaluate(control("C28"), {"policies": {"value": policies}})).verdict is expected


@pytest.mark.parametrize("control_id", ["C23", "C24", "C25", "C26", "C27", "C28"])
@respx.mock
async def test_new_controls_fail_to_inconclusive_on_denial(control_id: str) -> None:
    definition = control(control_id)
    for name in sorted(definition.queries, key=lambda item: len(path_of(definition, item)), reverse=True):
        respx.get(url__startswith=BASE + path_of(definition, name)).respond(403, json={"error": {"message": "Access denied"}})
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [definition])

    assert run.findings[0].verdict is Verdict.INCONCLUSIVE
    assert "HTTP 403" in run.findings[0].rationale
