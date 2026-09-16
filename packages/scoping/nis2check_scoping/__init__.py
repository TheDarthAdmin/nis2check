"""Self-declared entity scoping for NIS2, kept strictly apart from collected evidence."""

from .classify import NOT_LISTED, classify, size_class
from .models import (
    Annex,
    Classification,
    EssentialRule,
    OrganisationProfile,
    ScopeRule,
    ScopingResult,
    SectorDefinition,
    SizeClass,
)
from .sectors import SectorCatalogueError, find_sector, load_sectors, sectors_by_annex

__all__ = [
    "NOT_LISTED",
    "Annex",
    "Classification",
    "EssentialRule",
    "OrganisationProfile",
    "ScopeRule",
    "ScopingResult",
    "SectorCatalogueError",
    "SectorDefinition",
    "SizeClass",
    "classify",
    "find_sector",
    "load_sectors",
    "sectors_by_annex",
    "size_class",
]
