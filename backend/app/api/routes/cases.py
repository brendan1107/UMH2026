"""
Business Cases Routes

CRUD operations for business investigation cases.
Each case represents a user's F&B business idea or existing business under review.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.post("/")
async def create_case(db: Session = Depends(get_db)):
    """Create a new business investigation case."""
    # TODO: Create case record, initialize session
    pass


@router.get("/")
async def list_cases(db: Session = Depends(get_db)):
    """List all business cases for the current user."""
    # TODO: Return user's cases
    pass


@router.get("/{case_id}")
async def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get detailed info for a specific business case."""
    # TODO: Return case details with facts, tasks, recommendation
    pass


@router.put("/{case_id}")
async def update_case(case_id: str, db: Session = Depends(get_db)):
    """Update business case details."""
    # TODO: Update case metadata
    pass


@router.delete("/{case_id}")
async def delete_case(case_id: str, db: Session = Depends(get_db)):
    """Delete a business case and all associated data."""
    # TODO: Cascade delete
    pass
