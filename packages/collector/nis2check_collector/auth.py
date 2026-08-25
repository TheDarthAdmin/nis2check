"""MSAL-based Microsoft Graph authentication without web-server dependencies."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import msal

GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


class AuthenticationError(RuntimeError):
    """MSAL could not acquire a Graph access token."""


class MsalAuthenticator:
    """Acquire app-only certificate or delegated device-code Graph tokens."""

    def __init__(self, tenant_id: str, client_id: str, cache_path: Path | None = None) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.cache_path = cache_path

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    def _cache(self) -> msal.SerializableTokenCache:
        cache = msal.SerializableTokenCache()
        if self.cache_path is not None and self.cache_path.exists():
            cache.deserialize(self.cache_path.read_text(encoding="utf-8"))
        return cache

    def _save_cache(self, cache: msal.SerializableTokenCache) -> None:
        if self.cache_path is not None and cache.has_state_changed:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(cache.serialize(), encoding="utf-8")

    @staticmethod
    def _access_token(result: dict[str, Any]) -> str:
        token = result.get("access_token")
        if isinstance(token, str):
            return token
        description = result.get("error_description") or result.get("error") or "unknown MSAL error"
        raise AuthenticationError(f"Unable to acquire Microsoft Graph token: {description}")

    def acquire_certificate_token(self, certificate_pem: str, thumbprint: str) -> str:
        """Acquire an app-only token using a registered certificate."""
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential={"private_key": certificate_pem, "thumbprint": thumbprint},
        )
        return self._access_token(app.acquire_token_for_client([GRAPH_DEFAULT_SCOPE]))

    def acquire_device_code_token(
        self,
        scopes: list[str],
        device_code_callback: Callable[[str], None] = print,
    ) -> str:
        """Acquire and cache a delegated token via the standard device-code flow."""
        cache = self._cache()
        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=cache,
        )
        accounts = app.get_accounts()
        if accounts:
            silent = app.acquire_token_silent(scopes, account=accounts[0])
            silent_token = silent.get("access_token") if silent else None
            if isinstance(silent_token, str):
                self._save_cache(cache)
                return silent_token

        flow = app.initiate_device_flow(scopes=scopes)
        message = flow.get("message")
        if not isinstance(message, str):
            reason = flow.get("error", "unknown error")
            raise AuthenticationError(f"Unable to start device-code flow: {reason}")
        device_code_callback(message)
        result = app.acquire_token_by_device_flow(flow)
        self._save_cache(cache)
        return self._access_token(result)
