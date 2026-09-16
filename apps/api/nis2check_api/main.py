"""Hosted API: authenticated tenant-scoped persistence around the pure collector."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Database
from .models import Tenant
from .service import (
    ActiveRunError,
    CollectionError,
    ConsentRequiredError,
    DossierUnavailableError,
    ProfileError,
    build_dossier,
    compare_runs,
    create_run,
    create_scheduled_runs,
    get_profile,
    get_run,
    get_tenant,
    list_findings,
    list_runs,
    profile_view,
    record_admin_consent,
    run_view,
    save_profile,
    sector_options,
    tenant_view,
)
from .settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app_settings = get_settings()
    database = Database(app_settings)
    await database.create_tables()
    app.state.settings = app_settings
    app.state.database = database
    yield
    await database.close()


app = FastAPI(title="Nis2Check API", version="0.2.0", lifespan=lifespan)


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


def normalized_tenant_id(value: str | None) -> str:
    try:
        return str(UUID(value or "")).lower()
    except ValueError as error:
        raise HTTPException(status_code=400, detail="A valid tenant context is required.") from error


async def tenant_context(
    database_session: Annotated[AsyncSession, Depends(session)],
    x_nis2check_tenant_id: Annotated[str | None, Header()] = None,
) -> Tenant:
    tenant = await get_tenant(database_session, normalized_tenant_id(x_nis2check_tenant_id))
    if tenant is None or tenant.consent_granted_at is None:
        raise HTTPException(status_code=403, detail="Tenant administrator consent is required.")
    return tenant


@app.get("/v1/tenants/{tenant_id}", dependencies=[Depends(authorize)])
async def read_tenant_status(
    tenant_id: str, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, object]:
    normalized = normalized_tenant_id(tenant_id)
    return tenant_view(await get_tenant(database_session, normalized), normalized)


@app.post("/v1/tenants/{tenant_id}/consent", dependencies=[Depends(authorize)])
async def complete_admin_consent(
    tenant_id: str, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, object]:
    tenant = await record_admin_consent(database_session, normalized_tenant_id(tenant_id))
    return tenant_view(tenant, tenant.entra_tenant_id)


@app.get("/v1/sectors", dependencies=[Depends(authorize)])
async def read_sectors() -> dict[str, object]:
    """The annex I and annex II activities a tenant can declare. Catalogue data, not tenant data."""
    return {"sectors": sector_options()}


@app.get("/v1/tenants/{tenant_id}/profile", dependencies=[Depends(authorize)])
async def read_profile(
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
) -> dict[str, object]:
    return profile_view(await get_profile(database_session, tenant))


@app.put("/v1/tenants/{tenant_id}/profile", dependencies=[Depends(authorize)])
async def write_profile(
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
    declared: Annotated[dict[str, object], Body()],
) -> dict[str, object]:
    try:
        return await save_profile(database_session, tenant, declared)
    except ProfileError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@app.get("/v1/runs/{run_id}/dossier", dependencies=[Depends(authorize)])
async def read_dossier(
    run_id: UUID,
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
    format: str = "pdf",
) -> Response:
    """The downloadable evidence dossier for a completed run.

    HTML always works. PDF needs WeasyPrint's system libraries, so a deployment without them
    gets a 503 that names what is missing rather than a broken download.
    """
    if format not in {"pdf", "html"}:
        raise HTTPException(status_code=400, detail="Choose format=pdf or format=html.")
    try:
        body, media_type, filename = await build_dossier(
            database_session, tenant, run_id, want_pdf=format == "pdf"
        )
    except DossierUnavailableError as error:
        message = str(error)
        code = (
            status.HTTP_404_NOT_FOUND
            if message == "Run not found."
            else status.HTTP_503_SERVICE_UNAVAILABLE
            if "WeasyPrint" in message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=message) from error
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/v1/runs", dependencies=[Depends(authorize)])
async def read_runs(
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
) -> dict[str, object]:
    return {"runs": await list_runs(database_session, tenant)}


@app.post("/v1/runs", dependencies=[Depends(authorize)], status_code=status.HTTP_201_CREATED)
async def start_run(
    request: Request,
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
) -> dict[str, object]:
    try:
        return await create_run(database_session, settings(request), tenant)
    except ActiveRunError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except (CollectionError, ConsentRequiredError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@app.post("/v1/scheduled-runs", dependencies=[Depends(authorize)])
async def start_scheduled_runs(
    request: Request, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, int]:
    return await create_scheduled_runs(database_session, settings(request))


@app.get("/api/cron")
async def start_vercel_cron(
    request: Request, database_session: Annotated[AsyncSession, Depends(session)]
) -> dict[str, int]:
    if request.headers.get("authorization") != f"Bearer {settings(request).cron_secret}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")
    return await create_scheduled_runs(database_session, settings(request))


@app.get("/v1/runs/{run_id}", dependencies=[Depends(authorize)])
async def read_run(
    run_id: UUID,
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
) -> dict[str, object]:
    run = await get_run(database_session, tenant, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run_view(run)


@app.get("/v1/runs/{run_id}/findings", dependencies=[Depends(authorize)])
async def read_findings(
    run_id: UUID,
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
) -> dict[str, object]:
    if await get_run(database_session, tenant, run_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return {"findings": await list_findings(database_session, tenant, run_id)}


@app.get("/v1/runs/{left_run_id}/compare/{right_run_id}", dependencies=[Depends(authorize)])
async def read_comparison(
    left_run_id: UUID,
    right_run_id: UUID,
    database_session: Annotated[AsyncSession, Depends(session)],
    tenant: Annotated[Tenant, Depends(tenant_context)],
) -> dict[str, object]:
    if left_run_id == right_run_id:
        raise HTTPException(status_code=400, detail="Choose two different runs to compare.")
    if await get_run(database_session, tenant, left_run_id) is None or await get_run(
        database_session, tenant, right_run_id
    ) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return {
        "from": str(left_run_id),
        "to": str(right_run_id),
        "findings": await compare_runs(database_session, tenant, left_run_id, right_run_id),
    }
