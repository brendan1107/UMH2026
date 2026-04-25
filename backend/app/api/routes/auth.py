"""
Authentication Routes

Handles user authentication verification and session management.
Firebase Auth is handled on the frontend — these endpoints verify tokens
and sync user profile data to Firestore.
"""
# What is route?
# A route in a web application is an endpoint that defines how the application responds 
# to a specific HTTP request (like GET, POST, etc.) at a particular URL path. In this 
# context, the auth.py file defines routes for user authentication, such as registering
# a new user, logging in, and logging out. Each route corresponds to a specific 
# function that processes the incoming request and returns an appropriate response, 
# such as a success message or an authentication token.

# This file defines the API endpoints for user authentication, including:
# - /me: Returns the current authenticated user's profile.
# - /session: Syncs the frontend Firebase Auth user to Firestore.
# - /register, /login, /logout: Placeholder endpoints for future custom auth flows.

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return the current authenticated user's token claims."""
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }


@router.post("/session")
async def sync_session(
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Sync the authenticated user's profile to Firestore.

    Called by the frontend after login to ensure the user document exists.
    Creates the user doc if it doesn't exist, or updates the last login time.
    """
    uid = user["uid"]
    user_ref = db.collection(User.COLLECTION).document(uid)
    user_doc = user_ref.get()

    now = datetime.utcnow()

    if user_doc.exists:
        user_ref.update({"updated_at": now})
    else:
        new_user = User(
            uid=uid,
            email=user.get("email", ""),
            full_name=user.get("name") or user.get("displayName"),
            created_at=now,
            updated_at=now,
        )
        user_ref.set(new_user.to_dict())

    return {"status": "ok", "uid": uid}


@router.post("/register")
async def register(db=Depends(get_db)):
    """Register a new user account.

    NOTE: User registration is handled by Firebase Auth on the frontend.
    This endpoint is a placeholder for any future custom registration logic.
    """
    raise HTTPException(
        status_code=501,
        detail="Registration is handled by Firebase Auth on the frontend.",
    )


@router.post("/login")
async def login(db=Depends(get_db)):
    """Authenticate user and return JWT token.

    NOTE: Login is handled by Firebase Auth on the frontend.
    Use POST /auth/session to sync after login.
    """
    raise HTTPException(
        status_code=501,
        detail="Login is handled by Firebase Auth on the frontend. Use POST /auth/session to sync.",
    )


@router.post("/logout")
async def logout():
    """Invalidate user session.

    NOTE: Logout is handled by Firebase Auth on the frontend.
    """
    return {"status": "ok", "message": "Session invalidated on client side."}
