"""Tests for report service behavior."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.routes import reports as report_routes
from app.services.report_service import ReportService


class FakeSnapshot:
    def __init__(self, document_id: str, data: dict | None):
        self.id = document_id
        self.exists = data is not None
        self._data = data or {}

    def to_dict(self):
        return self._data


class FakeDocument:
    def __init__(self, document_id: str):
        self.id = document_id
        self.data = None
        self.collections = {}

    def set(self, data):
        self.data = data

    def update(self, data):
        if self.data is None:
            self.data = {}
        self.data.update(data)

    def get(self):
        return FakeSnapshot(self.id, self.data)

    def to_dict(self):
        return self.data or {}

    def collection(self, collection_name):
        self.collections.setdefault(collection_name, FakeCollection(collection_name))
        return self.collections[collection_name]


class FakeQuery:
    def __init__(self, documents):
        self.documents = documents
        self.filters = []
        self.order_field = None
        self.descending = False
        self.limit_count = None

    def where(self, field, operator, value):
        self.filters.append((field, operator, value))
        return self

    def order_by(self, field, direction=None):
        self.order_field = field
        self.descending = str(direction).upper().endswith("DESCENDING")
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def stream(self):
        snapshots = [
            FakeSnapshot(document.id, document.data)
            for document in self.documents.values()
            if document.data is not None
        ]
        for field, operator, value in self.filters:
            if operator == "==":
                snapshots = [
                    snapshot
                    for snapshot in snapshots
                    if snapshot.to_dict().get(field) == value
                ]
        if self.order_field:
            snapshots.sort(
                key=lambda snapshot: snapshot.to_dict().get(self.order_field),
                reverse=self.descending,
            )
        if self.limit_count is not None:
            snapshots = snapshots[: self.limit_count]
        return iter(snapshots)


class FakeCollection(FakeQuery):
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.documents = {}
        self.auto_id_counter = 0
        super().__init__(self.documents)

    def document(self, document_id: str | None = None):
        if document_id is None:
            self.auto_id_counter += 1
            document_id = f"{self.collection_name}-{self.auto_id_counter}"
        self.documents.setdefault(document_id, FakeDocument(document_id))
        return self.documents[document_id]


class FakeFirestore:
    def __init__(self):
        self.collections = {}

    def collection(self, collection_name):
        self.collections.setdefault(collection_name, FakeCollection(collection_name))
        return self.collections[collection_name]


class FakeStorageClient:
    def __init__(self):
        self.uploads = []

    async def upload_file(
        self,
        destination_path: str,
        file_data: bytes,
        content_type: str | None = None,
    ):
        self.uploads.append(
            {
                "destination_path": destination_path,
                "file_data": file_data,
                "content_type": content_type,
            }
        )
        return f"https://storage.example/{destination_path}"


class FakeReportService:
    instances = []

    def __init__(self, db_client=None):
        self.db_client = db_client
        self.calls = []
        self.__class__.instances.append(self)

    async def get_latest_report(self, case_id: str):
        self.calls.append(("get_latest_report", case_id))
        return {
            "case_id": case_id,
            "recommendation": {"id": "rec-1", "summary": "Latest summary"},
            "report": "Latest report",
            "export": None,
        }

    async def generate_full_report(self, case_id: str):
        self.calls.append(("generate_full_report", case_id))
        return {
            "case_id": case_id,
            "recommendation": {"id": "rec-2", "summary": "Generated summary"},
            "report": "Generated report",
            "context": {"facts": []},
        }

    async def export_pdf(self, case_id: str):
        self.calls.append(("export_pdf", case_id))
        return {
            "case_id": case_id,
            "file_name": "fb-genie-report-case-123.pdf",
            "content_type": "application/pdf",
            "pdf_bytes": b"%PDF-1.4\nfake pdf",
            "export": {"id": "export-1"},
        }


def build_report_test_client(monkeypatch, db):
    FakeReportService.instances = []
    monkeypatch.setattr(report_routes, "ReportService", FakeReportService)

    app = FastAPI()
    app.include_router(report_routes.router, prefix="/api/reports")
    app.dependency_overrides[report_routes.get_db] = lambda: db
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_latest_report_returns_latest_recommendation_and_export():
    db = FakeFirestore()
    case_ref = db.collection("business_cases").document("case-123")
    case_ref.set({"title": "Cafe launch"})

    old_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_date = datetime(2026, 1, 2, tzinfo=timezone.utc)
    case_ref.collection("recommendations").document("rec-old").set(
        {
            "case_id": "case-123",
            "summary": "Old summary",
            "full_report": "Old report",
            "created_at": old_date,
            "version": 1,
        }
    )
    case_ref.collection("recommendations").document("rec-new").set(
        {
            "case_id": "case-123",
            "verdict": "proceed",
            "confidence_score": 82,
            "summary": "Latest summary",
            "strengths": ["Good lunch demand"],
            "weaknesses": ["High rent"],
            "action_items": ["Validate supplier costs"],
            "full_report": "Latest full report",
            "is_provisional": False,
            "version": 2,
            "created_at": new_date,
        }
    )
    db.collection("report_exports").document("export-old").set(
        {
            "case_id": "case-123",
            "file_name": "old.pdf",
            "created_at": old_date,
        }
    )
    db.collection("report_exports").document("export-new").set(
        {
            "case_id": "case-123",
            "file_name": "latest.pdf",
            "download_url": "https://example.com/latest.pdf",
            "format": "pdf",
            "created_at": new_date,
        }
    )

    result = await ReportService(db_client=db).get_latest_report(" case-123 ")

    assert result["case_id"] == "case-123"
    assert result["report"] == "Latest full report"
    assert result["recommendation"]["id"] == "rec-new"
    assert result["recommendation"]["summary"] == "Latest summary"
    assert result["recommendation"]["version"] == 2
    assert result["export"]["id"] == "export-new"
    assert result["export"]["file_name"] == "latest.pdf"


@pytest.mark.asyncio
async def test_get_latest_report_raises_404_when_no_recommendation_exists():
    db = FakeFirestore()
    db.collection("business_cases").document("case-123").set({"title": "Cafe launch"})

    with pytest.raises(HTTPException) as exc_info:
        await ReportService(db_client=db).get_latest_report("case-123")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_generate_full_report_compiles_evidence_and_saves_recommendation():
    db = FakeFirestore()
    case_ref = db.collection("business_cases").document("case-123")
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    case_ref.set(
        {
            "user_id": "user-123",
            "title": "SS15 cafe launch",
            "description": "Small cafe near offices",
            "mode": "pre_launch",
            "business_type": "cafe",
            "target_location": "SS15",
            "status": "active",
            "created_at": created_at,
            "updated_at": created_at,
        }
    )
    case_ref.collection("extracted_facts").document("fact-1").set(
        {
            "case_id": "case-123",
            "category": "location",
            "key": "target_area",
            "value": "SS15",
            "confidence": "user_provided",
            "source": "user_input",
            "created_at": created_at,
        }
    )
    case_ref.collection("evidence_uploads").document("upload-1").set(
        {
            "case_id": "case-123",
            "file_name": "menu-prices.pdf",
            "file_type": "application/pdf",
            "ai_summary": "Competitor prices are RM12-RM18.",
            "analysis_status": "processed",
            "created_at": created_at,
        }
    )
    case_ref.collection("place_results").document("place-1").set(
        {
            "case_id": "case-123",
            "name": "Nearby Cafe",
            "address": "SS15 Subang Jaya",
            "rating": 4.2,
            "created_at": created_at,
        }
    )
    rec_ref = case_ref.collection("recommendations").document("rec-1")
    rec_ref.set(
        {
            "case_id": "case-123",
            "verdict": "reconsider",
            "confidence_score": 55,
            "summary": "Need more evidence before launch.",
            "strengths": ["Visible office crowd"],
            "weaknesses": ["Rent unknown"],
            "action_items": ["Confirm monthly rent"],
            "is_provisional": True,
            "version": 1,
            "created_at": created_at,
        }
    )
    rec_ref.collection("tasks").document("task-1").set(
        {
            "recommendation_id": "rec-1",
            "title": "Count lunch traffic",
            "description": "Count pedestrians at lunch.",
            "priority": "high",
            "status": "pending",
            "created_at": created_at,
        }
    )

    result = await ReportService(db_client=db).generate_full_report(" case-123 ")

    assert result["case_id"] == "case-123"
    assert result["recommendation"]["version"] == 2
    assert result["recommendation"]["verdict"] == "reconsider"
    assert result["recommendation"]["confidence_score"] == 55
    assert result["recommendation"]["strengths"] == ["Visible office crowd"]
    assert result["recommendation"]["weaknesses"] == ["Rent unknown"]
    assert result["recommendation"]["action_items"] == ["Confirm monthly rent"]
    assert "SS15 cafe launch" in result["report"]
    assert "target_area = SS15" in result["report"]
    assert "menu-prices.pdf" in result["report"]
    assert "Nearby Cafe" in result["report"]
    assert "Count lunch traffic" in result["report"]
    assert result["context"]["facts"][0]["key"] == "target_area"

    new_recommendation = case_ref.collection("recommendations").document(
        "recommendations-1"
    )
    assert new_recommendation.data["full_report"] == result["report"]
    assert new_recommendation.data["version"] == 2
    assert case_ref.data["status"] == "report_generated"


@pytest.mark.asyncio
async def test_export_pdf_renders_uploads_and_saves_export_metadata():
    db = FakeFirestore()
    storage = FakeStorageClient()
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    case_ref = db.collection("business_cases").document("case-123")
    case_ref.set(
        {
            "title": "Cafe launch",
            "business_type": "cafe",
            "status": "active",
            "created_at": created_at,
            "updated_at": created_at,
        }
    )
    case_ref.collection("recommendations").document("rec-1").set(
        {
            "case_id": "case-123",
            "verdict": "proceed",
            "confidence_score": 90,
            "summary": "Strong launch indicators.",
            "full_report": "# Cafe launch\n\n## Recommendation\n- Proceed with launch",
            "is_provisional": False,
            "version": 1,
            "created_at": created_at,
        }
    )

    result = await ReportService(
        db_client=db,
        storage_client=storage,
    ).export_pdf(" case-123 ")

    assert result["case_id"] == "case-123"
    assert result["content_type"] == "application/pdf"
    assert result["file_name"].startswith("fb-genie-report-case-123-")
    assert result["file_name"].endswith(".pdf")
    assert result["pdf_bytes"].startswith(b"%PDF")
    assert result["export"]["id"] == "report_exports-1"
    assert result["export"]["case_id"] == "case-123"
    assert result["export"]["file_name"] == result["file_name"]
    assert result["export"]["format"] == "pdf"
    assert result["export"]["file_size"] == len(result["pdf_bytes"])
    assert result["export"]["download_url"].startswith("https://storage.example/")
    assert result["export"]["storage_path"] == storage.uploads[0]["destination_path"]

    assert len(storage.uploads) == 1
    assert storage.uploads[0]["content_type"] == "application/pdf"
    assert storage.uploads[0]["file_data"] == result["pdf_bytes"]

    saved_export = db.collection("report_exports").document("report_exports-1")
    assert saved_export.data["download_url"] == result["export"]["download_url"]
    assert saved_export.data["file_size"] == len(result["pdf_bytes"])


def test_get_report_endpoint_calls_report_service(monkeypatch):
    db = FakeFirestore()
    client = build_report_test_client(monkeypatch, db)

    response = client.get("/api/reports/case-123/report")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "case-123",
        "recommendation": {"id": "rec-1", "summary": "Latest summary"},
        "report": "Latest report",
        "export": None,
    }
    assert FakeReportService.instances[0].db_client is db
    assert FakeReportService.instances[0].calls == [
        ("get_latest_report", "case-123")
    ]


def test_generate_report_endpoint_calls_report_service(monkeypatch):
    db = FakeFirestore()
    client = build_report_test_client(monkeypatch, db)

    response = client.post("/api/reports/case-123/report/generate")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "case-123",
        "recommendation": {"id": "rec-2", "summary": "Generated summary"},
        "report": "Generated report",
        "context": {"facts": []},
    }
    assert FakeReportService.instances[0].db_client is db
    assert FakeReportService.instances[0].calls == [
        ("generate_full_report", "case-123")
    ]


def test_export_report_pdf_endpoint_streams_pdf(monkeypatch):
    db = FakeFirestore()
    client = build_report_test_client(monkeypatch, db)

    response = client.get("/api/reports/case-123/report/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="fb-genie-report-case-123.pdf"'
    )
    assert response.headers["content-length"] == str(len(b"%PDF-1.4\nfake pdf"))
    assert response.headers["x-report-export-id"] == "export-1"
    assert response.content == b"%PDF-1.4\nfake pdf"
    assert FakeReportService.instances[0].db_client is db
    assert FakeReportService.instances[0].calls == [("export_pdf", "case-123")]
