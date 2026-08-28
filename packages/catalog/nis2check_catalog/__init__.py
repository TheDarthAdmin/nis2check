"""Declarative NIS2 control catalogue."""

from .loader import CatalogValidationError, load_catalog, load_control, required_scopes
from .models import ControlDefinition

__all__ = [
    "CatalogValidationError",
    "ControlDefinition",
    "load_catalog",
    "load_control",
    "required_scopes",
]
