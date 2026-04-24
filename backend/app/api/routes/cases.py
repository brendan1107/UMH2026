"""
Business Cases Routes

CRUD operations for business investigation cases.
Each case represents a user's F&B business idea or existing business under review.
"""
# This file defines the API endpoints for managing business investigation cases.
# The main functionalities include:
# - Creating a new case when a user starts a new investigation.
# - Listing all cases associated with the current user.
# - Retrieving detailed information for a specific case, including facts, tasks, and AI recommendations.
# - Updating case metadata (e.g., name, description).
# - Deleting a case and all associated data when the user no longer needs it.
# Each endpoint interacts with the database to perform the necessary operations on the 
# case records. The endpoints are designed to be used by the frontend to allow users to
# manage their business cases effectively through the application's interface.

# For example, when a user creates a new case, the POST /api/cases/ endpoint will be
#  called to create a new case record in the database and initialize the investigation
#  session. When the user views their cases, the GET /api/cases/ endpoint will return a
#  list of their cases. When they click on a specific case, the GET /api/cases/{case_id}
#  endpoint will return detailed information about that case, including any facts that 
# have been added, tasks that have been created, and the current AI recommendation. 
# The PUT /api/cases/{case_id} endpoint allows users to update the case metadata, such
#  as changing the name or description of the case. Finally, if the user decides to 
# delete a case, the DELETE /api/cases/{case_id} endpoint will remove the case and all 
# associated data from the database.

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
