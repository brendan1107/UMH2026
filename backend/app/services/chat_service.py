"""
Chat Service

Orchestrates the message flow between user, AI, and external services.
This is the main entry point for the iterative investigation workflow.
"""


class ChatService:
    """Service for chat session and message operations."""

    async def create_session(self, case_id: str):
        """Initialize a new chat session for a case."""
        pass

    async def process_message(self, case_id: str, session_id: str, content: str):
        """
        Process a user message through the full AI pipeline.

        Steps:
        1. Store user message
        2. Load context (facts, summary, place data, uploads)
        3. Call AI orchestrator
        4. Parse and store structured outputs
        5. Update recommendation if applicable
        6. Return AI response
        """
        pass

    async def get_session_history(self, session_id: str):
        """Retrieve message history with pagination."""
        pass
