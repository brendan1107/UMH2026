"""
Extracted Fact Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/extracted_facts/{fact_id}
Used as structured memory to manage GLM's shorter context window.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ExtractedFact:
    """Firestore document schema for extracted_facts subcollection."""
    id: str = ""
    case_id: str = ""
    category: Optional[str] = None  # "location", "pricing", "competition", "finance"
    key: str = ""
    value: str = ""
    confidence: str = "user_provided"  # user_provided, ai_inferred, verified
    source: Optional[str] = None  # "user_input", "google_places", "field_task"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "ExtractedFact":
        return ExtractedFact(
            id=doc_id,
            case_id=data.get("case_id", ""),
            category=data.get("category"),
            key=data.get("key", ""),
            value=data.get("value", ""),
            confidence=data.get("confidence", "user_provided"),
            source=data.get("source"),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "extracted_facts"
