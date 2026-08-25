"""Pure, read-only Microsoft Graph evidence collector."""

from .engine import CollectorEngine
from .models import Finding, RunResult, Verdict

__all__ = ["CollectorEngine", "Finding", "RunResult", "Verdict"]
