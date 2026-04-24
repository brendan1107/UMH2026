"""
User Model (Firestore Document Schema)

Collection: users/{uid}
Uses Firebase Auth UID as the document ID.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

# What is user.py for?
# The user.py file defines a data model for representing users in our application. This model, User, includes fields for storing relevant information about a user, such as their Firebase Auth UID, email, full name, and timestamps for when the user document was created and last updated. By defining this model, we can easily serialize and deserialize user data when storing it in Firestore and retrieving it for use in our application. This allows us to manage user profiles effectively and link them to their associated business cases and other related data in our Firestore database. The user's UID serves as the unique identifier for their document in the "users" collection, ensuring that we can efficiently query and manage user data based on their authentication status.
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
