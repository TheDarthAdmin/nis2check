"""Hosted orchestration: tenant-scoped Graph access and pseudonymous persistence."""

import asyncio
import hashlib
import hmac
from collections.abc import Iterable
from datetime import UTC, datetime, time
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import UUID

from nis2check_catalog import load_catalog
from nis2check_collector.auth import AuthenticationError, MsalAuthenticator
from nis2check_collector.engine import CollectorEngine
from nis2check_collector.graph import AsyncGraphClient
from nis2check_collector.models import Finding, RunResult
from sqlalchemy import Select, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import FindingRecord, Organization, Run, Tenant
from .settings import Settings

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "packages" / "catalog" / "controls"


class ActiveRunError(RuntimeError):
    """A collection is already in progress for this tenant."""


class CollectionError(RuntimeError):
    """The app-only credential could not collect the tenant evidence."""


class ConsentRequiredError(RuntimeError):
    """The tenant administrator has not granted Graph application consent."""


async def get_tenant(session: AsyncSession, entra_tenant_id: str) -> Tenant | None:
    result: Tenant | None = await session.scalar(
        select(Tenant).where(Tenant.entra_tenant_id == entra_tenant_id.lower())
    )
    return result


async def record_admin_consent(session: AsyncSession, entra_tenant_id: str) -> Tenant:
    """Create the tenant workspace only after a verified admin-consent callback."""
    tenant = await get_tenant(session, entra_tenant_id)
    if tenant is None:
        # Do not store an organization display name or user identity from Entra.
        organization = Organization(name="Microsoft 365 tenant")
        session.add(organization)
        await session.flush()
        tenant = Tenant(organization_id=organization.id, entra_tenant_id=entra_tenant_id.lower())
        session.add(tenant)
    tenant.consent_granted_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(tenant)
    return tenant


def tenant_view(tenant: Tenant | None, entra_tenant_id: str) -> dict[str, object]:
    return {
        "tenantId": entra_tenant_id.lower(),
        "consentGranted": bool(tenant and tenant.consent_granted_at),
        "consentedAt": tenant.consent_granted_at.isoformat()
        if tenant and tenant.consent_granted_at
        else None,
    }


def _pseudonymize(value: str, settings: Settings) -> str:
    digest = hmac.new(
        settings.evidence_hash_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"hmac-sha256:{digest}"


def _id_values(value: object, key: str | None = None) -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            yield from _id_values(child_value, child_key)
    elif isinstance(value, list):
        for item in value:
            yield from _id_values(item, key)
    elif (
        isinstance(value, str)
        and key is not None
        and (key.lower().endswith("id") or key.lower() == "excludeusers")
    ):
        yield value


def evidence_summary(raw_evidence: dict[str, Any], settings: Settings) -> tuple[list[str], dict[str, int]]:
    """Keep counts and keyed pseudonyms; raw Graph payloads never enter the database."""
    object_ids = sorted({_pseudonymize(value, settings) for value in _id_values(raw_evidence)})
    counts = {name: len(value) for name, value in raw_evidence.items() if isinstance(value, list)}
    return object_ids, counts


async def _collect(settings: Settings, tenant: Tenant) -> RunResult:
    try:
        token = await asyncio.to_thread(
            MsalAuthenticator(tenant.entra_tenant_id, settings.client_id).acquire_client_secret_token,
            settings.client_secret,
        )
    except AuthenticationError as error:
        raise CollectionError(str(error)) from error
    except Exception as error:
        raise CollectionError("Unable to acquire the Microsoft Graph application token.") from error
    async with AsyncGraphClient(token) as graph:
        return await CollectorEngine(graph, version("nis2check")).run(
            tenant.entra_tenant_id, load_catalog(CATALOGUE)
        )


async def create_run(
    session: AsyncSession, settings: Settings, tenant: Tenant, source: str = "manual"
) -> dict[str, object]:
    if tenant.consent_granted_at is None:
        raise ConsentRequiredError("A tenant administrator must grant Microsoft Graph consent first.")
    if source == "scheduled":
        today = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        existing = await session.scalar(
            select(Run).where(
                Run.tenant_id == tenant.id,
                Run.source == "scheduled",
                Run.created_at >= today,
            )
        )
        if existing is not None:
            raise ActiveRunError("Today's scheduled tenant collection has already run.")
    run = Run(tenant_id=tenant.id, status="RUNNING", source=source, collector_version="0.1.0")
    session.add(run)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ActiveRunError("A tenant collection is already in progress.") from error
    await session.refresh(run)
    try:
        result = await _collect(settings, tenant)
    except CollectionError as error:
        run.status = "FAILED"
        run.failure_reason = str(error)
        run.completed_at = datetime.now(UTC)
        await session.commit()
        raise

    for finding in result.findings:
        object_ids, counts = evidence_summary(finding.raw_evidence, settings)
        session.add(_finding_record(run, tenant, finding, object_ids, counts))
    run.status = "COMPLETE"
    run.collector_version = result.tool_version
    run.completed_at = datetime.now(UTC)
    await session.commit()
    return run_view(run)


async def create_scheduled_runs(session: AsyncSession, settings: Settings) -> dict[str, int]:
    tenants = (
        await session.scalars(
            select(Tenant).where(Tenant.consent_granted_at.is_not(None)).order_by(Tenant.created_at)
        )
    ).all()
    started = 0
    skipped = 0
    failed = 0
    for tenant in tenants:
        try:
            await create_run(session, settings, tenant, "scheduled")
            started += 1
        except ActiveRunError:
            skipped += 1
        except CollectionError:
            failed += 1
    return {"started": started, "skipped": skipped, "failed": failed}


def _finding_record(
    run: Run, tenant: Tenant, finding: Finding, object_ids: list[str], counts: dict[str, int]
) -> FindingRecord:
    return FindingRecord(
        tenant_id=tenant.id,
        run_id=run.id,
        control_id=finding.control_id,
        nis2=finding.nis2,
        domain=finding.domain,
        title=finding.title,
        verdict=finding.verdict,
        rationale=finding.rationale,
        endpoints=finding.endpoints,
        remediation=finding.remediation,
        limits=finding.limits,
        object_ids=object_ids,
        counts=counts,
    )


def run_view(run: Run) -> dict[str, object]:
    return {
        "id": str(run.id),
        "status": run.status,
        "source": run.source,
        "collectorVersion": run.collector_version,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "completedAt": run.completed_at.isoformat() if run.completed_at else None,
        "failureReason": run.failure_reason,
    }


def finding_view(finding: FindingRecord) -> dict[str, object]:
    return {
        "id": str(finding.id),
        "controlId": finding.control_id,
        "nis2": finding.nis2,
        "domain": finding.domain,
        "title": finding.title,
        "verdict": finding.verdict,
        "rationale": finding.rationale,
        "endpoints": finding.endpoints,
        "remediation": finding.remediation,
        "limits": finding.limits,
        "objectIds": finding.object_ids,
        "counts": finding.counts,
    }


async def list_runs(session: AsyncSession, tenant: Tenant, limit: int = 20) -> list[dict[str, object]]:
    query: Select[tuple[Run]] = (
        select(Run).where(Run.tenant_id == tenant.id).order_by(desc(Run.created_at)).limit(limit)
    )
    return [run_view(run) for run in (await session.scalars(query)).all()]


async def get_run(session: AsyncSession, tenant: Tenant, run_id: UUID) -> Run | None:
    result = await session.scalars(select(Run).where(Run.id == run_id, Run.tenant_id == tenant.id))
    return result.one_or_none()


async def list_findings(
    session: AsyncSession, tenant: Tenant, run_id: UUID
) -> list[dict[str, object]]:
    run = await get_run(session, tenant, run_id)
    if run is None:
        return []
    query: Select[tuple[FindingRecord]] = (
        select(FindingRecord)
        .where(FindingRecord.run_id == run.id, FindingRecord.tenant_id == tenant.id)
        .order_by(FindingRecord.control_id)
    )
    return [finding_view(finding) for finding in (await session.scalars(query)).all()]


async def compare_runs(
    session: AsyncSession, tenant: Tenant, left_run_id: UUID, right_run_id: UUID
) -> list[dict[str, object]]:
    left = {str(item["controlId"]): item for item in await list_findings(session, tenant, left_run_id)}
    right = {
        str(item["controlId"]): item for item in await list_findings(session, tenant, right_run_id)
    }
    return [
        {
            "controlId": control_id,
            "previous": left.get(control_id),
            "current": right.get(control_id),
            "change": _change(left.get(control_id), right.get(control_id)),
        }
        for control_id in sorted(set(left) | set(right))
    ]


def _change(previous: dict[str, object] | None, current: dict[str, object] | None) -> str:
    if previous is None:
        return "NEW"
    if current is None:
        return "REMOVED"
    if previous["verdict"] == current["verdict"]:
        return "UNCHANGED"
    return "CHANGED"
