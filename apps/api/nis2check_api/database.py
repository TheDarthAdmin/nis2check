"""Database lifecycle owned by the hosted API, never by the collector."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base
from .settings import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            # Existing single-tenant previews get the multitenant consent state without data loss.
            await connection.execute(
                text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS consent_granted_at TIMESTAMP WITH TIME ZONE")
            )

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessions() as session:
            yield session

    async def close(self) -> None:
        await self.engine.dispose()
