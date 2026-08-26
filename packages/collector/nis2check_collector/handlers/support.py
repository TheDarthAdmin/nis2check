"""Shared helpers for control handlers.

Handlers stay pure: they read the Graph responses they were given, and report only what
those responses prove. Anything unreadable becomes INCONCLUSIVE with the reason attached.
"""

from datetime import UTC, datetime
from typing import Any

from ..models import HandlerResult, Verdict

Results = dict[str, list[dict[str, Any]]]


def result(verdict: Verdict, rationale: str, results: Results) -> HandlerResult:
    """Build a handler result that keeps the raw Graph responses beside the interpretation."""
    return HandlerResult(verdict=verdict, rationale=rationale, raw_evidence=results)


def unreadable(reason: str, results: Results) -> HandlerResult:
    """Report missing or unexpected data instead of assuming what it would have said."""
    return result(Verdict.INCONCLUSIVE, reason, results)


def integer_param(params: dict[str, object], key: str, default: int) -> int:
    value = params.get(key, default)
    return value if isinstance(value, int) else default


def string_list_param(params: dict[str, object], key: str, default: list[str]) -> list[str]:
    value = params.get(key, default)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [str(item) for item in value]
    return default


def single_object(results: Results, name: str) -> dict[str, Any] | None:
    """The body of a non-paged query, unwrapping the `value` envelope Graph uses for some settings."""
    pages = results.get(name) or []
    if not pages or not isinstance(pages[0], dict):
        return None
    body = pages[0].get("value", pages[0])
    return body if isinstance(body, dict) else None


def timestamp(value: object) -> datetime | None:
    """Parse a Graph timestamp, or None when it is absent or malformed."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
