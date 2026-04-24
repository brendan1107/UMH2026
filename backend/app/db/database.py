"""Firebase initialization with safe local fallback support."""

from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import settings

firebase_initialization_error: Exception | None = None
firebase_app = None
db = None
bucket = None

credential_path = Path(settings.FIREBASE_CREDENTIALS_PATH)

if not credential_path.exists():
    firebase_initialization_error = FileNotFoundError(
        f"Firebase credentials file not found: {credential_path}"
    )
else:
    try:
        cred = credentials.Certificate(str(credential_path))
        options = {}
        if settings.FIREBASE_STORAGE_BUCKET:
            options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET

        try:
            firebase_app = firebase_admin.get_app()
        except ValueError:
            firebase_app = firebase_admin.initialize_app(cred, options)

        db = firestore.client()
        bucket = (
            storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
            if settings.FIREBASE_STORAGE_BUCKET
            else None
        )
    except Exception as exc:
        firebase_initialization_error = exc
        firebase_app = None
        db = None
        bucket = None
