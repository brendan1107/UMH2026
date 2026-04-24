"""
Report Export Model (Firestore Document Schema)

Collection: report_exports/{export_id}
PDF files stored in Firebase Storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ReportExport:
    """Firestore document schema for report exports."""
    id: str = ""
    case_id: str = ""
    file_name: str = ""
    storage_path: Optional[str] = None  # Firebase Storage path
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    format: str = "pdf"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "file_name": self.file_name,
            "storage_path": self.storage_path,
            "download_url": self.download_url,
            "file_size": self.file_size,
            "format": self.format,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "ReportExport":
        return ReportExport(
            id=doc_id,
            case_id=data.get("case_id", ""),
            file_name=data.get("file_name", ""),
            storage_path=data.get("storage_path"),
            download_url=data.get("download_url"),
            file_size=data.get("file_size"),
            format=data.get("format", "pdf"),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    COLLECTION = "report_exports"
