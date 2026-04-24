"""
Authentication Service

Handles user registration, login, password hashing, and JWT token management.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth
from jose import jwt

from app.config import settings
from app.db.database import db as default_db
from app.models.user import User

# What is auth_service.py for?
# The auth_service.py file defines a service class, AuthService, that contains the core logic for handling user authentication operations in our application. This includes functions for registering new users, authenticating existing users, hashing passwords securely, and generating JWT tokens for authenticated sessions. By centralizing this logic in a service class, we can keep our API route handlers clean and focused on handling HTTP requests and responses, while the AuthService takes care of the underlying authentication mechanics. This separation of concerns allows us to maintain a clear structure in our codebase and makes it easier to manage and update our authentication logic as needed.



class AuthService:
    """Service for authentication operations."""

    # Detail explanation of __init__  function:
    # The __init__ function of the AuthService class is a constructor 
    # that initializes the service with various dependencies and configuration
    # options.
    # 

    def __init__(
        self,
        db_client: Any | None = None,
        auth_provider: Any | None = None,
        identity_toolkit_api_key: str | None = None,
        http_client_factory: Any | None = None,
        jwt_secret_key: str | None = None,
        jwt_algorithm: str | None = None,
        access_token_expire_minutes: int | None = None,
    ):
        self.db = db_client if db_client is not None else default_db
        self.auth = auth_provider if auth_provider is not None else firebase_auth
        self.identity_toolkit_api_key = identity_toolkit_api_key
        self.http_client_factory = http_client_factory or httpx.AsyncClient
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    async def register_user(self, email: str, password: str, full_name: str = None):
        """Register a Firebase Auth user and create its Firestore profile."""
        email = self._normalize_email(email)
        full_name = self._normalize_full_name(full_name)
        self._validate_registration_input(email, password)
        self._require_firestore()

        try:
            firebase_user = self.auth.create_user(
                email=email,
                password=password,
                display_name=full_name,
            )
        except firebase_auth.EmailAlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Firebase Auth is unavailable: {exc}",
            )

        now = datetime.now(timezone.utc)
        user = User(
            uid=firebase_user.uid,
            email=firebase_user.email or email,
            full_name=full_name,
            created_at=now,
            updated_at=now,
        )

        try:
            self.db.collection(User.COLLECTION).document(user.uid).set(user.to_dict())
        except Exception:
            self._delete_firebase_user_safely(user.uid)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile",
            )

        return self._serialize_user(user)

    async def authenticate_user(self, email: str, password: str):
        """Validate credentials and return a Firebase ID token."""
        email = self._normalize_email(email)
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required",
            )

        api_key = self._get_identity_toolkit_api_key()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="FIREBASE_WEB_API_KEY is not configured",
            )

        url = (
            "https://identitytoolkit.googleapis.com/v1/"
            f"accounts:signInWithPassword?key={api_key}"
        )
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            async with self.http_client_factory(timeout=10.0) as client:
                response = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Firebase Auth request failed: {exc}",
            )

        if response.status_code != status.HTTP_200_OK:
            self._raise_firebase_login_error(response)

        data = response.json()
        access_token = data.get("idToken")
        uid = data.get("localId")
        if not access_token or not uid:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Firebase Auth returned an invalid login response",
            )

        self._ensure_user_profile(
            uid=uid,
            email=data.get("email") or email,
            full_name=data.get("displayName"),
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": data.get("refreshToken"),
            "expires_in": self._parse_expires_in(data.get("expiresIn")),
            "uid": uid,
            "email": data.get("email") or email,
        }


    async def create_access_token(self, user_id: str) -> str:
        """Generate a JWT access token."""
        user_id = (user_id or "").strip()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required",
            )

        secret_key = self._get_jwt_secret_key()
        if not secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT_SECRET_KEY is not configured",
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self._get_access_token_expire_minutes())
        payload = {
            "sub": user_id,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        return jwt.encode(
            payload,
            secret_key,
            algorithm=self._get_jwt_algorithm(),
        )

    def _require_firestore(self):
        if self.db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firestore is not configured",
            )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return (email or "").strip().lower()

    @staticmethod
    def _normalize_full_name(full_name: str | None) -> str | None:
        if full_name is None:
            return None
        return full_name.strip() or None

    @staticmethod
    def _validate_registration_input(email: str, password: str):
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required",
            )
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long",
            )

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": user.uid,
            "uid": user.uid,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def _delete_firebase_user_safely(self, uid: str):
        try:
            self.auth.delete_user(uid)
        except Exception:
            pass

    def _get_identity_toolkit_api_key(self) -> str:
        return (
            self.identity_toolkit_api_key
            or getattr(settings, "FIREBASE_WEB_API_KEY", "")
            or os.getenv("FIREBASE_WEB_API_KEY", "")
            or os.getenv("FIREBASE_API_KEY", "")
        )

    def _get_jwt_secret_key(self) -> str:
        return (
            self.jwt_secret_key
            or settings.JWT_SECRET_KEY
            or os.getenv("JWT_SECRET_KEY", "")
        )

    def _get_jwt_algorithm(self) -> str:
        return self.jwt_algorithm or settings.JWT_ALGORITHM or "HS256"

    def _get_access_token_expire_minutes(self) -> int:
        value = (
            self.access_token_expire_minutes
            if self.access_token_expire_minutes is not None
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            return 60
        return minutes if minutes > 0 else 60

    @staticmethod
    def _raise_firebase_login_error(response: httpx.Response):
        try:
            message = response.json().get("error", {}).get("message", "")
        except ValueError:
            message = ""

        if message in {
            "EMAIL_NOT_FOUND",
            "INVALID_PASSWORD",
            "INVALID_LOGIN_CREDENTIALS",
            "INVALID_EMAIL",
        }:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if message == "USER_DISABLED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        if message == "TOO_MANY_ATTEMPTS_TRY_LATER":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later",
            )
        if message == "OPERATION_NOT_ALLOWED":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email/password sign-in is disabled in Firebase",
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Firebase Auth rejected the login request",
        )

    def _ensure_user_profile(self, uid: str, email: str, full_name: str | None):
        if self.db is None:
            return

        doc_ref = self.db.collection(User.COLLECTION).document(uid)
        try:
            if doc_ref.get().exists:
                return

            now = datetime.now(timezone.utc)
            user = User(
                uid=uid,
                email=email,
                full_name=self._normalize_full_name(full_name),
                created_at=now,
                updated_at=now,
            )
            doc_ref.set(user.to_dict())
        except Exception:
            return

    @staticmethod
    def _parse_expires_in(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
