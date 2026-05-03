"""Shared test fixtures for the F&B Genie backend test suite.

The in-memory Firestore mock replaces the real Firestore client so tests
run offline with no Firebase credentials required.
"""

import os
from uuid import uuid4

# Must be set before any app module is imported
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.dependencies import get_current_user
from app.db.session import get_db


# ── In-memory Firestore mock ─────────────────────────────────────────────────


class MockDocSnapshot:
    """Simulates a Firestore DocumentSnapshot."""

    def __init__(self, doc_id: str, data, collection_path: str, store: dict):
        self.id = doc_id
        self._data = data
        self._collection_path = collection_path
        self._store = store

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict:
        return dict(self._data) if self._data else {}

    @property
    def reference(self) -> "MockDocRef":
        return MockDocRef(self._store, self._collection_path, self.id)


class MockDocRef:
    """Simulates a Firestore DocumentReference."""

    def __init__(self, store: dict, collection_path: str, doc_id=None):
        self._store = store
        self._collection_path = collection_path
        self._id = doc_id if doc_id is not None else uuid4().hex

    @property
    def id(self) -> str:
        return self._id

    def get(self) -> MockDocSnapshot:
        data = self._store.get((self._collection_path, self._id))
        return MockDocSnapshot(self._id, data, self._collection_path, self._store)

    def set(self, data: dict) -> None:
        self._store[(self._collection_path, self._id)] = dict(data)

    def update(self, data: dict) -> None:
        existing = dict(self._store.get((self._collection_path, self._id)) or {})
        existing.update(data)
        self._store[(self._collection_path, self._id)] = existing

    def delete(self) -> None:
        self._store.pop((self._collection_path, self._id), None)

    def collection(self, subcollection: str) -> "MockCollectionRef":
        path = f"{self._collection_path}/{self._id}/{subcollection}"
        return MockCollectionRef(self._store, path)


class MockQuery:
    """Simulates a Firestore Query (supports where / order_by / limit / stream)."""

    def __init__(self, store, collection_path, filters=None,
                 order_field=None, order_dir=None, limit_n=None):
        self._store = store
        self._collection_path = collection_path
        self._filters = filters or []
        self._order_field = order_field
        self._order_dir = order_dir
        self._limit_n = limit_n

    def where(self, field, op: str, value=None) -> "MockQuery":
        return MockQuery(
            self._store, self._collection_path,
            self._filters + [(field, op, value)],
            self._order_field, self._order_dir, self._limit_n,
        )

    def order_by(self, field, direction=None) -> "MockQuery":
        return MockQuery(
            self._store, self._collection_path,
            self._filters, field, direction, self._limit_n,
        )

    def limit(self, n: int) -> "MockQuery":
        return MockQuery(
            self._store, self._collection_path,
            self._filters, self._order_field, self._order_dir, n,
        )

    def stream(self):
        results = []
        for (cpath, doc_id), data in self._store.items():
            if cpath != self._collection_path:
                continue
            match = True
            for field, op, value in self._filters:
                # firestore.FieldPath.document_id() arrives as a non-str object
                if not isinstance(field, str):
                    if op == "==" and doc_id != value:
                        match = False
                elif op == "==" and data.get(field) != value:
                    match = False
                if not match:
                    break
            if match:
                results.append(
                    MockDocSnapshot(doc_id, data, cpath, self._store)
                )
        if self._limit_n is not None:
            results = results[: self._limit_n]
        return iter(results)


class MockCollectionRef:
    """Simulates a Firestore CollectionReference."""

    def __init__(self, store: dict, collection_path: str):
        self._store = store
        self._collection_path = collection_path

    def document(self, doc_id=None) -> MockDocRef:
        return MockDocRef(self._store, self._collection_path, doc_id)

    def where(self, field, op: str, value=None) -> MockQuery:
        return MockQuery(self._store, self._collection_path, [(field, op, value)])

    def order_by(self, field, direction=None) -> MockQuery:
        return MockQuery(self._store, self._collection_path, [], field, direction)

    def stream(self):
        return MockQuery(self._store, self._collection_path).stream()

    def add(self, data: dict):
        doc_ref = self.document()
        doc_ref.set(data)
        return (None, doc_ref)


class MockCollectionGroupRef:
    """Simulates a Firestore collectionGroup() query across all subcollections."""

    def __init__(self, store: dict, subcollection_name: str, filters=None):
        self._store = store
        self._subcollection_name = subcollection_name
        self._filters = filters or []

    def where(self, field, op: str, value=None) -> "MockCollectionGroupRef":
        return MockCollectionGroupRef(
            self._store, self._subcollection_name,
            self._filters + [(field, op, value)],
        )

    def stream(self):
        results = []
        for (cpath, doc_id), data in self._store.items():
            parts = cpath.split("/")
            if not parts or parts[-1] != self._subcollection_name:
                continue
            match = True
            for field, op, value in self._filters:
                if not isinstance(field, str):
                    if op == "==" and doc_id != value:
                        match = False
                elif op == "==" and data.get(field) != value:
                    match = False
                if not match:
                    break
            if match:
                results.append(
                    MockDocSnapshot(doc_id, data, cpath, self._store)
                )
        return iter(results)


class InMemoryFirestore:
    """Lightweight in-memory Firestore client for unit testing."""

    def __init__(self):
        self._store: dict = {}

    def collection(self, name: str) -> MockCollectionRef:
        return MockCollectionRef(self._store, name)

    def collection_group(self, name: str) -> MockCollectionGroupRef:
        return MockCollectionGroupRef(self._store, name)

    def reset(self) -> None:
        self._store.clear()


# ── Test constants ───────────────────────────────────────────────────────────

DEV_USER = {"uid": "dev-user-001", "email": "dev@test.com"}


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_db():
    """Fresh in-memory Firestore instance per test."""
    return InMemoryFirestore()


@pytest.fixture()
def client(mock_db):
    """TestClient with both Firestore and auth dependencies overridden."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: DEV_USER
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client_no_auth(mock_db):
    """TestClient where only Firestore is overridden; real auth logic applies."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def case_id(client):
    """Pre-create a business case and return its Firestore ID."""
    resp = client.post("/api/cases/", json={
        "title": "Test Cafe",
        "description": "A test cafe case",
        "stage": "new",
        "business_type": "cafe",
        "target_location": "Kuala Lumpur",
    })
    assert resp.status_code == 200
    return resp.json()["id"]
