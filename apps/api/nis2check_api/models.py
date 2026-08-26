"""Tenant-isolated hosted persistence model.

Raw Graph evidence is deliberately absent from findings. Optional encrypted evidence is
stored separately with expiry so normal application queries never receive it by accident.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    entra_tenant_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    evidence_retention_enabled: Mapped[bool] = mapped_column(default=False)
    consent_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_tenant_created", "tenant_id", "created_at"),
        Index(
            "uq_runs_one_active_per_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    collector_version: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FindingRecord(Base):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_tenant_run_control", "tenant_id", "run_id", "control_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    control_id: Mapped[str] = mapped_column(String(8), nullable=False)
    nis2: Mapped[str] = mapped_column(String(32), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    endpoints: Mapped[list[str]] = mapped_column(JSONB, default=list)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_steps: Mapped[list[str]] = mapped_column(JSONB, default=list)
    limits: Mapped[str] = mapped_column(Text, nullable=False)
    object_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    counts: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)


class EncryptedEvidence(Base):
    __tablename__ = "encrypted_evidence"
    __table_args__ = (Index("ix_evidence_tenant_expires", "tenant_id", "expires_at"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    finding_id: Mapped[UUID] = mapped_column(ForeignKey("findings.id"), nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    key_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
