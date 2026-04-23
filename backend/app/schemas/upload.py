"""Evidence upload schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UploadResponse(BaseModel):
    id: str
    file_name: str
    file_type: Optional[str]
    file_size: Optional[int]
    ai_summary: Optional[str]
    analysis_status: str
    created_at: datetime

    class Config:
        from_attributes = True
