"""
Report Service

Compiles business reports and handles PDF export.
"""


class ReportService:
    """Service for report generation and export."""

    async def get_latest_report(self, case_id: str):
        """Get the latest recommendation and report for a case."""
        pass

    async def generate_full_report(self, case_id: str):
        """Compile all evidence into a comprehensive business report."""
        pass

    async def export_pdf(self, case_id: str):
        """Generate and return a PDF version of the report."""
        pass
