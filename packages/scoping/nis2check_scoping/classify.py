"""Deciding whether NIS2 applies to an organisation, and as an essential or important entity.

Everything here follows directive (EU) 2022/2555 article 2 for scope, article 3 for the tier,
and the annex to recommendation 2003/361/EC for enterprise size. Where the declared figures do
not settle the question, the answer is UNDETERMINED with the reason attached, never a guess.
"""

from decimal import Decimal

from .models import (
    Classification,
    EssentialRule,
    OrganisationProfile,
    ScopeRule,
    ScopingResult,
    SectorDefinition,
    SizeClass,
)
from .sectors import find_sector

#: Sector key for "none of these activities", which the questionnaire has to offer.
NOT_LISTED = "not_listed"

#: Staff headcount, annual turnover and balance sheet total ceilings of the SME recommendation.
MEDIUM_CEILING = (250, Decimal("50000000"), Decimal("43000000"))
SMALL_CEILING = (50, Decimal("10000000"), Decimal("10000000"))
MICRO_CEILING = (10, Decimal("2000000"), Decimal("2000000"))

ESSENTIAL_SUPERVISION = [
    "Proactive supervision: regular and targeted security audits, on-site inspections and off-site checks, without a prior indication of non-compliance (article 32).",
    "Administrative fines of up to EUR 10 000 000 or 2% of total worldwide annual turnover, whichever is higher (article 34(4)).",
]
IMPORTANT_SUPERVISION = [
    "Reactive supervision only: the authority acts when it has evidence or an indication of non-compliance, or after an incident (article 33).",
    "Administrative fines of up to EUR 7 000 000 or 1.4% of total worldwide annual turnover, whichever is higher (article 34(5)).",
]
SHARED_SUPERVISION = [
    "Registration with the national authority, in Belgium the Centre for Cybersecurity Belgium, so the entity appears in the register of article 3(4).",
    "Incident reporting under article 23: an early warning within 24 hours, an incident notification within 72 hours and a final report within one month.",
    "The management body approves the risk management measures and can be held liable for failing to do so (article 20).",
]
OUT_OF_SCOPE_SUPERVISION = [
    "No direct obligation and no supervisory authority for the entity itself.",
    "Customers that are in scope must manage supplier risk under article 21(2)(d), so the requirements still arrive through contracts.",
    "A Member State may still designate the entity under article 2(2), which changes this outcome.",
]


def _exceeds(
    employees: int | None,
    turnover: Decimal | None,
    balance: Decimal | None,
    ceiling: tuple[int, Decimal, Decimal],
) -> bool | None:
    """Whether the entity exceeds a ceiling, or None when the figures do not settle it.

    A ceiling is exceeded when headcount reaches it, or when both financial figures pass it.
    It is provably not exceeded only when headcount is below it and at least one financial
    figure stays within it, which is what the "and/or" of the recommendation means.
    """
    staff_cap, turnover_cap, balance_cap = ceiling
    if employees is not None and employees >= staff_cap:
        return True
    if turnover is not None and balance is not None and turnover > turnover_cap and balance > balance_cap:
        return True
    within_financial = (turnover is not None and turnover <= turnover_cap) or (
        balance is not None and balance <= balance_cap
    )
    if employees is not None and employees < staff_cap and within_financial:
        return False
    return None


def size_class(
    employees: int | None,
    turnover: Decimal | None = None,
    balance: Decimal | None = None,
) -> SizeClass:
    """Enterprise size under the annex to recommendation 2003/361/EC."""
    for ceiling, larger, smaller in (
        (MEDIUM_CEILING, SizeClass.LARGE, None),
        (SMALL_CEILING, SizeClass.MEDIUM, None),
        (MICRO_CEILING, SizeClass.SMALL, SizeClass.MICRO),
    ):
        exceeds = _exceeds(employees, turnover, balance, ceiling)
        if exceeds is None:
            return SizeClass.UNDETERMINED
        if exceeds:
            return larger
        if smaller is not None:
            return smaller
    return SizeClass.UNDETERMINED  # pragma: no cover - the loop always returns


def _figures(profile: OrganisationProfile) -> str:
    """How the declared figures read back, so a rationale can quote them."""
    parts = []
    if profile.employees is not None:
        parts.append(f"{profile.employees} employee(s)")
    if profile.annual_turnover_eur is not None:
        parts.append(f"EUR {profile.annual_turnover_eur:,.0f} turnover")
    if profile.balance_sheet_total_eur is not None:
        parts.append(f"EUR {profile.balance_sheet_total_eur:,.0f} balance sheet total")
    return ", ".join(parts) if parts else "no size figures"


def _missing(profile: OrganisationProfile) -> str:
    """Which declared figures would settle an undetermined size."""
    absent = [
        label
        for label, value in (
            ("the headcount", profile.employees),
            ("the annual turnover", profile.annual_turnover_eur),
            ("the balance sheet total", profile.balance_sheet_total_eur),
        )
        if value is None
    ]
    return " and ".join(absent) if absent else "a consistent set of figures"


def _tier(sector: SectorDefinition, size: SizeClass) -> Classification:
    """Essential or important under article 3, given a sector and a settled scope."""
    if sector.essential_rule is EssentialRule.ALWAYS:
        return Classification.ESSENTIAL
    if sector.essential_rule is EssentialRule.NEVER:
        return Classification.IMPORTANT
    if size is SizeClass.UNDETERMINED:
        return Classification.UNDETERMINED
    if sector.essential_rule is EssentialRule.WHEN_LARGE:
        return Classification.ESSENTIAL if size is SizeClass.LARGE else Classification.IMPORTANT
    return (
        Classification.ESSENTIAL
        if size in (SizeClass.MEDIUM, SizeClass.LARGE)
        else Classification.IMPORTANT
    )


def _supervision(classification: Classification) -> list[str]:
    if classification is Classification.ESSENTIAL:
        return ESSENTIAL_SUPERVISION + SHARED_SUPERVISION
    if classification is Classification.IMPORTANT:
        return IMPORTANT_SUPERVISION + SHARED_SUPERVISION
    if classification is Classification.OUT_OF_SCOPE:
        return list(OUT_OF_SCOPE_SUPERVISION)
    return []


def classify(profile: OrganisationProfile) -> ScopingResult:
    """Classify a self-declared organisation profile. Raises on an unknown sector key."""
    sector = None if profile.sector_key == NOT_LISTED else find_sector(profile.sector_key)
    if sector is None and profile.sector_key != NOT_LISTED:
        raise LookupError(f"Unknown sector key: {profile.sector_key}")
    size = size_class(profile.employees, profile.annual_turnover_eur, profile.balance_sheet_total_eur)

    if profile.designated_as is not None:
        return _result(
            profile.designated_as,
            size,
            sector,
            f"A national authority designated this entity as {profile.designated_as.lower()}, which settles the classification whatever the size figures say.",
            ["Article 3(1)(e)", "Article 3(2)"],
        )

    if profile.critical_entity_cer:
        return _result(
            Classification.ESSENTIAL,
            size,
            sector,
            "The entity is identified as critical under directive (EU) 2022/2557, which makes it essential regardless of sector or size.",
            ["Article 2(3)", "Article 3(1)(f)"],
        )

    if sector is None:
        return _result(
            Classification.OUT_OF_SCOPE,
            size,
            None,
            "The declared activity is not listed in annex I or annex II, so the directive does not apply of its own accord.",
            ["Article 2(1)", "Annex I", "Annex II"],
        )

    size_exempt = sector.scope_rule is ScopeRule.REGARDLESS_OF_SIZE
    if size_exempt or profile.sole_provider:
        basis = "Article 2(2)(a)" if size_exempt else "Article 2(2)(b)"
        reason = (
            f"a {sector.subsector.lower()} is in scope at any size"
            if size_exempt
            else "the entity declares it is the sole provider in the Member State of an essential service"
        )
        tier = _tier(sector, size)
        if tier is Classification.UNDETERMINED:
            return _result(
                tier,
                size,
                sector,
                f"The entity is in scope because {reason}, but {_missing(profile)} is missing, so essential cannot be told apart from important. Declared: {_figures(profile)}.",
                [basis, "Article 3(1)", "Recommendation 2003/361/EC, annex article 2"],
                in_scope=True,
            )
        return _result(
            tier,
            size,
            sector,
            f"The entity is in scope because {reason}, and article 3 places a {size.lower()} {sector.subsector.lower()} in annex {sector.annex.value} among the {tier.lower()} entities.",
            [basis, _tier_article(sector, tier), f"Annex {sector.annex_point}"],
        )

    if size is SizeClass.UNDETERMINED:
        return _result(
            Classification.UNDETERMINED,
            size,
            sector,
            f"The activity is listed in annex {sector.annex_point}, but {_missing(profile)} is missing, so the medium-sized ceilings of article 2(1) cannot be applied. Declared: {_figures(profile)}.",
            ["Article 2(1)", "Recommendation 2003/361/EC, annex article 2"],
        )

    if size in (SizeClass.MICRO, SizeClass.SMALL):
        return _result(
            Classification.OUT_OF_SCOPE,
            size,
            sector,
            f"The activity is listed in annex {sector.annex_point}, but a {size.lower()} enterprise stays below the medium-sized ceilings of article 2(1). Declared: {_figures(profile)}.",
            ["Article 2(1)", "Recommendation 2003/361/EC, annex article 2"],
        )

    tier = _tier(sector, size)
    return _result(
        tier,
        size,
        sector,
        f"A {size.lower()} enterprise in annex {sector.annex_point} is in scope under article 2(1) and counts as an {tier.lower()} entity. Declared: {_figures(profile)}.",
        ["Article 2(1)", _tier_article(sector, tier), f"Annex {sector.annex_point}"],
    )


def _tier_article(sector: SectorDefinition, tier: Classification) -> str:
    if tier is not Classification.ESSENTIAL:
        return "Article 3(2)"
    if sector.essential_rule is EssentialRule.ALWAYS:
        return "Article 3(1)(b)" if sector.annex_point != "I.10(a)" else "Article 3(1)(d)"
    if sector.essential_rule is EssentialRule.WHEN_MEDIUM_OR_LARGER:
        return "Article 3(1)(c)"
    return "Article 3(1)(a)"


#: How a classification answers "does the directive apply at all".
IN_SCOPE: dict[Classification, bool | None] = {
    Classification.ESSENTIAL: True,
    Classification.IMPORTANT: True,
    Classification.OUT_OF_SCOPE: False,
    Classification.UNDETERMINED: None,
}


def _result(
    classification: Classification,
    size: SizeClass,
    sector: SectorDefinition | None,
    rationale: str,
    legal_basis: list[str],
    in_scope: bool | None = None,
) -> ScopingResult:
    return ScopingResult(
        classification=classification,
        size=size,
        sector=sector,
        in_scope=IN_SCOPE[classification] if in_scope is None else in_scope,
        rationale=rationale,
        legal_basis=legal_basis,
        supervision=_supervision(classification),
    )
