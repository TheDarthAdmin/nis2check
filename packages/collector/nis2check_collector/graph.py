"""Async, read-only Microsoft Graph client."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


class GraphAccessError(RuntimeError):
    """Graph was unavailable or denied access; includes the relevant HTTP status."""

    def __init__(self, status_code: int | None, detail: str) -> None:
        self.status_code = status_code
        super().__init__(detail)


class AsyncGraphClient:
    """A GET-only Graph client with paging and bounded 429 retry handling."""

    def __init__(
        self,
        access_token: str,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = "https://graph.microsoft.com",
        max_retries: int = 3,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self._owns_client = client is None
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        self._max_retries = max_retries
        self._sleep = sleep

    async def __aenter__(self) -> "AsyncGraphClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _retry_after(value: str | None, attempt: int) -> float:
        if value is not None:
            try:
                return max(float(value), 0.0)
            except ValueError:
                try:
                    wait = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
                    return max(wait, 0.0)
                except (TypeError, ValueError):
                    pass
        return float(2**attempt)

    async def _get(self, url: str) -> dict[str, Any]:
        request_url = f"{self._base_url}{url}" if url.startswith("/") else url
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(request_url, headers=self._headers)
            except httpx.HTTPError as error:
                raise GraphAccessError(None, f"Microsoft Graph request failed: {error}") from error
            if response.status_code == 429 and attempt < self._max_retries:
                await self._sleep(self._retry_after(response.headers.get("Retry-After"), attempt))
                continue
            if response.is_error:
                detail = response.text
                try:
                    payload = response.json()
                    detail = str(payload.get("error", {}).get("message", detail))
                except ValueError:
                    pass
                raise GraphAccessError(
                    response.status_code,
                    f"Microsoft Graph returned HTTP {response.status_code}: {detail}",
                )
            try:
                payload = response.json()
            except ValueError as error:
                raise GraphAccessError(
                    response.status_code,
                    "Microsoft Graph returned invalid JSON",
                ) from error
            if not isinstance(payload, dict):
                raise GraphAccessError(
                    response.status_code,
                    "Microsoft Graph returned an unexpected JSON value",
                )
            return payload
        raise AssertionError("unreachable")

    async def query(self, endpoint: str, *, paged: bool) -> list[dict[str, Any]]:
        """Get one endpoint, following Graph next links when configured as paged."""
        page = await self._get(endpoint)
        if not paged:
            return [page]
        results: list[dict[str, Any]] = []
        while True:
            values = page.get("value")
            if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
                raise GraphAccessError(
                    200,
                    "Microsoft Graph paged response has no object 'value' array",
                )
            results.extend(values)
            next_link = page.get("@odata.nextLink")
            if next_link is None:
                return results
            if not isinstance(next_link, str):
                raise GraphAccessError(200, "Microsoft Graph returned an invalid @odata.nextLink")
            page = await self._get(next_link)
