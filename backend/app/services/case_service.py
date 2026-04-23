"""
Business Case Service

Business logic for creating, managing, and analyzing business cases.
"""


class CaseService:
    """Service for business case operations."""

    async def create_case(self, user_id: str, data: dict):
        """Create a new business investigation case."""
        # TODO: Create case, trigger initial location lookup
        pass

    async def get_case_with_details(self, case_id: str):
        """Get case with all related data (facts, tasks, recommendations)."""
        # TODO: Aggregate case data
        pass

    async def update_case(self, case_id: str, data: dict):
        """Update case metadata."""
        pass

    async def delete_case(self, case_id: str):
        """Delete case and cascade all related records."""
        pass
