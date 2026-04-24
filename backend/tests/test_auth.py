"""Tests for authentication behavior."""

import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from app.api.routes import auth as auth_routes
from app.services.auth_service import AuthService


class FakeDocument:
    def __init__(self):
        self.data = None

    def set(self, data):
        self.data = data

    def get(self):
        return SimpleNamespace(exists=self.data is not None)


class FakeCollection:
    def __init__(self):
        self.documents = {}

    def document(self, document_id):
        self.documents.setdefault(document_id, FakeDocument())
        return self.documents[document_id]


class FakeFirestore:
    def __init__(self):
        self.collections = {}

    def collection(self, collection_name):
        self.collections.setdefault(collection_name, FakeCollection())
        return self.collections[collection_name]


class FakeFirebaseAuth:
    def __init__(self):
        self.created_user = None
        self.deleted_uid = None

    def create_user(self, **kwargs):
        self.created_user = kwargs
        return SimpleNamespace(uid="user-123", email=kwargs["email"])

    def delete_user(self, uid):
        self.deleted_uid = uid


class FakeAuthService:
    instances = []

    def __init__(self, db_client=None):
        self.db_client = db_client
        self.register_call = None
        self.login_call = None
        self.__class__.instances.append(self)

    async def register_user(self, email: str, password: str, full_name: str = None):
        self.register_call = {
            "email": email,
            "password": password,
            "full_name": full_name,
        }
        return {
            "id": "user-123",
            "uid": "user-123",
            "email": email,
            "full_name": full_name,
        }

    async def authenticate_user(self, email: str, password: str):
        self.login_call = {
            "email": email,
            "password": password,
        }
        return {
            "access_token": "id-token",
            "token_type": "bearer",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
            "uid": "user-123",
            "email": email,
        }


def build_auth_test_client(monkeypatch, db):
    FakeAuthService.instances = []
    monkeypatch.setattr(auth_routes, "AuthService", FakeAuthService)

    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/auth")
    app.dependency_overrides[auth_routes.get_db] = lambda: db
    return TestClient(app)


@pytest.mark.asyncio
async def test_register_user_creates_auth_user_and_firestore_profile():
    """Test user registration."""
    db = FakeFirestore()
    auth_provider = FakeFirebaseAuth()
    service = AuthService(db_client=db, auth_provider=auth_provider)

    result = await service.register_user(
        email=" Test@Example.COM ",
        password="secret1",
        full_name=" Test User ",
    )

    assert auth_provider.created_user == {
        "email": "test@example.com",
        "password": "secret1",
        "display_name": "Test User",
    }
    assert result["id"] == "user-123"
    assert result["email"] == "test@example.com"
    assert result["full_name"] == "Test User"

    stored_user = db.collection("users").document("user-123").data
    assert stored_user["uid"] == "user-123"
    assert stored_user["email"] == "test@example.com"
    assert stored_user["full_name"] == "Test User"


def test_register_endpoint_calls_auth_service(monkeypatch):
    db = FakeFirestore()
    client = build_auth_test_client(monkeypatch, db)

    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "secret1",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "message": "User registered successfully",
        "user": {
            "id": "user-123",
            "uid": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
        },
    }
    assert FakeAuthService.instances[0].db_client is db
    assert FakeAuthService.instances[0].register_call == {
        "email": "test@example.com",
        "password": "secret1",
        "full_name": "Test User",
    }


def test_login_endpoint_calls_auth_service(monkeypatch):
    db = FakeFirestore()
    client = build_auth_test_client(monkeypatch, db)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "secret1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "id-token",
        "token_type": "bearer",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "uid": "user-123",
        "email": "test@example.com",
    }
    assert FakeAuthService.instances[0].db_client is db
    assert FakeAuthService.instances[0].login_call == {
        "email": "test@example.com",
        "password": "secret1",
    }


def test_logout_endpoint_returns_success_message():
    app = FastAPI()
    app.include_router(auth_routes.router, prefix="/api/auth")
    client = TestClient(app)

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}


@pytest.mark.asyncio
async def test_create_access_token_returns_signed_jwt():
    service = AuthService(
        jwt_secret_key="test-secret",
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
    )

    token = await service.create_access_token(" user-123 ")
    payload = jwt.decode(token, "test-secret", algorithms=["HS256"])

    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["exp"] - payload["iat"] == 15 * 60


@pytest.mark.asyncio
async def test_authenticate_user_returns_firebase_token_and_backfills_profile():
    """Test user login."""
    async def firebase_handler(request):
        assert "accounts:signInWithPassword?key=test-api-key" in str(request.url)
        assert json.loads(request.content) == {
            "email": "test@example.com",
            "password": "secret1",
            "returnSecureToken": True,
        }
        return httpx.Response(
            200,
            json={
                "idToken": "id-token",
                "refreshToken": "refresh-token",
                "expiresIn": "3600",
                "localId": "user-123",
                "email": "test@example.com",
                "displayName": "Test User",
            },
        )

    db = FakeFirestore()
    transport = httpx.MockTransport(firebase_handler)
    service = AuthService(
        db_client=db,
        identity_toolkit_api_key="test-api-key",
        http_client_factory=lambda **kwargs: httpx.AsyncClient(
            transport=transport,
            **kwargs,
        ),
    )

    result = await service.authenticate_user(
        email=" Test@Example.COM ",
        password="secret1",
    )

    assert result == {
        "access_token": "id-token",
        "token_type": "bearer",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "uid": "user-123",
        "email": "test@example.com",
    }

    stored_user = db.collection("users").document("user-123").data
    assert stored_user["uid"] == "user-123"
    assert stored_user["email"] == "test@example.com"
    assert stored_user["full_name"] == "Test User"
