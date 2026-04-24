"""
Evidence Upload Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/evidence_uploads/{upload_id}
Files are stored in Firebase Storage, metadata in Firestore.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# What is evidence_upload.py for?
# The evidence_upload.py file defines a data model for representing evidence files that users upload in relation to their business cases. This model, EvidenceUpload, includes fields for storing metadata about the uploaded file, such as its name, type, size, storage path in Firebase Storage, download URL, and any AI-generated summary or analysis results. By defining this model, we can easily serialize and deserialize evidence upload data when storing it in Firestore and retrieving it for use in our application. This allows us to manage user-uploaded files effectively, link them to the relevant business cases, and provide insights based on the content of the files through AI analysis. The actual file data is stored in Firebase Storage, while the metadata and analysis results are stored in Firestore for easy querying and association with business cases.

@dataclass
class EvidenceUpload:
    """Firestore document schema for evidence_uploads subcollection."""
    id: str = ""
    case_id: str = ""
    file_name: str = ""
    file_type: Optional[str] = None  # image/jpeg, application/pdf, etc.
    file_size: Optional[int] = None
    storage_path: Optional[str] = None  # Firebase Storage path
    download_url: Optional[str] = None  # Public download URL
    ai_summary: Optional[str] = None
    analysis_status: str = "pending"  # pending, processed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "storage_path": self.storage_path,
            "download_url": self.download_url,
            "ai_summary": self.ai_summary,
            "analysis_status": self.analysis_status,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "EvidenceUpload":
        return EvidenceUpload(
            id=doc_id,
            case_id=data.get("case_id", ""),
            file_name=data.get("file_name", ""),
            file_type=data.get("file_type"),
            file_size=data.get("file_size"),
            storage_path=data.get("storage_path"),
            download_url=data.get("download_url"),
            ai_summary=data.get("ai_summary"),
            analysis_status=data.get("analysis_status", "pending"),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "evidence_uploads"
