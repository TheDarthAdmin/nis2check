from uuid import uuid4

from nis2check_api.database import SCHEMA_PATCHES
from nis2check_api.models import FindingRecord
from nis2check_api.onboarding import admin_consent_url
from nis2check_api.service import evidence_summary, finding_view
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


def test_finding_view_exposes_the_remediation_steps() -> None:
    record = FindingRecord(
        id=uuid4(),
        control_id="C01",
        nis2="21(2)(j)",
        domain="authentication",
        title="Conditional Access requires MFA for all users",
        verdict="FAIL",
        rationale="No policy covers every user.",
        endpoints=["/v1.0/identity/conditionalAccess/policies"],
        remediation="https://learn.microsoft.com/entra",
        remediation_steps=["Create the policy.", "Enable it."],
        limits="Policy state only.",
        object_ids=[],
        counts={},
    )

    view = finding_view(record)

    assert view["remediationSteps"] == ["Create the policy.", "Enable it."]


def test_finding_view_tolerates_a_finding_stored_before_remediation_steps_existed() -> None:
    record = FindingRecord(
        id=uuid4(),
        control_id="C01",
        nis2="21(2)(j)",
        domain="authentication",
        title="Conditional Access requires MFA for all users",
        verdict="FAIL",
        rationale="No policy covers every user.",
        endpoints=[],
        remediation="https://learn.microsoft.com/entra",
        remediation_steps=None,
        limits="Policy state only.",
        object_ids=[],
        counts={},
    )

    assert finding_view(record)["remediationSteps"] == []


def test_settings_translate_neon_database_url_for_asyncpg() -> None:
    settings = Settings(
        database_url="postgresql://user:password@example.com/database?sslmode=require&channel_binding=require",
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
    assert "scope=https%3A%2F%2Fgraph.microsoft.com%2F.default" in url
    assert "state=fixture-state" in url


def test_schema_patches_stay_idempotent() -> None:
    """They run on every start, against databases in every state this schema has had."""
    for statement in SCHEMA_PATCHES:
        assert statement.startswith("ALTER TABLE "), statement
        assert "IF NOT EXISTS" in statement, statement


def test_columns_added_after_the_first_release_are_patched_in() -> None:
    """`create_all` creates missing tables but never alters one that already exists."""
    patched = " ".join(SCHEMA_PATCHES)

    assert "findings" in patched and "remediation_steps" in patched
    assert "tenants" in patched and "consent_granted_at" in patched
