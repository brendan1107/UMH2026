"""
Authentication Routes

Handles user registration, login, token validation, and logout helpers.
"""

from fastapi import APIRouter, Depends, status

from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserLogin, UserRegister
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated Firebase user."""
    return {
        "data": {
            "uid": current_user["uid"],
            "authProvider": current_user.get("authProvider", "firebase"),
        }
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db=Depends(get_db)):
    """Register a new user account."""
    auth_service = AuthService(db_client=db)
    user = await auth_service.register_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return {
        "message": "User registered successfully",
        "user": user,
    }


@router.post("/login")
async def login(payload: UserLogin, db=Depends(get_db)):
    """Authenticate user and return a Firebase ID token."""
    auth_service = AuthService(db_client=db)
    return await auth_service.authenticate_user(
        email=payload.email,
        password=payload.password,
    )


@router.post("/logout")
async def logout():
    """Acknowledge client-side Firebase logout."""
    return {
        "message": "Logged out successfully",
    }
