"""Investigation task schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    """Schema for creating a new task under a case."""
    title: str
    description: Optional[str] = None
    type: str = "answer_questions"
    status: str = "pending"
    actionLabel: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    """Schema for updating a task's status."""
    status: str  # pending | completed | skipped | scheduled


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
