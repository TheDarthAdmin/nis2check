"""Verdict paths of the assurance controls C32 to C36.

These check whether a measure is worked rather than merely configured, so the fixtures aim at
the gap between the two: an ageing incident queue, an unassigned policy, a consent request with
nobody to answer it, a default that admits every tenant, a label that was never published.
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


async def evaluate(definition: ControlDefinition, bodies: dict[str, Any]) -> Finding:
    """Answer each named query of a control with its own response body."""
    for name, query in definition.queries.items():
        respx.get(url__startswith=BASE + query.endpoint.split("?")[0]).respond(
            200, json=bodies[name]
        )
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [definition])
    return run.findings[0]


def collection(*items: dict[str, Any]) -> dict[str, Any]:
    return {"value": list(items)}


def days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


def incident(
    status: str = "resolved",
    classification: str | None = "truePositive",
    updated_days_ago: int = 1,
) -> dict[str, Any]:
    return {
        "id": "fixture-incident",
        "status": status,
        "severity": "medium",
        "classification": classification,
        "createdDateTime": days_ago(updated_days_ago + 1),
        "lastUpdateDateTime": days_ago(updated_days_ago),
    }


def compliance_policy(assigned: bool = True) -> dict[str, Any]:
    return {
        "id": "fixture-policy",
        "assignments": [{"id": "fixture-assignment"}] if assigned else [],
    }


def consent_policy(
    enabled: bool = True, reviewers: int = 1, notify: bool = True
) -> dict[str, Any]:
    return {
        "isEnabled": enabled,
        "notifyReviewers": notify,
        "reviewers": [{"query": "/users/fixture"} for _ in range(reviewers)],
    }


def cross_tenant_default(access: str = "blocked", trust_mfa: bool = False) -> dict[str, Any]:
    return {
        "inboundTrust": {"isMfaAccepted": trust_mfa},
        "b2bCollaborationInbound": {"usersAndGroups": {"accessType": access}},
    }


def retention_label(days: int | None = 730, in_use: bool = True) -> dict[str, Any]:
    duration: dict[str, Any] = (
        {"@odata.type": "#microsoft.graph.security.retentionDurationInDays", "days": days}
        if days is not None
        else {"@odata.type": "#microsoft.graph.security.retentionDurationUnknown"}
    )
    return {"id": "fixture-label", "retentionDuration": duration, "isInUse": in_use}


@pytest.mark.parametrize(
    ("incidents", "expected"),
    [
        pytest.param([incident()], Verdict.PASS, id="closed-with-a-classification"),
        pytest.param([incident(status="active")], Verdict.PASS, id="active-but-recently-worked"),
        pytest.param([incident(status="active", updated_days_ago=90)], Verdict.FAIL, id="active-and-stale"),
        pytest.param([incident(classification=None)], Verdict.PARTIAL, id="closed-without-a-verdict"),
        pytest.param([incident(classification="unknown")], Verdict.PARTIAL, id="closed-as-unknown"),
        pytest.param([], Verdict.INCONCLUSIVE, id="empty-queue-is-not-a-pass"),
    ],
)
@respx.mock
async def test_c32_security_incident_followup(
    incidents: list[dict[str, Any]], expected: Verdict
) -> None:
    finding = await evaluate(control("C32"), {"incidents": collection(*incidents)})

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c32_will_not_call_an_empty_queue_a_pass() -> None:
    finding = await evaluate(control("C32"), {"incidents": collection()})

    assert finding.verdict is Verdict.INCONCLUSIVE
    assert "never deployed" in finding.rationale


@pytest.mark.parametrize(
    ("policies", "expected"),
    [
        pytest.param([compliance_policy()], Verdict.PASS, id="assigned"),
        pytest.param([], Verdict.FAIL, id="no-policy-at-all"),
        pytest.param([compliance_policy(assigned=False)], Verdict.FAIL, id="none-assigned"),
        pytest.param(
            [compliance_policy(), compliance_policy(assigned=False)],
            Verdict.PARTIAL,
            id="some-assigned",
        ),
    ],
)
@respx.mock
async def test_c33_device_compliance_policies(
    policies: list[dict[str, Any]], expected: Verdict
) -> None:
    finding = await evaluate(control("C33"), {"policies": collection(*policies)})

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c33_says_an_unassigned_policy_evaluates_nothing() -> None:
    finding = await evaluate(
        control("C33"), {"policies": collection(compliance_policy(assigned=False))}
    )

    assert "not one of them evaluates a device" in finding.rationale


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        pytest.param(consent_policy(), Verdict.PASS, id="on-with-notified-reviewers"),
        pytest.param(consent_policy(enabled=False), Verdict.FAIL, id="workflow-off"),
        pytest.param(consent_policy(reviewers=0), Verdict.PARTIAL, id="no-reviewer-named"),
        pytest.param(consent_policy(notify=False), Verdict.PARTIAL, id="reviewers-not-notified"),
        pytest.param({}, Verdict.FAIL, id="policy-without-an-enabled-flag"),
    ],
)
@respx.mock
async def test_c34_admin_consent_workflow(policy: dict[str, Any], expected: Verdict) -> None:
    finding = await evaluate(control("C34"), {"policy": policy})

    assert finding.verdict is expected
    assert finding.rationale


@pytest.mark.parametrize(
    ("default_policy", "partners", "expected"),
    [
        pytest.param(cross_tenant_default(), [], Verdict.PASS, id="inbound-blocked"),
        pytest.param(cross_tenant_default(access="allowed"), [], Verdict.FAIL, id="open-and-nobody-named"),
        pytest.param(
            cross_tenant_default(access="allowed"),
            [{"tenantId": "fixture-partner"}],
            Verdict.PARTIAL,
            id="open-but-partners-configured",
        ),
        pytest.param(
            cross_tenant_default(access="allowed", trust_mfa=True),
            [{"tenantId": "fixture-partner"}],
            Verdict.FAIL,
            id="open-and-trusts-external-mfa",
        ),
        pytest.param({}, [], Verdict.INCONCLUSIVE, id="no-access-type-returned"),
    ],
)
@respx.mock
async def test_c35_cross_tenant_access(
    default_policy: dict[str, Any], partners: list[dict[str, Any]], expected: Verdict
) -> None:
    finding = await evaluate(
        control("C35"),
        {"default_policy": default_policy, "partners": collection(*partners)},
    )

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c35_names_the_trust_of_an_external_multifactor_claim() -> None:
    finding = await evaluate(
        control("C35"),
        {
            "default_policy": cross_tenant_default(access="allowed", trust_mfa=True),
            "partners": collection(),
        },
    )

    assert "their own multifactor claim" in finding.rationale


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        pytest.param([retention_label()], Verdict.PASS, id="published-and-long-enough"),
        pytest.param([], Verdict.FAIL, id="no-label-at-all"),
        pytest.param([retention_label(in_use=False)], Verdict.FAIL, id="never-published"),
        pytest.param([retention_label(days=30)], Verdict.PARTIAL, id="shorter-than-the-threshold"),
        pytest.param([retention_label(days=None)], Verdict.INCONCLUSIVE, id="duration-unreadable"),
        pytest.param(
            [retention_label(), retention_label(days=None)],
            Verdict.PARTIAL,
            id="one-duration-unreadable",
        ),
    ],
)
@respx.mock
async def test_c36_retention_labels(labels: list[dict[str, Any]], expected: Verdict) -> None:
    finding = await evaluate(control("C36"), {"labels": collection(*labels)})

    assert finding.verdict is expected
    assert finding.rationale


@respx.mock
async def test_c36_treats_an_indefinite_hold_as_long_enough() -> None:
    forever = {
        "id": "fixture-label",
        "isInUse": True,
        "retentionDuration": {"@odata.type": "#microsoft.graph.security.retentionDurationForever"},
    }

    finding = await evaluate(control("C36"), {"labels": collection(forever)})

    assert finding.verdict is Verdict.PASS


def test_c36_says_plainly_that_retention_is_not_backup() -> None:
    assert "not backup" in control("C36").limits.lower()


@pytest.mark.parametrize("control_id", ["C32", "C33", "C34", "C35", "C36"])
@respx.mock
async def test_assurance_controls_fail_to_inconclusive_on_denial(control_id: str) -> None:
    respx.get(url__startswith=BASE).respond(403, json={"error": {"message": "Access denied"}})

    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [control(control_id)])

    assert run.findings[0].verdict is Verdict.INCONCLUSIVE
    assert "HTTP 403" in run.findings[0].rationale


@pytest.mark.parametrize("control_id", ["C32", "C33", "C34", "C35", "C36"])
def test_assurance_controls_document_their_limits(control_id: str) -> None:
    definition = control(control_id)

    assert len(definition.limits.strip()) > 40
    assert definition.remediation_steps
