import json
from pathlib import Path

import httpx
import pytest
import respx
from nis2check_catalog import load_control
from nis2check_collector.engine import CollectorEngine
from nis2check_collector.graph import AsyncGraphClient
from nis2check_collector.models import Verdict

ROOT = Path(__file__).parent
CONTROL = load_control(Path("packages/catalog/controls/C01.yaml"))
ENDPOINT = "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies"


def fixture(name: str) -> dict[str, object]:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("c01_pass.json", Verdict.PASS),
        ("c01_partial.json", Verdict.PARTIAL),
        ("c01_fail.json", Verdict.FAIL),
    ],
)
@respx.mock
async def test_c01_verdicts(response: str, expected: Verdict) -> None:
    respx.get(ENDPOINT).respond(200, json=fixture(response))
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [CONTROL])
        finding = run.findings[0]

    assert finding.verdict is expected
    assert finding.raw_evidence["policies"]


@respx.mock
async def test_c01_turns_graph_denial_into_inconclusive() -> None:
    respx.get(ENDPOINT).respond(403, json={"error": {"message": "Access denied"}})
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        run = await CollectorEngine(graph, "test").run("fixture-tenant", [CONTROL])
        finding = run.findings[0]

    assert finding.verdict is Verdict.INCONCLUSIVE
    assert "HTTP 403" in finding.rationale
