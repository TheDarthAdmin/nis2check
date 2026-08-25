"""Strict environment configuration for the hosted API boundary."""

from dataclasses import dataclass
from os import environ


@dataclass(frozen=True)
class Settings:
    database_url: str
    tenant_id: str
    client_id: str
    client_secret: str
    api_key: str
    evidence_hash_key: str

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.replace("sslmode=", "ssl=")
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
        return url


def get_settings() -> Settings:
    required = (
        "DATABASE_URL",
        "NIS2CHECK_TENANT_ID",
        "NIS2CHECK_CLIENT_ID",
        "NIS2CHECK_CLIENT_SECRET",
        "NIS2CHECK_API_KEY",
        "EVIDENCE_HASH_KEY",
    )
    missing = [key for key in required if not environ.get(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")
    if len(environ["NIS2CHECK_API_KEY"]) < 32 or len(environ["EVIDENCE_HASH_KEY"]) < 32:
        raise RuntimeError("NIS2CHECK_API_KEY and EVIDENCE_HASH_KEY must be at least 32 characters.")
    return Settings(
        database_url=environ["DATABASE_URL"],
        tenant_id=environ["NIS2CHECK_TENANT_ID"].lower(),
        client_id=environ["NIS2CHECK_CLIENT_ID"],
        client_secret=environ["NIS2CHECK_CLIENT_SECRET"],
        api_key=environ["NIS2CHECK_API_KEY"],
        evidence_hash_key=environ["EVIDENCE_HASH_KEY"],
    )
