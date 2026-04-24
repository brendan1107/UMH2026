"""
Extracted Fact Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/extracted_facts/{fact_id}
Used as structured memory to manage GLM's shorter context window.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# What is extracted_fact.py for?
# The extracted_fact.py file defines a data model for representing structured facts that are extracted from user inputs, chat messages, or external data sources in relation to a business case. This model, ExtractedFact, includes fields for categorizing the fact (e.g., location, pricing, competition, finance), storing the key-value pair of the fact, indicating the confidence level (user-provided, AI-inferred, verified), and the source of the fact (user input, Google Places API, field task). By defining this model, we can easily serialize and deserialize extracted facts when storing them in Firestore and retrieving them for use in our application. These extracted facts serve as structured memory that helps us manage the GLM's shorter context window by providing concise and relevant information that can be referenced during conversations and analysis without needing to include lengthy chat histories. This allows us to maintain important information about the business case in a structured format that can be easily accessed and utilized by the AI assistant and other components of our application.

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
