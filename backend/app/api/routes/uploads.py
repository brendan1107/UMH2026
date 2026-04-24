"""
Evidence Upload Routes

Handles file uploads (images, documents, photos) that users
submit as evidence for their business investigation.
Files are stored in Supabase Storage and processed by the AI.
"""
# This file defines the API endpoints for managing evidence uploads related to business
#  cases.
# The main functionalities include:
# - Uploading evidence files (e.g., photos, documents, menus) for a specific business
#  case. The upload process includes validating the file type and size, storing the file
#  in Supabase Storage, creating a record in the evidence_uploads table, processing the
#  file through the AI for summary and analysis, and triggering a re-analysis of the 
# business case based on the new evidence.
# - Listing all evidence uploads for a specific business case, allowing users to view
#  the metadata of their uploaded files.
# - Deleting an evidence upload, which involves removing the file from storage and
#  deleting the corresponding record from the database.
# The endpoints in this file will interact with the database to manage evidence upload
# records and with Supabase Storage to handle the actual file uploads. This allows users
#  to easily submit real-world evidence that the AI can analyze to provide more accurate
# recommendations for their F&B business cases.

# For example, when a user uploads a photo of a competitor's menu, the POST /api/cases/{case_id}/upload endpoint will be called to handle the file upload. The file will be validated and stored in Supabase Storage, and a new record will be created in the evidence_uploads table. The AI will then process the uploaded file to extract relevant information (e.g., menu items, prices) and update the business case analysis accordingly. Users can also view their uploaded evidence through the GET /api/cases/{case_id}/uploads endpoint and delete any unwanted uploads using the DELETE /api/uploads/{upload_id} endpoint. This functionality allows users to easily incorporate real-world evidence into their business investigations and see how it impacts the AI's recommendations.

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
