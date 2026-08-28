"""Loading and validating YAML control definitions."""

import json
from collections.abc import Iterable
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from .models import ControlDefinition


class CatalogValidationError(ValueError):
    """A catalogue document does not comply with the public schema."""


def _schema_path() -> Path:
    return Path(__file__).with_name("schema.json")


def load_control(path: Path, schema_path: Path | None = None) -> ControlDefinition:
    """Load one YAML control after JSON-schema and model validation."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CatalogValidationError(f"{path}: expected a YAML mapping")

    schema = json.loads((schema_path or _schema_path()).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(raw),
        key=lambda error: list(error.path),
    )
    if errors:
        rendered = "; ".join(error.message for error in errors)
        raise CatalogValidationError(f"{path}: {rendered}")
    try:
        return ControlDefinition.model_validate(raw)
    except ValidationError as error:
        raise CatalogValidationError(f"{path}: {error}") from error


def load_catalog(directory: Path) -> list[ControlDefinition]:
    """Load controls in deterministic ID order."""
    return [load_control(path) for path in sorted(directory.glob("C*.yaml"))]


def required_scopes(controls: Iterable[ControlDefinition]) -> list[str]:
    """The read-only Graph permissions these controls need, as a stable sorted set.

    This is what an administrator consents to. Comparing it with what a tenant consented to
    earlier is how the hosted workspace knows a tenant has to approve again.
    """
    return sorted({scope for control in controls for scope in control.requires.scopes})
