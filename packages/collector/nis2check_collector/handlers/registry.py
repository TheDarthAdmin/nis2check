"""Small explicit registry for Python control evaluators."""

from collections.abc import Callable
from typing import Any

from ..models import HandlerResult

Handler = Callable[[dict[str, list[dict[str, Any]]], dict[str, object]], HandlerResult]
_HANDLERS: dict[str, Handler] = {}


def register(name: str) -> Callable[[Handler], Handler]:
    """Register a uniquely named control handler."""
    def decorator(handler: Handler) -> Handler:
        if name in _HANDLERS:
            raise RuntimeError(f"Handler already registered: {name}")
        _HANDLERS[name] = handler
        return handler

    return decorator


def get_handler(name: str) -> Handler:
    """Return a handler or raise a clear configuration error."""
    try:
        return _HANDLERS[name]
    except KeyError as error:
        raise LookupError(f"No handler registered for '{name}'") from error
