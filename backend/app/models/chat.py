"""
Chat Session & Message Models (Firestore Document Schemas)

Subcollections:
  business_cases/{case_id}/chat_sessions/{session_id}
  business_cases/{case_id}/chat_sessions/{session_id}/messages/{msg_id}
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# What is chat.py for?
# The chat.py file defines data models for representing chat sessions and messages in our application. The ChatSession model represents a conversation thread associated with a specific business case, while the ChatMessage model represents individual messages within a chat session. These models include fields for storing relevant information such as the role of the message sender (user, assistant, system), the content of the message, any structured output (e.g., extracted facts or tasks), and timestamps. By defining these models, we can easily serialize and deserialize chat data when storing it in Firestore and retrieving it for use in our application. This allows us to maintain a history of conversations between users and the AI assistant, which can be valuable for context management, analysis, and reporting.
@dataclass
class ChatSession:
    """Firestore document schema for chat_sessions subcollection."""
    id: str = ""
    case_id: str = ""
    summary: Optional[str] = None  # Summarized conversation for context management
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "ChatSession":
        return ChatSession(
            id=doc_id,
            case_id=data.get("case_id", ""),
            summary=data.get("summary"),
            created_at=data.get("created_at", datetime.utcnow()),
            updated_at=data.get("updated_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "chat_sessions"


@dataclass
class ChatMessage:
    """Firestore document schema for messages subcollection."""
    id: str = ""
    session_id: str = ""
    role: str = "user"  # user | assistant | system
    content: str = ""
    structured_output: Optional[str] = None  # JSON: extracted facts, tasks, etc.
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "structured_output": self.structured_output,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "ChatMessage":
        return ChatMessage(
            id=doc_id,
            session_id=data.get("session_id", ""),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            structured_output=data.get("structured_output"),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "messages"
