"""The hosted side of scoping and the dossier.

The hosted database holds no company name and no registration number, so these tests pin that
down as much as they pin down the classification itself.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from nis2check_api.models import FindingRecord, TenantProfile
from nis2check_api.service import (
    _finding_from_record,
    _organisation_profile,
    profile_view,
    scoping_view,
    sector_options,
)
from nis2check_collector.models import RunResult, Verdict
from nis2check_reporting import render_dossier_html
from nis2check_scoping import NOT_LISTED, Classification, classify


def profile_record(**overrides: object) -> TenantProfile:
    values: dict[str, object] = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "sector_key": "health.provider",
        "employees": 400,
        "annual_turnover_eur": Decimal("90000000"),
        "balance_sheet_total_eur": Decimal("60000000"),
        "sole_provider": False,
        "critical_entity_cer": False,
        "designated_as": None,
        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
    }
    values.update(overrides)
    return TenantProfile(**values)


def finding_record(control_id: str = "C01", verdict: str = "FAIL") -> FindingRecord:
    return FindingRecord(
        id=uuid4(),
        tenant_id=uuid4(),
        run_id=uuid4(),
        control_id=control_id,
        nis2="21(2)(j)",
        domain="authentication",
        title=f"Control {control_id}",
        verdict=verdict,
        rationale=f"Rationale for {control_id}.",
        endpoints=["/v1.0/identity/conditionalAccess/policies"],
        remediation="https://learn.microsoft.com/entra",
        remediation_steps=["Create the policy.", "Enable it."],
        limits="Policy state only.",
        object_ids=["hmac-sha256:abc"],
        counts={"policies": 2},
    )


def test_the_hosted_profile_table_holds_nothing_that_identifies_the_customer() -> None:
    columns = set(TenantProfile.__table__.columns.keys())

    assert "name" not in columns
    assert "registration_number" not in columns
    assert {"sector_key", "employees", "annual_turnover_eur"} <= columns


def test_a_stored_profile_never_carries_a_name_into_the_scoping_package() -> None:
    profile = _organisation_profile(profile_record())

    assert profile.name is None
    assert profile.registration_number is None
    assert profile.sector_key == "health.provider"


def test_a_stored_profile_classifies_the_same_as_the_cli_would() -> None:
    outcome = classify(_organisation_profile(profile_record()))

    assert outcome.classification is Classification.ESSENTIAL


def test_a_designation_survives_the_round_trip_through_the_database() -> None:
    record = profile_record(designated_as="IMPORTANT", employees=3, annual_turnover_eur=None, balance_sheet_total_eur=None)

    outcome = classify(_organisation_profile(record))

    assert outcome.classification is Classification.IMPORTANT


def test_the_profile_view_is_empty_before_anything_is_declared() -> None:
    assert profile_view(None) == {"declared": None, "scoping": None}


def test_the_profile_view_returns_the_declaration_and_what_it_means() -> None:
    view = profile_view(profile_record())
    declared = view["declared"]
    scoping = view["scoping"]

    assert isinstance(declared, dict) and isinstance(scoping, dict)
    assert declared["sectorKey"] == "health.provider"
    assert declared["annualTurnoverEur"] == 90000000.0
    assert scoping["classification"] == "ESSENTIAL"
    assert scoping["inScope"] is True
    assert "Article 3(1)(a)" in scoping["legalBasis"]


def test_the_scoping_view_keeps_undetermined_undetermined() -> None:
    record = profile_record(employees=None, annual_turnover_eur=None, balance_sheet_total_eur=None)

    scoping = scoping_view(classify(_organisation_profile(record)))

    assert scoping["classification"] == "UNDETERMINED"
    assert scoping["inScope"] is None
    assert scoping["supervision"] == []


def test_the_sector_list_offers_every_annex_activity_and_a_way_out() -> None:
    options = sector_options()
    keys = [option["key"] for option in options]

    assert len(options) > 60
    assert keys[-1] == NOT_LISTED
    assert "banking.credit_institution" in keys
    assert len(set(keys)) == len(keys)
    assert all(option["subsector"] for option in options)


def test_a_stored_finding_becomes_a_finding_the_dossier_can_render() -> None:
    finding = _finding_from_record(finding_record())

    assert finding.control_id == "C01"
    assert finding.verdict is Verdict.FAIL
    assert finding.remediation_steps == ["Create the policy.", "Enable it."]
    assert finding.raw_evidence == {}, "stored findings hold no raw Graph payload to restore"


def test_the_hosted_dossier_renders_from_stored_findings() -> None:
    result = RunResult(
        tenant_id="00000000-0000-0000-0000-00000000fixt",
        started_at=datetime(2026, 1, 2, tzinfo=UTC),
        tool_version="0.1.0",
        findings=[_finding_from_record(finding_record("C01")), _finding_from_record(finding_record("C02", "PASS"))],
    )
    record = profile_record()

    html = render_dossier_html(
        result, scoping=classify(_organisation_profile(record)), profile=_organisation_profile(record)
    )

    assert "ESSENTIAL" in html
    assert "Control C01" in html
    assert "Coverage of article 21(2)" in html


def test_the_hosted_dossier_is_headed_by_the_tenant_id_because_no_name_is_stored() -> None:
    result = RunResult(
        tenant_id="00000000-0000-0000-0000-00000000fixt",
        started_at=datetime(2026, 1, 2, tzinfo=UTC),
        tool_version="0.1.0",
        findings=[_finding_from_record(finding_record())],
    )
    profile = _organisation_profile(profile_record())

    html = render_dossier_html(result, scoping=classify(profile), profile=profile)

    assert "00000000-0000-0000-0000-00000000fixt" in html
    assert "Organisation" not in html, "no company name is stored, so the cover does not claim one"


@pytest.mark.parametrize("sector_key", ["banking.credit_institution", NOT_LISTED])
def test_every_offered_sector_key_is_one_the_scoping_package_accepts(sector_key: str) -> None:
    record = profile_record(sector_key=sector_key)

    classify(_organisation_profile(record))
