"""
Task Service

Manages investigation task lifecycle and triggers re-analysis
when tasks are completed with new findings.
"""


class TaskService:
    """Service for investigation task operations."""

    async def get_tasks_for_case(self, case_id: str):
        """List all tasks for a business case."""
        pass

    async def complete_task(self, task_id: str, findings: str):
        """Mark task as completed and trigger AI re-analysis."""
        pass

    async def skip_task(self, task_id: str):
        """Mark task as skipped."""
        pass

    async def schedule_task(self, task_id: str, scheduled_date: str):
        """Mark task as scheduled (optionally with Calendar integration)."""
        pass
