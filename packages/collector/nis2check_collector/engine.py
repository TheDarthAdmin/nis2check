"""Catalogue-driven collector orchestration."""

from datetime import UTC, datetime

from nis2check_catalog import ControlDefinition

from .graph import AsyncGraphClient, GraphAccessError
from .handlers import get_handler
from .models import Finding, RunResult, Verdict


class CollectorEngine:
    """Executes Graph queries and invokes pure registered handlers."""

    def __init__(self, graph: AsyncGraphClient, tool_version: str) -> None:
        self._graph = graph
        self._tool_version = tool_version

    async def run(self, tenant_id: str, controls: list[ControlDefinition]) -> RunResult:
        findings = [await self._run_control(control) for control in controls]
        return RunResult(
            tenant_id=tenant_id,
            started_at=datetime.now(UTC),
            tool_version=self._tool_version,
            findings=findings,
        )

    async def _run_control(self, control: ControlDefinition) -> Finding:
        try:
            results = {
                name: await self._graph.query(query.endpoint, paged=query.paged)
                for name, query in control.queries.items()
            }
            evaluation = get_handler(control.handler)(results, control.params)
            return self._finding(
                control,
                evaluation.verdict,
                evaluation.rationale,
                evaluation.raw_evidence,
            )
        except GraphAccessError as error:
            status = (
                f"HTTP {error.status_code}"
                if error.status_code is not None
                else "network error"
            )
            return self._finding(
                control,
                Verdict.INCONCLUSIVE,
                f"Evidence could not be read from Microsoft Graph ({status}): {error}",
                {},
            )
        except Exception as error:  # handlers must never be able to crash a full run
            return self._finding(
                control,
                Verdict.INCONCLUSIVE,
                f"Control evaluation could not be completed: {type(error).__name__}: {error}",
                {},
            )

    @staticmethod
    def _finding(
        control: ControlDefinition,
        verdict: Verdict,
        rationale: str,
        raw_evidence: dict[str, object],
    ) -> Finding:
        return Finding(
            control_id=control.id,
            nis2=control.nis2,
            domain=control.domain,
            title=control.title,
            verdict=verdict,
            rationale=rationale,
            endpoints=[query.endpoint for query in control.queries.values()],
            remediation=str(control.remediation),
            remediation_steps=list(control.remediation_steps),
            limits=control.limits,
            raw_evidence=raw_evidence,
        )
