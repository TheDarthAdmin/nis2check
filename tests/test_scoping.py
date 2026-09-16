"""Scoping tests. Every case is a declared profile; none of them carries real customer data."""

from decimal import Decimal

import pytest
from nis2check_scoping import (
    NOT_LISTED,
    Classification,
    OrganisationProfile,
    SectorCatalogueError,
    SizeClass,
    classify,
    find_sector,
    load_sectors,
    sectors_by_annex,
    size_class,
)

LARGE = {"employees": 400}
MEDIUM = {
    "employees": 120,
    "annual_turnover_eur": Decimal("30000000"),
    "balance_sheet_total_eur": Decimal("25000000"),
}
SMALL = {"employees": 20, "annual_turnover_eur": Decimal("4000000")}


def profile(sector_key: str, **kwargs: object) -> OrganisationProfile:
    return OrganisationProfile(sector_key=sector_key, **kwargs)  # type: ignore[arg-type]


class TestSizeClass:
    def test_headcount_alone_settles_large(self) -> None:
        assert size_class(250) is SizeClass.LARGE

    def test_both_financial_ceilings_must_be_passed_to_be_large(self) -> None:
        assert size_class(10, Decimal("80000000"), Decimal("20000000")) is SizeClass.MEDIUM
        assert size_class(10, Decimal("80000000"), Decimal("60000000")) is SizeClass.LARGE

    def test_medium_small_and_micro_boundaries(self) -> None:
        assert size_class(50, Decimal("1000000"), Decimal("1000000")) is SizeClass.MEDIUM
        assert size_class(49, Decimal("1000000"), Decimal("1000000")) is SizeClass.SMALL
        assert size_class(9, Decimal("1000000"), Decimal("1000000")) is SizeClass.MICRO

    def test_turnover_over_ten_million_lifts_a_small_headcount_to_medium(self) -> None:
        assert size_class(20, Decimal("12000000"), Decimal("11000000")) is SizeClass.MEDIUM

    def test_missing_figures_are_undetermined_rather_than_assumed_small(self) -> None:
        assert size_class(None) is SizeClass.UNDETERMINED
        assert size_class(None, Decimal("1000")) is SizeClass.UNDETERMINED
        assert size_class(10) is SizeClass.UNDETERMINED

    def test_headcount_below_the_ceiling_still_needs_a_financial_figure(self) -> None:
        """120 staff with over EUR 50m turnover and over EUR 43m balance is still large."""
        assert size_class(120) is SizeClass.UNDETERMINED
        assert size_class(120, Decimal("80000000"), Decimal("60000000")) is SizeClass.LARGE
        assert size_class(120, Decimal("30000000")) is SizeClass.MEDIUM


class TestSectorCatalogue:
    def test_every_sector_loads_and_is_in_an_annex(self) -> None:
        sectors = load_sectors()
        assert len(sectors) > 60
        assert {sector.annex.value for sector in sectors} == {"I", "II"}

    def test_keys_are_unique_and_findable(self) -> None:
        sectors = load_sectors()
        assert len({sector.key for sector in sectors}) == len(sectors)
        assert find_sector("banking.credit_institution") is not None
        assert find_sector("nope.not.a.sector") is None

    def test_annex_two_sectors_are_never_essential_by_rule(self) -> None:
        for sector in sectors_by_annex()["II"]:
            assert sector.essential_rule.value == "never", sector.key

    def test_a_broken_catalogue_is_rejected(self, tmp_path: object) -> None:
        from pathlib import Path

        from nis2check_scoping.sectors import load_sectors as loader

        broken = Path(str(tmp_path)) / "sectors.yaml"
        broken.write_text("sectors: not-a-list\n", encoding="utf-8")
        with pytest.raises(SectorCatalogueError):
            loader(broken)


class TestClassification:
    def test_large_annex_one_entity_is_essential(self) -> None:
        outcome = classify(profile("energy.electricity_dso", **LARGE))
        assert outcome.classification is Classification.ESSENTIAL
        assert outcome.in_scope is True
        assert "Article 3(1)(a)" in outcome.legal_basis

    def test_medium_annex_one_entity_is_important(self) -> None:
        outcome = classify(profile("health.provider", **MEDIUM))
        assert outcome.classification is Classification.IMPORTANT
        assert "Article 3(2)" in outcome.legal_basis

    def test_large_annex_two_entity_stays_important(self) -> None:
        outcome = classify(profile("food.production", **LARGE))
        assert outcome.classification is Classification.IMPORTANT
        assert outcome.size is SizeClass.LARGE

    def test_small_entity_in_a_listed_sector_is_out_of_scope(self) -> None:
        outcome = classify(profile("manufacturing.machinery", **SMALL))
        assert outcome.classification is Classification.OUT_OF_SCOPE
        assert outcome.in_scope is False

    def test_unlisted_activity_is_out_of_scope_but_told_about_the_supply_chain(self) -> None:
        outcome = classify(profile(NOT_LISTED, **LARGE))
        assert outcome.classification is Classification.OUT_OF_SCOPE
        assert outcome.sector is None
        assert any("21(2)(d)" in line for line in outcome.supervision)

    def test_missing_figures_give_undetermined_not_out_of_scope(self) -> None:
        outcome = classify(profile("chemicals.manufacture"))
        assert outcome.classification is Classification.UNDETERMINED
        assert outcome.in_scope is None
        assert "the headcount" in outcome.rationale

    def test_unknown_sector_key_is_an_error_not_a_verdict(self) -> None:
        with pytest.raises(LookupError):
            classify(profile("energy.nonexistent"))


class TestSizeExemptSectors:
    def test_tiny_dns_provider_is_essential_regardless_of_size(self) -> None:
        outcome = classify(profile("digital_infrastructure.dns_service_provider", employees=3))
        assert outcome.classification is Classification.ESSENTIAL
        assert "Article 2(2)(a)" in outcome.legal_basis

    def test_qualified_trust_service_provider_is_essential_with_no_figures_at_all(self) -> None:
        outcome = classify(profile("digital_infrastructure.trust_service_qualified"))
        assert outcome.classification is Classification.ESSENTIAL
        assert outcome.size is SizeClass.UNDETERMINED

    def test_small_electronic_communications_provider_is_important(self) -> None:
        outcome = classify(profile("digital_infrastructure.public_ecomms_service", **SMALL))
        assert outcome.classification is Classification.IMPORTANT

    def test_medium_electronic_communications_provider_is_essential(self) -> None:
        outcome = classify(profile("digital_infrastructure.public_ecomms_service", **MEDIUM))
        assert outcome.classification is Classification.ESSENTIAL
        assert "Article 3(1)(c)" in outcome.legal_basis

    def test_size_exempt_sector_without_figures_reports_in_scope_but_undetermined_tier(self) -> None:
        outcome = classify(profile("digital_infrastructure.trust_service_non_qualified"))
        assert outcome.classification is Classification.UNDETERMINED
        assert outcome.in_scope is True
        assert "in scope" in outcome.rationale


class TestOverrides:
    def test_cer_critical_entity_is_essential_whatever_the_sector(self) -> None:
        outcome = classify(profile("food.distribution", critical_entity_cer=True, **SMALL))
        assert outcome.classification is Classification.ESSENTIAL
        assert "Article 3(1)(f)" in outcome.legal_basis

    def test_authority_designation_wins_over_the_size_gate(self) -> None:
        outcome = classify(
            profile("waste.management", designated_as=Classification.ESSENTIAL, **SMALL)
        )
        assert outcome.classification is Classification.ESSENTIAL
        assert "Article 3(1)(e)" in outcome.legal_basis

    def test_sole_provider_is_in_scope_below_the_ceilings(self) -> None:
        outcome = classify(profile("transport.port_managing_body", sole_provider=True, **SMALL))
        assert outcome.classification is Classification.IMPORTANT
        assert "Article 2(2)(b)" in outcome.legal_basis

    def test_central_government_is_essential_at_any_size(self) -> None:
        outcome = classify(profile("public_administration.central_government", employees=4))
        assert outcome.classification is Classification.ESSENTIAL
        assert "Article 3(1)(d)" in outcome.legal_basis


class TestSupervision:
    def test_essential_supervision_is_proactive_and_important_is_reactive(self) -> None:
        essential = classify(profile("banking.credit_institution", **LARGE))
        important = classify(profile("postal.postal_courier", **MEDIUM))
        assert any("without a prior indication" in line for line in essential.supervision)
        assert any("evidence or an indication" in line for line in important.supervision)

    def test_both_tiers_carry_the_shared_obligations(self) -> None:
        for outcome in (
            classify(profile("banking.credit_institution", **LARGE)),
            classify(profile("postal.postal_courier", **MEDIUM)),
        ):
            assert any("Centre for Cybersecurity Belgium" in line for line in outcome.supervision)
            assert any("article 23" in line for line in outcome.supervision)

    def test_undetermined_promises_no_supervision_detail(self) -> None:
        assert classify(profile("chemicals.manufacture")).supervision == []


def test_scoping_never_imports_collector_or_hosted_code() -> None:
    from pathlib import Path

    root = Path(__file__).parents[1] / "packages" / "scoping"
    forbidden = ("fastapi", "sqlalchemy", "httpx", "msal", "nis2check_collector", "nis2check_api")
    for source in root.rglob("*.py"):
        text = source.read_text(encoding="utf-8").lower()
        assert not any(term in text for term in forbidden), source
