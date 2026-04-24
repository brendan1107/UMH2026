"""
FastAPI Dependency Injection

Provides shared dependencies such as Firestore client,
authenticated user context, and service instances.
"""

from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth as firebase_auth

from app.db.session import get_db


async def get_current_user(request: Request):
    """
    Dependency to extract and validate the current authenticated user
    using Firebase Auth ID token from the Authorization header.
    """
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
