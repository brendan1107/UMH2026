"""
Recommendation Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/recommendations/{rec_id}
Final verdict values: proceed, reconsider, do_not_open, improve, pivot, shut_down.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

# What is recommendation.py for?
# The recommendation.py file defines a data model for representing the recommendations generated for a business case. This model, Recommendation, includes fields for storing the verdict (e.g., proceed, reconsider), confidence score, summary, strengths, weaknesses, action items, and the full report. By defining this model, we can easily serialize and deserialize recommendation data when storing it in Firestore and retrieving it for use in our application. This allows us to manage the recommendations effectively, track their versions, and provide detailed insights to users based on the analysis of their business cases. The recommendations are stored in a subcollection under each business case, reflecting the hierarchical relationship between these entities in our Firestore database.

@dataclass
class Recommendation:
    """Firestore document schema for recommendations subcollection."""
    id: str = ""
    case_id: str = ""
    verdict: Optional[str] = None  # proceed, reconsider, do_not_open, improve, pivot, shut_down
    confidence_score: Optional[int] = None  # 0-100
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    full_report: Optional[str] = None
    is_provisional: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "verdict": self.verdict,
            "confidence_score": self.confidence_score,
            "summary": self.summary,
            "strengths": self.strengths or [],
            "weaknesses": self.weaknesses or [],
            "action_items": self.action_items or [],
            "full_report": self.full_report,
            "is_provisional": self.is_provisional,
            "version": self.version,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "Recommendation":
        return Recommendation(
            id=doc_id,
            case_id=data.get("case_id", ""),
            verdict=data.get("verdict"),
            confidence_score=data.get("confidence_score"),
            summary=data.get("summary"),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            action_items=data.get("action_items", []),
            full_report=data.get("full_report"),
            is_provisional=data.get("is_provisional", True),
            version=data.get("version", 1),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "recommendations"
