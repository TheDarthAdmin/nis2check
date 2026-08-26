"""Database lifecycle owned by the hosted API, never by the collector."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base
from .settings import Settings

#: `create_all` creates missing tables but never alters an existing one, so every column added
#: after a deployment went live is applied here as well. Each statement must stay idempotent:
#: it runs on every start, against databases in any of the states this schema has had.
SCHEMA_PATCHES = (
    # Existing single-tenant previews get the multitenant consent state without data loss.
    "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS consent_granted_at TIMESTAMP WITH TIME ZONE",
    # Findings stored before the catalogue carried remediation steps keep an empty list.
    "ALTER TABLE findings ADD COLUMN IF NOT EXISTS remediation_steps JSONB NOT NULL DEFAULT '[]'::jsonb",
)


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            for statement in SCHEMA_PATCHES:
                await connection.execute(text(statement))

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessions() as session:
            yield session

    async def close(self) -> None:
        await self.engine.dispose()
