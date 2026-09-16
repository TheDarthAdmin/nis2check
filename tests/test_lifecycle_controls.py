"""Verdict paths of the identity lifecycle controls C29, C30 and C31.

Every case runs through the real catalogue entry and the engine, so the YAML query wiring is
covered as well as the handler. All data is fixture data; no record carries a name or a UPN.
"""

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


async def evaluate(definition: ControlDefinition, *values: dict[str, Any]) -> Finding:
    for query in definition.queries.values():
        respx.get(url__startswith=BASE + query.endpoint.split("?")[0]).respond(
            200, json={"value": list(values)}
        )
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [definition])
    return run.findings[0]


def workflow(category: str = "leaver", enabled: bool = True, scheduled: bool = True) -> dict[str, Any]:
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "category": category,
        "isEnabled": enabled,
        "isSchedulingEnabled": scheduled,
    }


def registration(capable: bool = True, admin: bool = False) -> dict[str, Any]:
    return {"id": "00000000-0000-0000-0000-000000000002", "isMfaCapable": capable, "isAdmin": admin}


def domain(authentication: str = "Managed", verified: bool = True) -> dict[str, Any]:
    return {"id": "fixture.example", "authenticationType": authentication, "isVerified": verified}


@pytest.mark.parametrize(
    ("workflows", "expected"),
    [
        pytest.param([workflow()], Verdict.PASS, id="enabled-and-scheduled"),
        pytest.param([], Verdict.FAIL, id="no-workflow-at-all"),
        pytest.param([workflow(category="joiner")], Verdict.FAIL, id="only-a-joiner-workflow"),
        pytest.param([workflow(enabled=False)], Verdict.FAIL, id="leaver-workflow-disabled"),
        pytest.param([workflow(scheduled=False)], Verdict.PARTIAL, id="enabled-but-unscheduled"),
    ],
)
@respx.mock
async def test_c29_leaver_workflows(workflows: list[dict[str, Any]], expected: Verdict) -> None:
    finding = await evaluate(control("C29"), *workflows)

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c29_says_an_unscheduled_workflow_has_to_be_started_by_hand() -> None:
    finding = await evaluate(control("C29"), workflow(scheduled=False))

    assert "started by hand" in finding.rationale


@pytest.mark.parametrize(
    ("registrations", "expected"),
    [
        pytest.param([registration(), registration(admin=True)], Verdict.PASS, id="everyone-registered"),
        pytest.param([registration(), registration(capable=False, admin=True)], Verdict.FAIL, id="administrator-not-registered"),
        pytest.param([registration(capable=False), registration(admin=True)], Verdict.PARTIAL, id="user-not-registered"),
        pytest.param([], Verdict.INCONCLUSIVE, id="empty-report-is-not-a-pass"),
    ],
)
@respx.mock
async def test_c30_mfa_registration_coverage(
    registrations: list[dict[str, Any]], expected: Verdict
) -> None:
    finding = await evaluate(control("C30"), *registrations)

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c30_reports_the_inspection_cap_instead_of_a_partial_answer() -> None:
    definition = control("C30").model_copy(update={"params": {"max_users": 2}})

    finding = await evaluate(definition, registration(), registration())

    assert finding.verdict is Verdict.INCONCLUSIVE
    assert "inspection cap of 2" in finding.rationale


def test_c30_never_asks_graph_for_a_user_principal_name() -> None:
    endpoint = control("C30").queries["registrations"].endpoint

    assert "$select=" in endpoint
    assert "userPrincipalName" not in endpoint
    assert "userDisplayName" not in endpoint


@pytest.mark.parametrize(
    ("domains", "expected"),
    [
        pytest.param([domain(), domain()], Verdict.PASS, id="all-managed"),
        pytest.param([domain(), domain(authentication="Federated")], Verdict.PARTIAL, id="one-federated"),
        pytest.param([domain(authentication="Federated")], Verdict.PARTIAL, id="fully-federated"),
        pytest.param([], Verdict.INCONCLUSIVE, id="no-domains"),
        pytest.param([domain(verified=False)], Verdict.INCONCLUSIVE, id="nothing-verified"),
    ],
)
@respx.mock
async def test_c31_federated_domains(domains: list[dict[str, Any]], expected: Verdict) -> None:
    finding = await evaluate(control("C31"), *domains)

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c31_says_the_rest_of_the_report_does_not_reach_a_federated_domain() -> None:
    finding = await evaluate(control("C31"), domain(authentication="Federated"))

    assert "none of the multifactor or Conditional Access evidence" in finding.rationale


@pytest.mark.parametrize("control_id", ["C29", "C30", "C31"])
@respx.mock
async def test_lifecycle_controls_fail_to_inconclusive_on_denial(control_id: str) -> None:
    respx.get(url__startswith=BASE).respond(403, json={"error": {"message": "Access denied"}})

    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [control(control_id)])

    assert run.findings[0].verdict is Verdict.INCONCLUSIVE
    assert "HTTP 403" in run.findings[0].rationale


@pytest.mark.parametrize("control_id", ["C29", "C30", "C31"])
def test_lifecycle_controls_document_their_limits(control_id: str) -> None:
    definition = control(control_id)

    assert len(definition.limits.strip()) > 40
    assert definition.remediation_steps
