"""Hosted API: tenant-scoped persistence around the pure, read-only collector."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from secrets import compare_digest
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Database
from .service import (
    ActiveRunError,
    CollectionError,
    compare_runs,
    create_run,
    get_run,
    list_findings,
    list_runs,
    run_view,
)
from .settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    database = Database(settings)
    await database.create_tables()
    app.state.settings = settings
    app.state.database = database
    yield
    await database.close()


app = FastAPI(title="Nis2Check API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


async def session(request: Request) -> AsyncIterator[AsyncSession]:
    async for item in request.app.state.database.session():
        yield item


async def authorize(
    request: Request, x_nis2check_api_key: Annotated[str | None, Header()] = None
) -> None:
    if x_nis2check_api_key is None or not compare_digest(x_nis2check_api_key, settings(request).api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")


@app.get("/v1/runs", dependencies=[Depends(authorize)])
async def read_runs(
    request: Request, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, object]:
    return {"runs": await list_runs(database_session, settings(request))}


@app.post("/v1/runs", dependencies=[Depends(authorize)], status_code=status.HTTP_201_CREATED)
async def start_run(
    request: Request,
    database_session: Annotated[AsyncSession, Depends(session)],
    source: Literal["manual", "scheduled"] = "manual",
) -> dict[str, object]:
    try:
        return await create_run(database_session, settings(request), source)
    except ActiveRunError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except CollectionError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@app.get("/api/cron")
async def start_vercel_cron(
    request: Request, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, object]:
    if request.headers.get("authorization") != f"Bearer {settings(request).cron_secret}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")
    try:
        return await create_run(database_session, settings(request), "scheduled")
    except ActiveRunError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except CollectionError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@app.get("/v1/runs/{run_id}", dependencies=[Depends(authorize)])
async def read_run(
    request: Request, run_id: UUID, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, object]:
    run = await get_run(database_session, settings(request), run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run_view(run)


@app.get("/v1/runs/{run_id}/findings", dependencies=[Depends(authorize)])
async def read_findings(
    request: Request, run_id: UUID, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, object]:
    if await get_run(database_session, settings(request), run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return {"findings": await list_findings(database_session, settings(request), run_id)}


@app.get("/v1/runs/{left_run_id}/compare/{right_run_id}", dependencies=[Depends(authorize)])
async def read_comparison(
    request: Request,
    left_run_id: UUID,
    right_run_id: UUID,
    database_session: Annotated[AsyncSession, Depends(session)],
) -> dict[str, object]:
    if left_run_id == right_run_id:
        raise HTTPException(status_code=400, detail="Choose two different runs to compare.")
    if await get_run(database_session, settings(request), left_run_id) is None or await get_run(
        database_session, settings(request), right_run_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return {
        "from": str(left_run_id),
        "to": str(right_run_id),
        "findings": await compare_runs(database_session, settings(request), left_run_id, right_run_id),
    }
