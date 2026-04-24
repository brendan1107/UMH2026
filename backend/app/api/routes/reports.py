"""
Report Routes

Handles business report generation and PDF export.
Reports are iteratively updated as the AI gathers more evidence.

Final verdict values: proceed, reconsider, do_not_open, improve, pivot, shut_down
(SAD Section 11).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/{case_id}/report")
async def get_report(case_id: str, db: Session = Depends(get_db)):
    """Get the current business report and recommendation for a case."""
    # TODO: Return latest recommendation with report content
    pass


@router.post("/{case_id}/report/generate")
async def generate_report(case_id: str, db: Session = Depends(get_db)):
    """Trigger a full report generation based on all available evidence."""
    # TODO: Compile all facts, tasks, uploads into a comprehensive report
    pass


@router.get("/{case_id}/report/pdf")
async def export_report_pdf(case_id: str, db: Session = Depends(get_db)):
    """Export the business report as a downloadable PDF."""
    # TODO: Generate PDF and return as streaming response
    pass
