from nis2check_api.onboarding import admin_consent_url
from nis2check_api.service import evidence_summary
from nis2check_api.settings import Settings


def test_evidence_summary_stores_only_counts_and_keyed_pseudonyms() -> None:
    settings = Settings(
        database_url="postgresql://example",
        client_id="fixture-client",
        client_secret="fixture-secret",
        api_key="a" * 32,
        evidence_hash_key="b" * 32,
        cron_secret="c" * 32,
    )

    object_ids, counts = evidence_summary(
        {
            "policies": [
                {"id": "policy-1", "displayName": "Do not retain this"},
                {"id": "policy-2", "excludeUsers": ["user-1"]},
            ]
        },
        settings,
    )

    assert counts == {"policies": 2}
    assert len(object_ids) == 3
    assert all(item.startswith("hmac-sha256:") for item in object_ids)
    assert all("policy" not in item and "user" not in item for item in object_ids)


def test_settings_translate_neon_database_url_for_asyncpg() -> None:
    settings = Settings(
        database_url="postgresql://user:password@example.com/database?sslmode=require",
        client_id="fixture-client",
        client_secret="fixture-secret",
        api_key="a" * 32,
        evidence_hash_key="b" * 32,
        cron_secret="c" * 32,
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+asyncpg://user:password@example.com/database?ssl=require"
    )


def test_admin_consent_url_is_scoped_to_the_signed_in_tenant() -> None:
    url = admin_consent_url(
        "0f0e0d0c-0b0a-4908-8706-050403020100",
        "fixture-client",
        "https://app.example/api/onboarding/callback/microsoft",
        "fixture-state",
    )

    assert url.startswith("https://login.microsoftonline.com/0f0e0d0c-0b0a-4908-8706-050403020100/")
    assert "client_id=fixture-client" in url
    assert "state=fixture-state" in url
