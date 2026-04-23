"""
Investigation Tasks Routes

Manages AI-generated field investigation tasks.
Tasks are created when the AI identifies missing evidence that
requires real-world validation (PRD Section 4.2: Human-in-the-Loop Field Tasks).

Task statuses: pending, scheduled, completed, skipped (SAD Section 11).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/{case_id}/tasks")
async def list_tasks(case_id: str, db: Session = Depends(get_db)):
    """List all investigation tasks for a business case."""
    # TODO: Return tasks with status
    pass


@router.put("/{task_id}")
async def update_task(task_id: str, db: Session = Depends(get_db)):
    """Update task status (e.g., mark as completed with findings)."""
    # TODO: Update status, store findings, trigger re-analysis if completed
    pass


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, db: Session = Depends(get_db)):
    """Mark a task as completed and submit findings for AI re-analysis."""
    # TODO: Store findings, trigger AI re-analysis (PRD Section 4.2: Re-analysis)
    pass


@router.post("/{task_id}/skip")
async def skip_task(task_id: str, db: Session = Depends(get_db)):
    """Skip a task (user chooses not to complete it)."""
    # TODO: Mark as skipped, note impact on recommendation confidence
    pass
