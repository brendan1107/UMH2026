"""
Firebase Initialization

Configures Firebase Admin SDK for Firestore and Storage.
Replaces SQLAlchemy/PostgreSQL — Firestore is a NoSQL document database.
"""
# What is /backend/app/db directory for?
# The /backend/app/db directory contains the database configuration and initialization
#  code for our application. In this case, we are using Firebase Firestore as our 
# database, so this directory includes the setup for the Firebase Admin SDK, which 
# allows us to interact with Firestore and Firebase Storage.

# What is this database.py file for?
# The database.py file is responsible for initializing the Firebase Admin SDK with the
#  necessary credentials and configuration. It sets up the Firestore client and the
#  Firebase Storage bucket that we will use throughout our application to manage data
#  and file uploads. By centralizing this initialization in one file, we can easily 
# import the Firestore client and Storage bucket in our API route handlers and other 
# parts of the application without having to repeat the initialization code. This 
# promotes code reuse and keeps our database access organized.

from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import settings

firebase_initialization_error: Exception | None = None

credential_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
db = None
bucket = None

if credential_path.exists():
    try:
        # Initialize Firebase Admin SDK
        _cred = credentials.Certificate(str(credential_path))
        app_options = {}
        if settings.FIREBASE_STORAGE_BUCKET:
            app_options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
        _app = firebase_admin.initialize_app(_cred, app_options)

        # Firestore client
        db = firestore.client()

        # Storage bucket
        if settings.FIREBASE_STORAGE_BUCKET:
            bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
        else:
            firebase_initialization_error = ValueError(
                "FIREBASE_STORAGE_BUCKET is not configured. Set it in "
                "backend/.env or backend/.env.backend."
            )
    except Exception as exc:
        firebase_initialization_error = exc
        db = None
        bucket = None
else:
    firebase_initialization_error = FileNotFoundError(
        f"Firebase credentials file not found: {credential_path}"
    )
