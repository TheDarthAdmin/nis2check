"""arq task boundary for scheduled tenant runs.

Deployment injects the tenant certificate and tenant-scoped evidence policy; neither is held
by the collector nor persisted in findings.
"""

from collections.abc import Mapping
from typing import Any


async def run_scheduled_tenant_run(_: Mapping[str, Any], tenant_id: str) -> None:
    """Queue entry point; persistence and secret resolution remain in the hosted boundary."""
    # Wiring intentionally lives in deployment configuration so the collector stays pure.
    del tenant_id


class WorkerSettings:
    functions = [run_scheduled_tenant_run]
