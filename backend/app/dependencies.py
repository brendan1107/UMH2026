"""
FastAPI Dependency Injection

Provides shared dependencies such as Firestore client,
authenticated user context, and service instances.
"""

# What is dependencies.py for?
# The dependencies.py file in the app directory is responsible for defining shared dependencies that can be injected into our API route handlers using FastAPI's dependency injection system. This includes functions for accessing the Firestore client, retrieving the current authenticated user from the request context, and providing instances of our service classes (ReportService, TaskService, UploadService). By centralizing these dependencies in one file, we can easily manage and reuse them across our API routes, keeping our code organized and promoting a clear separation of concerns. This allows us to maintain clean and efficient API route handlers while delegating the underlying mechanics of database access and user authentication to these shared dependencies.

import logging

import base64
import json

from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth

from app.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)


def _decode_dev_firebase_token(token: str) -> dict | None:
    """Decode Firebase JWT claims without verification for local development only."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None

        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
        uid = claims.get("user_id") or claims.get("sub")
        if not uid:
            return None

        return {
            "uid": uid,
            "email": claims.get("email"),
            "firebase": claims.get("firebase", {}),
        }
    except Exception:
        logger.exception("Failed to decode development Firebase token.")
        return None


async def get_current_user(request: Request):
    """
    Dependency to extract and validate the current authenticated user
    using Firebase Auth ID token from the Authorization header.

    In development mode (APP_ENV=development), accepts a special test token
    "dev-bypass" to skip Firebase verification for easier local testing.
    """

    # ── Dev bypass — only works when APP_ENV=development ──
    # To use: send header  Authorization: Bearer dev-bypass
    is_development = settings.APP_ENV == "development"
    auth_header = request.headers.get("Authorization", "")
    if is_development and auth_header == "Bearer dev-bypass":
        return {"uid": "dev-user-001", "email": "dev@test.com"}

    # ── Normal Firebase auth ───────────────────────────────
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
        if is_development:
            decoded_dev_token = _decode_dev_firebase_token(token)
            if decoded_dev_token:
                logger.warning(
                    "Using unverified Firebase token claims in development for uid=%s",
                    decoded_dev_token["uid"],
                )
                return decoded_dev_token

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
