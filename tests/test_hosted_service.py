from nis2check_api.service import evidence_summary
from nis2check_api.settings import Settings


def test_evidence_summary_stores_only_counts_and_keyed_pseudonyms() -> None:
    settings = Settings(
        database_url="postgresql://example",
        tenant_id="fixture-tenant",
        client_id="fixture-client",
        client_secret="fixture-secret",
        api_key="a" * 32,
        evidence_hash_key="b" * 32,
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
        tenant_id="fixture-tenant",
        client_id="fixture-client",
        client_secret="fixture-secret",
        api_key="a" * 32,
        evidence_hash_key="b" * 32,
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+asyncpg://user:password@example.com/database?ssl=require"
    )
