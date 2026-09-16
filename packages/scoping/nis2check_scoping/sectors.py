"""Loading the annex I and annex II sector list."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import SectorDefinition


class SectorCatalogueError(ValueError):
    """The sector list does not parse into sector definitions."""


def _sectors_path() -> Path:
    return Path(__file__).with_name("sectors.yaml")


@lru_cache(maxsize=1)
def load_sectors(path: Path | None = None) -> tuple[SectorDefinition, ...]:
    """Every selectable activity, in file order, which is annex order."""
    document = yaml.safe_load((path or _sectors_path()).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("sectors"), list):
        raise SectorCatalogueError("Expected a mapping with a 'sectors' list")
    try:
        sectors = tuple(SectorDefinition.model_validate(entry) for entry in document["sectors"])
    except ValidationError as error:
        raise SectorCatalogueError(str(error)) from error
    keys = [sector.key for sector in sectors]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise SectorCatalogueError(f"Duplicate sector keys: {', '.join(duplicates)}")
    return sectors


def find_sector(key: str) -> SectorDefinition | None:
    """The sector with this key, or None when the key is not in either annex."""
    return next((sector for sector in load_sectors() if sector.key == key), None)


def sectors_by_annex() -> dict[str, list[SectorDefinition]]:
    """Sectors grouped by the annex that lists them, for building a selection list."""
    grouped: dict[str, list[SectorDefinition]] = {}
    for sector in load_sectors():
        grouped.setdefault(sector.annex.value, []).append(sector)
    return grouped
