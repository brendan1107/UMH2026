"""
Firebase Initialization

Configures Firebase Admin SDK for Firestore and Storage.
Replaces SQLAlchemy/PostgreSQL — Firestore is a NoSQL document database.
"""

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import settings

# Initialize Firebase Admin SDK
_cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
_app = firebase_admin.initialize_app(_cred, {
    "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
})

# Firestore client
db = firestore.client()

# Storage bucket
bucket = storage.bucket()
