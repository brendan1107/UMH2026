"""FastAPI dependencies shared by the backend routes."""

from fastapi import HTTPException, Request, status
from firebase_admin import auth as firebase_auth

from app.config import settings
from app.db.database import firebase_app


def _local_demo_user(request: Request) -> dict:
    uid = (
        request.headers.get("X-Demo-User-Id")
        or request.headers.get("X-User-Id")
        or "demo-user"
    )
    return {"uid": uid, "authProvider": "local-demo"}


async def get_current_user(request: Request) -> dict:
    """
    Validate Firebase Auth when configured.

    In development, missing Firebase auth falls back to a scoped demo user so the
    backend can run without Firebase credentials or frontend auth wiring.
    """
    auth_header = request.headers.get("Authorization")

    if firebase_app is None:
        return _local_demo_user(request)

    if not auth_header:
        if settings.DEBUG:
            return _local_demo_user(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        return firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
