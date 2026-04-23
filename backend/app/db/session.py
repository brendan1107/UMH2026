"""
Firestore Session / Client Access

Provides the Firestore client for use across the application.
"""

from app.db.database import db, bucket


def get_db():
    """Return the Firestore client instance."""
    return db


def get_storage_bucket():
    """Return the Firebase Storage bucket instance."""
    return bucket
