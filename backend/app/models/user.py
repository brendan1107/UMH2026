"""
User Model (Firestore Document Schema)

Collection: users/{uid}
Uses Firebase Auth UID as the document ID.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Firestore document schema for users collection."""
    uid: str = ""  # Firebase Auth UID
    email: str = ""
    full_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to Firestore-compatible dict."""
        return {
            "uid": self.uid,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "User":
        """Create User from Firestore document dict."""
        return User(
            uid=data.get("uid", ""),
            email=data.get("email", ""),
            full_name=data.get("full_name"),
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
        )

    # Firestore collection name
    COLLECTION = "users"
