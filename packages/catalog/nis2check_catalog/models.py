"""Models for the declarative control catalogue."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scopes: list[str]
    licence: Literal["none", "entra_p1", "entra_p2", "intune"]


class QueryDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str = Field(pattern=r"^/")
    paged: bool


class ControlDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^C[0-9]{2}$")
    nis2: str
    domain: str
    title: str
    requires: Requirement
    queries: dict[str, QueryDefinition]
    handler: str
    params: dict[str, object]
    remediation: HttpUrl
    remediation_steps: list[str] = Field(min_length=1, max_length=8)
    limits: str
