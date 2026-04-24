"""
Business Case Model (Firestore Document Schema)

Collection: business_cases/{case_id}
Supports both pre-launch and existing business modes (PRD Section 4.1).
"""
# What is business_case.py for?
# The business_case.py file defines a data model for representing a business case in our application. This model, BusinessCase, includes fields for storing relevant information about a business case, such as the user ID of the creator, title, description, mode (pre-launch or existing business), business type, target location, status, and timestamps for creation and updates. By defining this model, we can easily serialize and deserialize business case data when storing it in Firestore and retrieving it for use in our application. This model serves as the core entity around which all other related data (chat sessions, extracted facts, recommendations, evidence uploads, place results) is organized in our Firestore database.

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BusinessCase:
    """Firestore document schema for business_cases collection."""
    id: str = ""
    user_id: str = ""  # Firebase Auth UID
    title: str = ""
    description: Optional[str] = None
    mode: str = "pre_launch"  # pre_launch | existing_business
    business_type: Optional[str] = None  # e.g., "western food", "cafe"
    target_location: Optional[str] = None
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "mode": self.mode,
            "business_type": self.business_type,
            "target_location": self.target_location,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "BusinessCase":
        return BusinessCase(
            id=doc_id,
            user_id=data.get("user_id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            mode=data.get("mode", "pre_launch"),
            business_type=data.get("business_type"),
            target_location=data.get("target_location"),
            status=data.get("status", "active"),
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
        )

    COLLECTION = "business_cases"
