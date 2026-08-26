"""Verdict paths of the risk, continuity, maintenance, governance and cryptography controls.

Every case runs through the real catalogue entry and the engine, so the YAML query wiring is
covered as well as the handler.
"""

from datetime import UTC, datetime, timedelta
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


def control(control_id: str) -> ControlDefinition:
    return load_control(CONTROLS / f"{control_id}.yaml")


async def evaluate(definition: ControlDefinition, payload: dict[str, Any]) -> Finding:
    for query in definition.queries.values():
        respx.get(url__startswith=BASE + query.endpoint.split("?")[0]).respond(200, json=payload)
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [definition])
    return run.findings[0]


def settings(**properties: object) -> dict[str, Any]:
    """The `/admin/sharepoint/settings` response shape, which wraps the object in `value`."""
    return {"value": {"@odata.type": "#microsoft.graph.sharepointSettings", **properties}}


def credential(days_valid: int, expired: bool = False) -> dict[str, str]:
    end = datetime.now(UTC) - timedelta(days=1) if expired else datetime.now(UTC) + timedelta(days=30)
    return {"startDateTime": (end - timedelta(days=days_valid)).isoformat(), "endDateTime": end.isoformat()}


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"value": [{"id": "1", "riskState": "remediated", "riskLevel": "high"}]}, Verdict.PASS),
        ({"value": [{"id": "1", "riskState": "atRisk", "riskLevel": "medium"}]}, Verdict.PARTIAL),
        ({"value": [{"id": "1", "riskState": "atRisk", "riskLevel": "high"}]}, Verdict.FAIL),
    ],
)
@respx.mock
async def test_c16_risky_users(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C16"), payload)).verdict is expected


@respx.mock
async def test_c16_reports_the_inspection_cap_instead_of_a_partial_answer() -> None:
    definition = control("C16").model_copy(update={"params": {"max_users": 1}})
    finding = await evaluate(definition, {"value": [{"id": "1", "riskState": "remediated"}]})

    assert finding.verdict is Verdict.INCONCLUSIVE
    assert "cap" in finding.rationale


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (settings(deletedUserPersonalSiteRetentionPeriodInDays=365), Verdict.PASS),
        (settings(deletedUserPersonalSiteRetentionPeriodInDays=30), Verdict.PARTIAL),
        (settings(deletedUserPersonalSiteRetentionPeriodInDays=0), Verdict.FAIL),
        (settings(sharingCapability="disabled"), Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c17_onedrive_retention(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C17"), payload)).verdict is expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"value": []}, Verdict.NOT_APPLICABLE),
        ({"value": [{"id": "a", "passwordCredentials": [], "keyCredentials": []}]}, Verdict.PASS),
        ({"value": [{"id": "a", "passwordCredentials": [credential(180)]}]}, Verdict.PASS),
        ({"value": [{"id": "a", "passwordCredentials": [credential(30, expired=True)]}]}, Verdict.PARTIAL),
        ({"value": [{"id": "a", "keyCredentials": [credential(900)]}]}, Verdict.FAIL),
    ],
)
@respx.mock
async def test_c18_application_credentials(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C18"), payload)).verdict is expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"value": [{"id": "1", "scope": {"query": "/roleManagement/directory/roleAssignmentScheduleInstances"}}]}, Verdict.PASS),
        ({"value": [{"id": "1", "scope": {"query": "/groups/abc/transitiveMembers"}}]}, Verdict.PARTIAL),
        ({"value": []}, Verdict.FAIL),
    ],
)
@respx.mock
async def test_c19_privileged_access_reviews(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C19"), payload)).verdict is expected


def methods(**states: str) -> dict[str, Any]:
    return {
        "id": "authenticationMethodsPolicy",
        "authenticationMethodConfigurations": [
            {"id": name, "state": state} for name, state in states.items()
        ],
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (methods(Sms="disabled", Voice="disabled", Email="disabled", Fido2="enabled"), Verdict.PASS),
        (methods(Sms="disabled", Voice="disabled", Email="disabled", Fido2="disabled"), Verdict.PARTIAL),
        (methods(Sms="enabled", Fido2="enabled"), Verdict.FAIL),
        ({"id": "authenticationMethodsPolicy"}, Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c20_weak_authentication_methods(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C20"), payload)).verdict is expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (settings(isLegacyAuthProtocolsEnabled=False), Verdict.PASS),
        (settings(isLegacyAuthProtocolsEnabled=True), Verdict.FAIL),
        (settings(), Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c21_sharepoint_legacy_auth(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C21"), payload)).verdict is expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (settings(sharingCapability="disabled"), Verdict.PASS),
        (settings(sharingCapability="existingExternalUserSharingOnly"), Verdict.PASS),
        (settings(sharingCapability="externalUserSharingOnly"), Verdict.PARTIAL),
        (settings(sharingCapability="externalUserAndGuestSharing"), Verdict.FAIL),
        (settings(sharingCapability="somethingNew"), Verdict.INCONCLUSIVE),
    ],
)
@respx.mock
async def test_c22_external_sharing(payload: dict[str, Any], expected: Verdict) -> None:
    assert (await evaluate(control("C22"), payload)).verdict is expected


@respx.mock
async def test_c22_mentions_external_resharing_in_the_rationale() -> None:
    finding = await evaluate(
        control("C22"), settings(sharingCapability="disabled", isResharingByExternalUsersEnabled=True)
    )

    assert "reshare" in finding.rationale


@pytest.mark.parametrize("control_id", ["C16", "C17", "C18", "C19", "C20", "C21", "C22"])
@respx.mock
async def test_new_controls_fail_to_inconclusive_on_denial(control_id: str) -> None:
    definition = control(control_id)
    for query in definition.queries.values():
        respx.get(url__startswith=BASE + query.endpoint.split("?")[0]).respond(403, json={"error": {"message": "Access denied"}})
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [definition])

    assert run.findings[0].verdict is Verdict.INCONCLUSIVE
    assert "HTTP 403" in run.findings[0].rationale


@pytest.mark.parametrize("control_id", ["C16", "C17", "C18", "C19", "C20", "C21", "C22"])
def test_new_controls_carry_remediation_guidance(control_id: str) -> None:
    definition = control(control_id)

    assert definition.remediation_steps
    assert definition.limits.strip()
