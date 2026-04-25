"""Investigation task schemas."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Literal, Optional
from datetime import datetime

TaskStatus = Literal["pending", "completed", "skipped", "scheduled"]


class TaskCreate(BaseModel):
    """Schema for creating a new task under a case."""
    model_config = ConfigDict(populate_by_name=True)

    title: str
    description: Optional[str] = None
    type: str = "answer_questions"
    status: TaskStatus = "pending"
    action_label: Optional[str] = Field(default=None, alias="actionLabel")
    data: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"


class TaskStatusUpdate(BaseModel):
    """Schema for updating a task's status and optional submitted value."""
    model_config = ConfigDict(populate_by_name=True)

    status: TaskStatus
    submitted_value: Optional[Any] = Field(default=None, alias="submittedValue")


class TaskResponse(BaseModel):
    id: str
    case_id: str
    title: str
    description: Optional[str] = None
    type: str = "answer_questions"
    status: TaskStatus = "pending"
    action_label: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"
    submitted_value: Optional[Any] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskComplete(BaseModel):
    findings: str


class TaskSchedule(BaseModel):
    scheduled_date: datetime
    notes: Optional[str] = None
