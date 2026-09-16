"""Models for entity scoping: does NIS2 apply to this organisation, and as what.

Scoping is not evidence. It is what the organisation declares about itself, so it lives
outside the collector and never becomes a Finding. The separation is deliberate: a verdict
in a report has to be traceable to a Graph response, a classification never is.
"""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Annex(StrEnum):
    """Which NIS2 annex lists the sector."""

    HIGH_CRITICALITY = "I"
    OTHER_CRITICAL = "II"


class ScopeRule(StrEnum):
    """How the size gate of article 2 applies to a sector."""

    #: Article 2(1): in scope from medium-sized upwards.
    BY_SIZE = "by_size"
    #: Article 2(2)(a): in scope at any size.
    REGARDLESS_OF_SIZE = "regardless_of_size"


class EssentialRule(StrEnum):
    """How article 3 decides essential versus important for a sector."""

    #: Article 3(1)(a): essential once the entity exceeds the medium-sized ceilings.
    WHEN_LARGE = "when_large"
    #: Article 3(1)(b): essential at any size.
    ALWAYS = "always"
    #: Article 3(1)(c): essential from medium-sized upwards.
    WHEN_MEDIUM_OR_LARGER = "when_medium_or_larger"
    #: Annex II: important unless a Member State designates otherwise.
    NEVER = "never"


class SizeClass(StrEnum):
    """Enterprise size under Recommendation 2003/361/EC, annex article 2."""

    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    UNDETERMINED = "UNDETERMINED"


class Classification(StrEnum):
    """The outcome of scoping.

    `UNDETERMINED` exists for the same reason `INCONCLUSIVE` does: telling an organisation
    it is out of scope on incomplete figures is worse than telling it we cannot say.
    """

    ESSENTIAL = "ESSENTIAL"
    IMPORTANT = "IMPORTANT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNDETERMINED = "UNDETERMINED"


class SectorDefinition(BaseModel):
    """One selectable activity from annex I or annex II."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_.]*$")
    annex: Annex
    annex_point: str
    sector: str
    subsector: str
    scope_rule: ScopeRule = ScopeRule.BY_SIZE
    essential_rule: EssentialRule = EssentialRule.WHEN_LARGE


class OrganisationProfile(BaseModel):
    """What an organisation declares about itself. Every field is self-reported.

    No identifying data is required to classify. `name` and `registration_number` are
    optional and exist only so a downloaded report can carry its own heading; nothing in
    this package stores, transmits or needs them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    sector_key: str
    employees: int | None = Field(default=None, ge=0)
    annual_turnover_eur: Decimal | None = Field(default=None, ge=0)
    balance_sheet_total_eur: Decimal | None = Field(default=None, ge=0)
    #: Article 2(2)(b): sole provider in a Member State of an essential service.
    sole_provider: bool = False
    #: Article 2(3): identified as critical under directive (EU) 2022/2557.
    critical_entity_cer: bool = False
    #: Article 3(1)(e)/(g): a national authority designated this entity explicitly.
    designated_as: Classification | None = None
    name: str | None = None
    registration_number: str | None = None
    country: str = "BE"


class ScopingResult(BaseModel):
    """A classification with the reasoning and the articles it rests on."""

    model_config = ConfigDict(frozen=True)

    classification: Classification
    size: SizeClass
    sector: SectorDefinition | None
    #: Whether the directive applies at all. None when the figures do not settle it.
    in_scope: bool | None
    rationale: str = Field(min_length=1)
    legal_basis: list[str] = Field(default_factory=list)
    #: What the classification means for supervision, not what the organisation must do.
    supervision: list[str] = Field(default_factory=list)
