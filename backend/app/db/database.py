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

import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage

from app.config import BACKEND_DIR, settings

logger = logging.getLogger(__name__)

firebase_initialization_error: Exception | None = None

credential_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
if not credential_path.is_absolute():
    credential_path = BACKEND_DIR / credential_path
db = None
bucket = None

if settings.FIREBASE_PRIVATE_KEY and settings.FIREBASE_CLIENT_EMAIL:
    try:
        # Load from env vars
        cert_dict = {
            "type": "service_account",
            "project_id": settings.FIREBASE_PROJECT_ID,
            "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
            "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": settings.FIREBASE_CLIENT_EMAIL,
            "client_id": settings.FIREBASE_CLIENT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.FIREBASE_CLIENT_EMAIL}"
        }
        _cred = credentials.Certificate(cert_dict)
        app_options = {}
        if settings.FIREBASE_STORAGE_BUCKET:
            app_options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
        _app = firebase_admin.initialize_app(_cred, app_options)

        # Firestore client
        db = firestore.client()
        logger.info("Firestore client initialized successfully from environment variables.")

        # Storage bucket
        if settings.FIREBASE_STORAGE_BUCKET:
            bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
            logger.info(
                "Firebase Storage bucket initialized: %s",
                settings.FIREBASE_STORAGE_BUCKET,
            )
        else:
            logger.warning(
                "FIREBASE_STORAGE_BUCKET is not configured. "
                "Uploads will use metadata-only fallback."
            )
    except Exception as exc:
        firebase_initialization_error = exc
        db = None
        bucket = None
        logger.error("Firebase initialization failed from env vars: %s", exc)

elif credential_path.exists():
    try:
        # Initialize Firebase Admin SDK
        _cred = credentials.Certificate(str(credential_path))
        app_options = {}
        if settings.FIREBASE_STORAGE_BUCKET:
            app_options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
        _app = firebase_admin.initialize_app(_cred, app_options)

        # Firestore client
        db = firestore.client()
        logger.info("Firestore client initialized successfully.")

        # Storage bucket
        if settings.FIREBASE_STORAGE_BUCKET:
            bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
            logger.info(
                "Firebase Storage bucket initialized: %s",
                settings.FIREBASE_STORAGE_BUCKET,
            )
        else:
            logger.warning(
                "FIREBASE_STORAGE_BUCKET is not configured. "
                "Uploads will use metadata-only fallback."
            )
    except Exception as exc:
        firebase_initialization_error = exc
        db = None
        bucket = None
        logger.error("Firebase initialization failed: %s", exc)
else:
    firebase_initialization_error = FileNotFoundError(
        f"Firebase credentials file not found: {credential_path} and environment variables not set."
    )
    logger.warning(
        "Firebase credentials file not found at '%s' and env vars not set. "
        "Using local fallback mode (no Firestore/Storage).",
        credential_path,
    )
