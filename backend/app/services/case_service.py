"""
Business Case Service

Business logic for creating, managing, and analyzing business cases.
"""

# What is case_service.py for?
# The case_service.py file defines a service class, CaseService, that contains the core business logic for handling operations related to business cases in our application. This includes functions for creating new business cases, retrieving case details along with all related data (such as facts, tasks, and recommendations), updating case metadata, and deleting cases along with their associated records. By centralizing this logic in a service class, we can keep our API route handlers clean and focused on handling HTTP requests and responses, while the CaseService takes care of the underlying mechanics of managing business cases. This separation of concerns allows us to maintain a clear structure in our codebase and makes it easier to manage and update our business case logic as needed.


from datetime import datetime
from google.cloud import firestore

class CaseService:
    """Service for business case operations."""

    async def create_case(self, user_id: str, data: dict):
        """Create a new business investigation case."""
        # TODO: Create case, trigger initial location lookup
        pass

    async def get_case_with_details(self, db: firestore.Client, case_id: str):
        """Get case with all related data (facts, tasks, recommendations)."""
        case_ref = db.collection("business_cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return None
        
        data = case_doc.to_dict()
        data["id"] = case_id

        # 1. Get latest location analysis
        place_results = case_ref.collection("place_results").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).get()
        data["latest_location_analysis"] = place_results[0].to_dict() if place_results else None

        # 2. Get all tasks
        tasks = case_ref.collection("tasks").order_by("created_at").get()
        data["tasks"] = [t.to_dict() for t in tasks]

        # 3. Get all case inputs
        inputs = case_ref.collection("case_inputs").order_by("updated_at", direction=firestore.Query.DESCENDING).get()
        data["case_inputs"] = [i.to_dict() for i in inputs]

        # 4. Get recent messages
        session_ref = case_ref.collection("chat_sessions").document("default_session")
        messages = session_ref.collection("messages").order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).get()
        data["recent_messages"] = [m.to_dict() for m in reversed(messages)]

        return data

    async def get_case_ai_context(self, db: firestore.Client, case_id: str):
        """Aggregate all data needed for AI context building."""
        case_ref = db.collection("business_cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return None
        
        case_data = case_doc.to_dict()
        
        # 1. Get latest location analysis results
        latest_analysis = None
        if case_data.get("latest_location_analysis_id"):
            analysis_doc = case_ref.collection("place_results").document(case_data["latest_location_analysis_id"]).get()
            if analysis_doc.exists:
                latest_analysis = analysis_doc.to_dict()

        # 2. Get all tasks and their responses
        tasks_docs = case_ref.collection("tasks").order_by("created_at").get()
        tasks = []
        for t in tasks_docs:
            t_data = t.to_dict()
            tasks.append({
                "id": t.id,
                "title": t_data.get("title"),
                "status": t_data.get("status"),
                "submitted_value": t_data.get("submitted_value"),
                "type": t_data.get("type"),
                "description": t_data.get("description")
            })

        # 3. Get all case inputs
        inputs_docs = case_ref.collection("case_inputs").get()
        case_inputs = [i.to_dict() for i in inputs_docs]

        # 4. Get recent messages from default session
        session_ref = case_ref.collection("chat_sessions").document("default_session")
        messages_docs = session_ref.collection("messages").order_by("created_at", direction=firestore.Query.DESCENDING).limit(15).get()
        messages = [m.to_dict() for m in reversed(messages_docs)]

        # 5. Get upload metadata
        uploads_docs = case_ref.collection("uploads").get()
        uploads = [{"name": u.to_dict().get("name"), "type": u.to_dict().get("type")} for u in uploads_docs]

        return {
            "case": case_data,
            "latest_analysis": latest_analysis,
            "tasks": tasks,
            "messages": messages,
            "uploads": uploads,
            "case_inputs": case_inputs
        }

    async def ensure_welcome_message(self, db: firestore.Client, case_id: str):
        """Create a welcome message if the default session is empty."""
        case_ref = db.collection("business_cases").document(case_id)
        session_ref = case_ref.collection("chat_sessions").document("default_session")
        
        if not session_ref.get().exists:
            session_ref.set({
                "case_id": case_id,
                "title": "Default Session",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

        msgs = session_ref.collection("messages").limit(1).get()
        if not msgs:
            welcome_content = "Hi, I'll help you evaluate this F&B business idea step by step. You do not need to answer everything perfectly now. Start by sharing anything you already know, such as your business idea, target location, target customers, expected price range, rental/cost estimate, or competitors you are worried about. You can edit your answers later, and I'll update the analysis based on the latest information."
            session_ref.collection("messages").document().set({
                "role": "assistant",
                "content": welcome_content,
                "type": "welcome",
                "ai_mode": "system_guidance",
                "created_at": datetime.utcnow()
            })

    async def save_case_input(self, db: firestore.Client, case_id: str, key: str, data: dict):
        """Save or update a structured case input with revision history."""
        case_ref = db.collection("business_cases").document(case_id)
        input_ref = case_ref.collection("case_inputs").document(key)
        input_doc = input_ref.get()
        
        now = datetime.utcnow()
        new_answer = data.get("answer")
        new_structured = data.get("structured_answer")
        
        if input_doc.exists:
            old_data = input_doc.to_dict()
            if old_data.get("answer") != new_answer or old_data.get("structured_answer") != new_structured:
                # Save revision
                version = old_data.get("version", 1)
                input_ref.collection("revisions").document().set({
                    "previous_answer": old_data.get("answer"),
                    "new_answer": new_answer,
                    "previous_structured": old_data.get("structured_answer"),
                    "new_structured": new_structured,
                    "version": version,
                    "edited_at": now,
                    "related_task_id": data.get("related_task_id")
                })
                
                input_ref.update({
                    "answer": new_answer,
                    "structured_answer": new_structured,
                    "status": data.get("status", "submitted"),
                    "source": data.get("source", "chat"),
                    "updated_at": now,
                    "version": version + 1
                })
        else:
            input_ref.set({
                "key": key,
                "question": data.get("question"),
                "answer": new_answer,
                "structured_answer": new_structured,
                "status": data.get("status", "submitted"),
                "source": data.get("source", "chat"),
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "related_task_id": data.get("related_task_id")
            })

    async def update_case(self, case_id: str, data: dict):
        """Update case metadata."""
        pass

    async def delete_case(self, case_id: str):
        """Delete case and cascade all related records."""
        pass
