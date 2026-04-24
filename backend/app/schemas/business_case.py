"""Business case request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

CaseStatus = Literal["active", "insight_generated", "archived"]


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    businessStage: str | None = None
    status: CaseStatus = "active"


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    businessStage: str | None = None
    status: CaseStatus | None = None


class CaseResponse(BaseModel):
    id: str
    title: str
    description: str | None
    businessStage: str | None
    status: CaseStatus
    createdAt: str
    updatedAt: str


class CaseListEnvelope(BaseModel):
    data: list[CaseResponse]


class CaseEnvelope(BaseModel):
    data: CaseResponse
