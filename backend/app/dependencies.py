"""
FastAPI Dependency Injection

Provides shared dependencies such as Firestore client,
authenticated user context, and service instances.
"""

# What is dependencies.py for?
# The dependencies.py file in the app directory is responsible for defining shared dependencies that can be injected into our API route handlers using FastAPI's dependency injection system. This includes functions for accessing the Firestore client, retrieving the current authenticated user from the request context, and providing instances of our service classes (ReportService, TaskService, UploadService). By centralizing these dependencies in one file, we can easily manage and reuse them across our API routes, keeping our code organized and promoting a clear separation of concerns. This allows us to maintain clean and efficient API route handlers while delegating the underlying mechanics of database access and user authentication to these shared dependencies.

import logging

from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth

from app.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)


async def get_current_user(request: Request):
    """
    Dependency to extract and validate the current authenticated user
    using Firebase Auth ID token from the Authorization header.

    If DEV_AUTH_BYPASS=true in env, returns a fake dev user without
    requiring a real Firebase token. This MUST be disabled in production.
    """
    # ── Dev bypass (opt-in via env flag, disabled by default) ──
    if settings.DEV_AUTH_BYPASS:
        logger.warning(
            "DEV_AUTH_BYPASS is enabled — skipping Firebase token verification. "
            "Do NOT use this in production!"
        )
        return {
            "uid": "dev-user-000",
            "email": "dev@localhost",
            "name": "Dev User",
        }

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.split("Bearer ")[1]
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
