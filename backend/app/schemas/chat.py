"""Chat request/response schemas."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    content: str
    attachments: Optional[List[str]] = None  # Upload IDs


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class AIResponse(BaseModel):
    """Structured AI response from orchestration."""
    message: str
    follow_up_questions: Optional[List[str]] = None
    extracted_facts: Optional[List[dict]] = None
    generated_tasks: Optional[List[dict]] = None
    recommendation_update: Optional[dict] = None
