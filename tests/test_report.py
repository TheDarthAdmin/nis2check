"""The rendered evidence report must stay self-contained and readable without JavaScript."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from nis2check_cli.report import follow_up, group_by_domain, render_html, verdict_tally
from nis2check_collector.models import Finding, RunResult, Verdict

TEMPLATES = Path(__file__).resolve().parents[1] / "apps" / "cli" / "templates"


def finding(control_id: str, verdict: Verdict, domain: str = "authentication") -> Finding:
    return Finding(
        control_id=control_id,
        nis2="21(2)(j)",
        domain=domain,
        title=f"Control {control_id}",
        verdict=verdict,
        rationale=f"Rationale for {control_id}.",
        endpoints=["/v1.0/identity/conditionalAccess/policies"],
        remediation="https://learn.microsoft.com/entra/identity",
        limits="Reads policy state only.",
        remediation_steps=[f"Open the admin center and fix {control_id}."],
        raw_evidence={"value": [{"id": "policy-1"}]},
    )


def run_result(*findings: Finding) -> RunResult:
    return RunResult(
        tenant_id="00000000-0000-0000-0000-000000000001",
        started_at=datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
        tool_version="0.1.0",
        findings=list(findings),
    )


def test_tally_counts_every_verdict_without_a_score() -> None:
    tally = verdict_tally([finding("C01", Verdict.FAIL), finding("C02", Verdict.FAIL)])
    assert tally[0] == (Verdict.FAIL, 2)
    assert [verdict for verdict, _ in tally] == [
        Verdict.FAIL,
        Verdict.PARTIAL,
        Verdict.INCONCLUSIVE,
        Verdict.PASS,
        Verdict.NOT_APPLICABLE,
    ]
    assert sum(count for _, count in tally) == 2


@pytest.mark.parametrize("verdict", [Verdict.FAIL, Verdict.PARTIAL, Verdict.INCONCLUSIVE])
def test_follow_up_lists_everything_that_is_not_evidenced(verdict: Verdict) -> None:
    assert [item.control_id for item in follow_up([finding("C01", verdict)])] == ["C01"]


@pytest.mark.parametrize("verdict", [Verdict.PASS, Verdict.NOT_APPLICABLE])
def test_follow_up_ignores_settled_verdicts(verdict: Verdict) -> None:
    assert follow_up([finding("C01", verdict)]) == []


def test_findings_are_grouped_by_domain_with_follow_up_first() -> None:
    grouped = group_by_domain(
        [
            finding("C01", Verdict.PASS),
            finding("C02", Verdict.FAIL),
            finding("C03", Verdict.PARTIAL, domain="devices"),
        ]
    )
    assert [domain for domain, _ in grouped] == ["authentication", "devices"]
    assert [item.control_id for item in grouped[0][1]] == ["C02", "C01"]


def test_report_is_self_contained() -> None:
    html = render_html(run_result(finding("C01", Verdict.FAIL)), TEMPLATES)
    assert "https://" not in html.split("<body")[0]
    assert "<script src" not in html
    assert "<link" not in html


def test_report_shows_the_evidence_and_its_limits() -> None:
    html = render_html(
        run_result(finding("C01", Verdict.FAIL), finding("C02", Verdict.PASS, domain="devices")), TEMPLATES
    )
    assert "not a NIS2 conformance statement" in html
    assert "Rationale for C01." in html
    assert "Reads policy state only." in html
    assert 'data-verdict="FAIL"' in html
    assert "Authentication" in html and "Devices" in html
    assert "Needs follow-up" in html


def test_report_shows_how_to_remediate_a_finding() -> None:
    html = render_html(run_result(finding("C01", Verdict.FAIL)), TEMPLATES)

    assert "How to remediate" in html
    assert "Open the admin center and fix C01." in html


def test_report_says_so_when_nothing_needs_follow_up() -> None:
    html = render_html(run_result(finding("C01", Verdict.PASS)), TEMPLATES)
    assert "Needs follow-up" not in html
    assert "not applicable to this tenant" in html


def test_report_escapes_evidence_content() -> None:
    injected = finding("C01", Verdict.FAIL).model_copy(
        update={"rationale": "<script>alert('x')</script>"}
    )
    html = render_html(run_result(injected), TEMPLATES)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
