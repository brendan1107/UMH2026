"""Report and recommendation schemas."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RecommendationResponse(BaseModel):
    id: str
    verdict: Optional[str]
    confidence_score: Optional[int]
    summary: Optional[str]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    action_items: Optional[List[str]]
    is_provisional: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True
