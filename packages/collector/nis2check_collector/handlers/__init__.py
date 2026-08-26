"""Built-in handler registration."""

from . import conditional_access as conditional_access  # noqa: F401 - register built-in handlers
from . import governance_controls as governance_controls  # noqa: F401 - register built-in handlers
from . import standard_controls as standard_controls  # noqa: F401 - register built-in handlers
from .registry import Handler, get_handler, register

__all__ = ["Handler", "get_handler", "register"]
