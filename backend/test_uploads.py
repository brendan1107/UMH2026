import os
import tempfile
from pathlib import Path

import requests


BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")
CASE_ID = os.getenv("UPLOAD_TEST_CASE_ID")
AUTH_HEADER = {"Authorization": "Bearer dev-token"}


def _require_case_id() -> str:
    if not CASE_ID:
        raise SystemExit(
            "Set UPLOAD_TEST_CASE_ID to an existing case owned by dev-user-000. "
            "Run the backend with DEV_AUTH_BYPASS=true for this smoke test."
        )
    return CASE_ID


def test_upload_list_delete():
    case_id = _require_case_id()

    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "test_upload.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        with test_file.open("rb") as f:
            response = requests.post(
                f"{BASE_URL}/uploads/{case_id}/upload",
                files={"file": (test_file.name, f, "application/pdf")},
                headers=AUTH_HEADER,
                timeout=30,
            )

        print("Upload status:", response.status_code)
        print("Upload body:", response.text)
        response.raise_for_status()

        upload_data = response.json()
        upload_id = upload_data["id"]
        assert "storagePath" in upload_data
        assert upload_data["storageMode"] in {"firebase_storage", "metadata_only"}

        response = requests.get(
            f"{BASE_URL}/uploads/{case_id}",
            headers=AUTH_HEADER,
            timeout=30,
        )
        print("List status:", response.status_code)
        print("List body:", response.text)
        response.raise_for_status()
        assert any(item["id"] == upload_id for item in response.json())

        response = requests.delete(
            f"{BASE_URL}/uploads/{case_id}/{upload_id}",
            headers=AUTH_HEADER,
            timeout=30,
        )
        print("Delete status:", response.status_code)
        print("Delete body:", response.text)
        response.raise_for_status()

        sensitive_file = Path(tmp) / "firebase-service-account.json"
        sensitive_file.write_text("{}", encoding="utf-8")
        with sensitive_file.open("rb") as f:
            response = requests.post(
                f"{BASE_URL}/uploads/{case_id}/upload",
                files={"file": (sensitive_file.name, f, "application/json")},
                headers=AUTH_HEADER,
                timeout=30,
            )

        print("Sensitive file status:", response.status_code)
        print("Sensitive file body:", response.text)
        assert response.status_code == 400


if __name__ == "__main__":
    test_upload_list_delete()
