"""Investigation task request and response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "completed", "skipped", "scheduled"]
TaskType = Literal[
    "answer_questions",
    "choose_option",
    "upload_file",
    "upload_image",
    "provide_text_input",
    "review_ai_suggestions",
    "analyze_competitors",
]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    type: TaskType = "provide_text_input"
    status: TaskStatus = "pending"
    actionLabel: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    type: TaskType | None = None
    status: TaskStatus | None = None
    actionLabel: str | None = None


class TaskResponse(BaseModel):
    id: str
    caseId: str
    title: str
    description: str | None
    type: TaskType
    status: TaskStatus
    actionLabel: str | None
    createdAt: str
    updatedAt: str


class TaskListEnvelope(BaseModel):
    data: list[TaskResponse]


class TaskEnvelope(BaseModel):
    data: TaskResponse
