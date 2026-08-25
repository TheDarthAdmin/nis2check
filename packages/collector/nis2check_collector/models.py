"""Evidence and finding models shared by all collector entry points."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCONCLUSIVE = "INCONCLUSIVE"


class HandlerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    verdict: Verdict
    rationale: str = Field(min_length=1)
    raw_evidence: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    control_id: str
    nis2: str
    domain: str
    title: str
    verdict: Verdict
    rationale: str = Field(min_length=1)
    endpoints: list[str]
    remediation: str
    limits: str
    raw_evidence: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str
    started_at: datetime
    tool_version: str
    findings: list[Finding]
