"""
FastAPI Dependency Injection

Provides shared dependencies such as Firestore client,
authenticated user context, and service instances.
"""

# What is dependencies.py for?
# The dependencies.py file in the app directory is responsible for defining shared dependencies that can be injected into our API route handlers using FastAPI's dependency injection system. This includes functions for accessing the Firestore client, retrieving the current authenticated user from the request context, and providing instances of our service classes (ReportService, TaskService, UploadService). By centralizing these dependencies in one file, we can easily manage and reuse them across our API routes, keeping our code organized and promoting a clear separation of concerns. This allows us to maintain clean and efficient API route handlers while delegating the underlying mechanics of database access and user authentication to these shared dependencies.

import os
from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth

from app.db.session import get_db


async def get_current_user(request: Request):
    """
    Dependency to extract and validate the current authenticated user
    using Firebase Auth ID token from the Authorization header.

    In development mode (APP_ENV=development), accepts a special test token
    "dev-bypass" to skip Firebase verification for easier local testing.
    """

    # ── Dev bypass — only works when APP_ENV=development ──
    # To use: send header  Authorization: Bearer dev-bypass
    if os.getenv("APP_ENV") == "development":
        auth_header = request.headers.get("Authorization", "")
        if auth_header == "Bearer dev-bypass":
            return {"uid": "dev-user-001", "email": "dev@test.com"}

    # ── Normal Firebase auth ───────────────────────────────
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
        print(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )