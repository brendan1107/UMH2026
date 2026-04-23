"""Business case request/response schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    mode: str = "pre_launch"  # pre_launch | existing_business
    business_type: Optional[str] = None
    target_location: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    mode: str
    business_type: Optional[str]
    target_location: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
