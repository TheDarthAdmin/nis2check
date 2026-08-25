from pathlib import Path
from unittest.mock import MagicMock, patch

from nis2check_collector.auth import GRAPH_DEFAULT_SCOPE, MsalAuthenticator


@patch("nis2check_collector.auth.msal.ConfidentialClientApplication")
def test_certificate_auth_uses_graph_default_scope(application: MagicMock) -> None:
    application.return_value.acquire_token_for_client.return_value = {
        "access_token": "fixture-token"
    }
    auth = MsalAuthenticator("fixture-tenant", "fixture-client")

    token = auth.acquire_certificate_token("fixture-pem", "fixture-thumbprint")

    assert token == "fixture-token"
    application.return_value.acquire_token_for_client.assert_called_once_with([GRAPH_DEFAULT_SCOPE])
    assert application.call_args.kwargs["client_credential"] == {
        "private_key": "fixture-pem",
        "thumbprint": "fixture-thumbprint",
    }


@patch("nis2check_collector.auth.msal.PublicClientApplication")
def test_device_code_auth_displays_flow_message(application: MagicMock, tmp_path: Path) -> None:
    application.return_value.get_accounts.return_value = []
    application.return_value.initiate_device_flow.return_value = {"message": "fixture-code"}
    application.return_value.acquire_token_by_device_flow.return_value = {
        "access_token": "fixture-token"
    }
    messages: list[str] = []
    auth = MsalAuthenticator("fixture-tenant", "fixture-client", tmp_path / "token.msal-cache.json")

    token = auth.acquire_device_code_token(["Policy.Read.All"], messages.append)

    assert token == "fixture-token"
    assert messages == ["fixture-code"]
