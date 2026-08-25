"""Built-in handler registration."""

from . import conditional_access as conditional_access  # noqa: F401 - register built-in handlers
from .registry import Handler, get_handler, register

__all__ = ["Handler", "get_handler", "register"]
