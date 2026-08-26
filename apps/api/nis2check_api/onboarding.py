"""Multi-tenant Entra admin-consent onboarding primitives."""

from urllib.parse import urlencode


def admin_consent_url(tenant_id: str, client_id: str, redirect_uri: str, state: str) -> str:
    """Create the Microsoft identity platform admin-consent URL for a tenant."""
    query = urlencode({"client_id": client_id, "redirect_uri": redirect_uri, "state": state})
    return f"https://login.microsoftonline.com/{tenant_id}/v2.0/adminconsent?{query}"
