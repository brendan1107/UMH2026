"""
Evidence Upload Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/evidence_uploads/{upload_id}
Files are stored in Firebase Storage, metadata in Firestore.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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
