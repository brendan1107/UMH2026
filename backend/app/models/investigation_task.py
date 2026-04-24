"""
Investigation Task Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/recommendations/{rec_id}/tasks/{task_id}
Task statuses: pending, scheduled, completed, skipped.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# What is investigation_task.py for?
# The investigation_task.py file defines a data model for representing investigation tasks that are generated as part of the recommendations for a business case. This model, InvestigationTask, includes fields for storing relevant information about a task, such as its title, description, location, priority, status, findings, associated calendar event ID (if scheduled), due date, and timestamps. By defining this model, we can easily serialize and deserialize investigation task data when storing it in Firestore and retrieving it for use in our application. This allows us to manage the lifecycle of investigation tasks effectively, track their progress, and integrate with calendar scheduling features to help users stay organized as they work through their F&B business cases. The tasks are stored in a subcollection under each recommendation, which in turn is under each business case, reflecting the hierarchical relationship between these entities in our Firestore database.
@dataclass
class InvestigationTask:
    """Firestore document schema for investigation tasks subcollection."""
    id: str = ""
    recommendation_id: str = ""
    title: str = ""
    description: Optional[str] = None
    location: Optional[str] = None
    priority: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, scheduled, completed, skipped
    findings: Optional[str] = None
    calendar_event_id: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "priority": self.priority,
            "status": self.status,
            "findings": self.findings,
            "calendar_event_id": self.calendar_event_id,
            "due_date": self.due_date,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "InvestigationTask":
        return InvestigationTask(
            id=doc_id,
            recommendation_id=data.get("recommendation_id", ""),
            title=data.get("title", ""),
            description=data.get("description"),
            location=data.get("location"),
            priority=data.get("priority", "medium"),
            status=data.get("status", "pending"),
            findings=data.get("findings"),
            calendar_event_id=data.get("calendar_event_id"),
            due_date=data.get("due_date"),
            completed_at=data.get("completed_at"),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "tasks"
