"""Shared Firebase client accessors.

These accessors return None when Firebase is not configured so route code can fall
back to in-memory demo storage instead of failing during local development.
"""

from app.db.database import bucket, db, firebase_initialization_error


def get_db():
    """Return the Firestore client, or None when unavailable."""
    return db


def get_storage_bucket():
    """Return the Firebase Storage bucket, or None when unavailable."""
    return bucket


def get_firebase_initialization_error() -> Exception | None:
    """Expose Firebase startup details for health/debug responses."""
    return firebase_initialization_error
