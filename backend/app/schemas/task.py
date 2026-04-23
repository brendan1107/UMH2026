"""Investigation task schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    location: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]

    class Config:
        from_attributes = True


class TaskComplete(BaseModel):
    findings: str


class TaskSchedule(BaseModel):
    scheduled_date: datetime
    notes: Optional[str] = None
