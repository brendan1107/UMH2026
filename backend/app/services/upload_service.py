"""
Upload Service

Handles evidence file processing, storage, and AI analysis.
"""


class UploadService:
    """Service for evidence upload operations."""

    async def upload_file(self, case_id: str, file):
        """Upload file to Supabase Storage and create record."""
        pass

    async def process_evidence(self, upload_id: str):
        """Process uploaded evidence through AI for summarization."""
        pass

    async def get_uploads_for_case(self, case_id: str):
        """List all uploads for a case."""
        pass

    async def delete_upload(self, upload_id: str):
        """Delete from storage and database."""
        pass
