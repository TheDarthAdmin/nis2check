"""The downloadable dossier must stay self-contained, complete and free of a total score."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from nis2check_catalog import ARTICLE_21_2
from nis2check_cli.dossier import (
    endpoint_index,
    measure_coverage,
    open_limits,
    render_dossier_html,
)
from nis2check_collector.models import Finding, RunResult, Verdict
from nis2check_scoping import Classification, OrganisationProfile, classify

TEMPLATES = Path(__file__).resolve().parents[1] / "apps" / "cli" / "templates"


def finding(
    control_id: str,
    verdict: Verdict = Verdict.PASS,
    nis2: str = "21(2)(j)",
    domain: str = "authentication",
    endpoint: str = "/v1.0/identity/conditionalAccess/policies",
) -> Finding:
    return Finding(
        control_id=control_id,
        nis2=nis2,
        domain=domain,
        title=f"Control {control_id}",
        verdict=verdict,
        rationale=f"Rationale for {control_id}.",
        endpoints=[endpoint],
        remediation="https://learn.microsoft.com/entra/identity",
        remediation_steps=[f"Open the admin center and fix {control_id}."],
        limits=f"Limit of {control_id}.",
        raw_evidence={"value": [{"id": "fixture"}]},
    )


def run_result(*findings: Finding) -> RunResult:
    return RunResult(
        tenant_id="00000000-0000-0000-0000-00000000fixt",
        started_at=datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
        tool_version="0.0.0-test",
        findings=list(findings),
    )


def essential_profile() -> OrganisationProfile:
    return OrganisationProfile(
        sector_key="health.provider",
        employees=400,
        annual_turnover_eur=Decimal("90000000"),
        balance_sheet_total_eur=Decimal("60000000"),
        name="Fixture Zorggroep",
        registration_number="BE0000000000",
    )


def test_every_measure_of_article_21_stays_in_the_coverage_matrix() -> None:
    coverage = measure_coverage([finding("C01", nis2="21(2)(j)")])

    assert [letter for letter, _, _, _ in coverage] == list(ARTICLE_21_2)
    empty = {letter: items for letter, _, items, _ in coverage if not items}
    assert "a" in empty, "a measure with no finding must not be dropped from the matrix"


def test_the_coverage_matrix_tallies_each_measure_separately() -> None:
    coverage = measure_coverage(
        [
            finding("C01", Verdict.FAIL, nis2="21(2)(j)"),
            finding("C02", Verdict.PASS, nis2="21(2)(j)"),
            finding("C12", Verdict.PASS, nis2="21(2)(b)"),
        ]
    )
    by_letter = {letter: tally for letter, _, _, tally in coverage}

    assert dict(by_letter["j"])[Verdict.FAIL] == 1
    assert dict(by_letter["b"])[Verdict.PASS] == 1
    assert dict(by_letter["b"])[Verdict.FAIL] == 0


def test_an_unparseable_article_reference_does_not_crash_the_matrix() -> None:
    coverage = measure_coverage([finding("C99", nis2="Annex I")])

    assert sum(len(items) for _, _, items, _ in coverage) == 0


def test_the_endpoint_appendix_lists_every_control_that_read_an_endpoint() -> None:
    index = endpoint_index(
        [
            finding("C01", endpoint="/v1.0/policies"),
            finding("C02", endpoint="/v1.0/policies"),
            finding("C03", endpoint="/v1.0/domains"),
        ]
    )

    assert index == [("/v1.0/domains", ["C03"]), ("/v1.0/policies", ["C01", "C02"])]


def test_passing_controls_keep_their_limits_in_the_appendix() -> None:
    """A PASS whose limit is hidden is the easiest way for a dossier to mislead."""
    limits = open_limits([finding("C01", Verdict.PASS), finding("C02", Verdict.FAIL)])

    assert [item.control_id for item in limits] == ["C02", "C01"]


def test_the_dossier_renders_without_a_scoping_profile() -> None:
    html = render_dossier_html(run_result(finding("C01")), TEMPLATES)

    assert "Scope and classification" not in html
    assert "How to read this dossier" in html
    assert "Coverage of article 21(2)" in html


def test_the_dossier_carries_the_classification_when_a_profile_is_given() -> None:
    profile = essential_profile()

    html = render_dossier_html(
        run_result(finding("C01")), TEMPLATES, scoping=classify(profile), profile=profile
    )

    assert "Scope and classification" in html
    assert "ESSENTIAL" in html
    assert "Fixture Zorggroep" in html
    assert "Article 3(1)(a)" in html


def test_the_dossier_says_the_classification_is_declared_not_collected() -> None:
    profile = essential_profile()

    html = render_dossier_html(
        run_result(finding("C01")), TEMPLATES, scoping=classify(profile), profile=profile
    )

    assert "Nothing in this section was read from the tenant" in html


def test_the_dossier_refuses_to_become_a_conformance_statement() -> None:
    html = render_dossier_html(run_result(finding("C01")), TEMPLATES)

    assert "not a conformance statement" in html
    assert "There is no total and no percentage" in html


def test_the_dossier_pulls_in_no_external_resource() -> None:
    html = render_dossier_html(run_result(finding("C01")), TEMPLATES)

    assert "<script" not in html
    assert "<link" not in html
    assert "src=" not in html
    assert "@import" not in html


def test_remediation_steps_are_shown_for_findings_that_need_follow_up() -> None:
    html = render_dossier_html(
        run_result(finding("C01", Verdict.FAIL), finding("C02", Verdict.PASS)), TEMPLATES
    )

    assert "Open the admin center and fix C01." in html
    assert "Open the admin center and fix C02." not in html
    assert "Limit of C02." in html, "a passing control still shows its limit"


def test_tenant_strings_are_escaped_rather_than_rendered() -> None:
    injected = run_result(finding("C01")).model_copy(
        update={"tenant_id": "<script>alert('x')</script>"}
    )

    html = render_dossier_html(injected, TEMPLATES)

    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    "classification",
    [Classification.ESSENTIAL, Classification.IMPORTANT, Classification.OUT_OF_SCOPE],
)
def test_the_cover_states_whatever_the_classification_turned_out_to_be(
    classification: Classification,
) -> None:
    profile = OrganisationProfile(sector_key="health.provider", designated_as=classification)

    html = render_dossier_html(
        run_result(finding("C01")), TEMPLATES, scoping=classify(profile), profile=profile
    )

    assert classification.replace("_", " ") in html


def test_the_pdf_writer_explains_itself_when_its_libraries_are_missing() -> None:
    """The CLI must keep working without WeasyPrint, and say what is missing when asked for a PDF."""
    from nis2check_cli import dossier

    source = Path(dossier.__file__).read_text(encoding="utf-8")

    assert "libpango-1.0-0" in source, "the error has to name the package that is missing"
    assert source.index("def write_pdf") < source.index("from weasyprint import HTML"), (
        "WeasyPrint must be imported inside write_pdf, so `run` and `report` work without it"
    )


def test_the_pdf_actually_renders_when_weasyprint_is_usable(tmp_path: Path) -> None:
    # importorskip only catches ImportError; a missing Pango surfaces as OSError from cffi.
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError) as error:
        pytest.skip(f"WeasyPrint cannot load its system libraries: {error}")
    from nis2check_cli.dossier import write_pdf

    profile = essential_profile()
    html = render_dossier_html(
        run_result(finding("C01", Verdict.FAIL), finding("C02")),
        TEMPLATES,
        scoping=classify(profile),
        profile=profile,
    )
    output = tmp_path / "dossier.pdf"

    write_pdf(html, output)

    assert output.read_bytes().startswith(b"%PDF-")
