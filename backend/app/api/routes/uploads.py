"""
Evidence Upload Routes

Handles file uploads (images, documents, photos) that users
submit as evidence for their business investigation.
Files are stored in Supabase Storage and processed by the AI.
"""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.post("/{case_id}/upload")
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload evidence file (photo, document, menu, etc.).

    Flow:
    1. Validate file type and size
    2. Upload to Supabase Storage
    3. Create evidence_uploads record
    4. Process through AI for summary/analysis
    5. Trigger re-analysis of business case
    """
    # TODO: Implement upload pipeline
    pass


@router.get("/{case_id}/uploads")
async def list_uploads(case_id: str, db: Session = Depends(get_db)):
    """List all evidence uploads for a business case."""
    # TODO: Return upload metadata
    pass


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str, db: Session = Depends(get_db)):
    """Delete an evidence upload."""
    # TODO: Remove from storage and database
    pass
