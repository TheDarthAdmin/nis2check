import httpx
import pytest
import respx
from nis2check_collector.graph import AsyncGraphClient, GraphAccessError


@respx.mock
async def test_graph_follows_paging_links() -> None:
    first = "https://graph.microsoft.com/v1.0/example"
    second = "https://graph.microsoft.com/v1.0/example/page-2"
    respx.get(first).respond(200, json={"value": [{"id": "one"}], "@odata.nextLink": second})
    respx.get(second).respond(200, json={"value": [{"id": "two"}]})
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        result = await graph.query("/v1.0/example", paged=True)

    assert result == [{"id": "one"}, {"id": "two"}]


@respx.mock
async def test_graph_retries_retry_after() -> None:
    url = "https://graph.microsoft.com/v1.0/example"
    route = respx.get(url)
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json={"value": []}),
    ]
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        result = await graph.query("/v1.0/example", paged=True)

    assert result == []
    assert route.call_count == 2


@respx.mock
async def test_graph_error_preserves_http_status() -> None:
    respx.get("https://graph.microsoft.com/v1.0/example").respond(
        403,
        json={"error": {"message": "Denied"}},
    )
    async with httpx.AsyncClient() as http_client:
        graph = AsyncGraphClient("fixture-token", client=http_client)
        with pytest.raises(GraphAccessError) as raised:
            await graph.query("/v1.0/example", paged=True)

    assert raised.value.status_code == 403
