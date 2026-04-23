"""
Chat Session Routes

Handles the iterative AI conversation flow.
- Receives user messages
- Triggers AI orchestration (follow-up questions, analysis, task generation)
- Returns AI responses with structured data
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.post("/{case_id}/sessions")
async def create_session(case_id: str, db: Session = Depends(get_db)):
    """Start a new chat session for a business case."""
    # TODO: Create session, initialize AI context
    pass


@router.get("/{case_id}/sessions")
async def list_sessions(case_id: str, db: Session = Depends(get_db)):
    """List all chat sessions for a business case."""
    # TODO: Return sessions
    pass


@router.post("/{case_id}/sessions/{session_id}/messages")
async def send_message(case_id: str, session_id: str, db: Session = Depends(get_db)):
    """
    Send a user message and receive AI response.

    Flow (SAD Section 8 Sequence):
    1. Store user message
    2. Build AI context (facts, summary, external data)
    3. Call GLM for reasoning
    4. Parse structured output (questions, facts, tasks, recommendation)
    5. Store AI response and extracted data
    6. Return response to frontend
    """
    # TODO: Implement full AI orchestration pipeline
    pass


@router.get("/{case_id}/sessions/{session_id}/messages")
async def get_messages(case_id: str, session_id: str, db: Session = Depends(get_db)):
    """Retrieve message history for a session."""
    # TODO: Return paginated messages
    pass
