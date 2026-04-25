"""
Business Case Service

Business logic for creating, managing, and analyzing business cases.
"""

# What is case_service.py for?
# The case_service.py file defines a service class, CaseService, that contains the core business logic for handling operations related to business cases in our application. This includes functions for creating new business cases, retrieving case details along with all related data (such as facts, tasks, and recommendations), updating case metadata, and deleting cases along with their associated records. By centralizing this logic in a service class, we can keep our API route handlers clean and focused on handling HTTP requests and responses, while the CaseService takes care of the underlying mechanics of managing business cases. This separation of concerns allows us to maintain a clear structure in our codebase and makes it easier to manage and update our business case logic as needed.


from datetime import datetime
from google.cloud import firestore
from typing import Any, Optional
import re

CANONICAL_KEY_MAP = {
    "business_idea": ["business idea", "concept", "food business idea"],
    "target_customer": ["analyze target audience", "confirm target customer", "define target customer segment", "target audience", "audience", "target group", "main customer"],
    "pricing_strategy": ["review pricing strategy", "compare nearby competitor pricing", "confirm price range", "review pricing", "pricing", "competitor pricing", "price range", "positioning"],
    "target_location": ["select location", "confirm location", "target location", "site selection"],
    "monthly_rent": ["confirm rent", "estimate monthly rent", "upload rental cost estimate", "kiosk cost", "monthly rent", "rental cost", "rent"],
    "cost_per_unit": ["confirm cost per item", "estimate cost per drink", "estimate food unit cost", "calculate cost per unit", "cost per item", "cost per unit", "unit cost", "cogs", "cost per drink", "cost per food unit"],
    "daily_sales_target": ["estimate daily sales", "break-even sales", "break even sales", "confirm daily sales target", "daily sales", "sales target", "expected daily sales"],
    "differentiation": ["confirm differentiation", "refine differentiation strategy", "identify unique value", "differentiation", "unique selling point", "unique concept", "value proposition"],
    "competitor_price": ["confirm competitor price", "compare competitor pricing", "competitor price", "competitor pricing", "nearby competitor price"],
    "competitor_review": ["analyze competitors", "competitor review", "competitor analysis"],
    "evidence_upload": ["upload photo", "upload evidence", "photo evidence", "site photo"],
    "final_recommendation": ["final recommendation", "feasibility recommendation", "what should i do next"],
}

INPUT_PRIORITY = [
    "business_idea",
    "target_location",
    "target_customer",
    "pricing_strategy",
    "cost_per_unit",
    "monthly_rent",
    "daily_sales_target",
    "differentiation",
    "competitor_price",
    "evidence_upload",
    "final_recommendation",
]

INPUT_QUESTIONS = {
    "business_idea": "What F&B business idea are you evaluating?",
    "target_location": "Which exact target location should I evaluate?",
    "target_customer": "Who is your main target customer group?",
    "pricing_strategy": "What is your expected selling price range and positioning?",
    "cost_per_unit": "What is your estimated cost per item?",
    "monthly_rent": "What is your estimated monthly rent or kiosk cost?",
    "daily_sales_target": "How many daily sales do you expect or need to break even?",
    "differentiation": "What makes your concept different from existing competitors?",
    "competitor_price": "What competitor price or competitor benchmark should we compare against?",
    "evidence_upload": "Do you have any evidence to upload, such as a rental quote, menu photo, or competitor price photo?",
}

INPUT_TYPES = {
    "business_idea": "text",
    "target_location": "location",
    "target_customer": "questions",
    "pricing_strategy": "questions",
    "cost_per_unit": "number_currency",
    "monthly_rent": "number_currency",
    "daily_sales_target": "number",
    "differentiation": "text",
    "competitor_price": "number_currency",
    "evidence_upload": "upload",
}


def _normalize_key_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _timestamp_sort_value(value: Any) -> float:
    if hasattr(value, "timestamp"):
        try:
            return value.timestamp()
        except Exception:
            return 0
    return 0


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

        # 2. Get all tasks and deduplicate by canonicalKey
        tasks_stream = case_ref.collection("tasks").order_by("created_at").get()
        tasks_dict = {}
        for t in tasks_stream:
            t_data = t.to_dict()
            t_data["id"] = t.id
            
            # Derive canonicalKey if missing
            key = t_data.get("canonical_key") or self.derive_canonical_key(t_data.get("title", ""))
            t_data["canonical_key"] = key
            
            # Deduplication logic: Completed > Latest > Pending
            if not key or key == "general":
                key = self.derive_canonical_key(t_data.get("title", ""))
            t_data["canonical_key"] = key

            if key not in tasks_dict:
                tasks_dict[key] = t_data
            else:
                existing = tasks_dict[key]
                if t_data.get("status") == "completed" and existing.get("status") != "completed":
                    # Mark existing as merged
                    if existing.get("id") != t_data.get("id"):
                        case_ref.collection("tasks").document(existing["id"]).update({
                            "status": "merged",
                            "merged_into_task_id": t_data["id"],
                            "updated_at": datetime.utcnow()
                        })
                    tasks_dict[key] = t_data
                elif t_data.get("status") == "merged":
                    continue
                elif existing.get("status") == "merged":
                    tasks_dict[key] = t_data
                elif t_data.get("status") == existing.get("status"):
                    # Both same status, take the latest updated
                    if _timestamp_sort_value(t_data.get("updated_at")) > _timestamp_sort_value(existing.get("updated_at")):
                        if existing.get("id") != t_data.get("id"):
                            case_ref.collection("tasks").document(existing["id"]).update({
                                "status": "merged",
                                "merged_into_task_id": t_data["id"],
                                "updated_at": datetime.utcnow()
                            })
                        tasks_dict[key] = t_data
                    else:
                        if existing.get("id") != t_data.get("id"):
                             case_ref.collection("tasks").document(t_data["id"]).update({
                                "status": "merged",
                                "merged_into_task_id": existing["id"],
                                "updated_at": datetime.utcnow()
                            })
        
        data["tasks"] = [t for t in tasks_dict.values() if t.get("status") != "merged"]

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
        latest_analysis_id = case_data.get("latest_location_analysis_id") or case_data.get("latestLocationAnalysisId")
        if latest_analysis_id:
            analysis_doc = case_ref.collection("place_results").document(latest_analysis_id).get()
            if analysis_doc.exists:
                latest_analysis = analysis_doc.to_dict()

        # 2. Get all tasks and their responses (deduplicated)
        tasks_docs = case_ref.collection("tasks").order_by("created_at").get()
        tasks_dict = {}
        for t in tasks_docs:
            t_data = t.to_dict()
            key = t_data.get("canonical_key") or self.derive_canonical_key(t_data.get("title", ""))
            
            t_payload = {
                "id": t.id,
                "title": t_data.get("title"),
                "status": t_data.get("status"),
                "submitted_value": t_data.get("submitted_value"),
                "type": t_data.get("type"),
                "description": t_data.get("description"),
                "canonical_key": key,
                "updated_at": t_data.get("updated_at")
            }
            
            if key not in tasks_dict:
                tasks_dict[key] = t_payload
            else:
                existing = tasks_dict[key]
                if t_payload["status"] == "completed" and existing["status"] != "completed":
                    tasks_dict[key] = t_payload
                elif t_payload["status"] == existing["status"]:
                    if _timestamp_sort_value(t_payload.get("updated_at")) > _timestamp_sort_value(existing.get("updated_at")):
                        tasks_dict[key] = t_payload
        
        tasks = list(tasks_dict.values())

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

    def _summarize_answer(self, structured_answer: Any, key: Optional[str] = None) -> str:
        """Convert structured answers into human-readable text summaries with normalization."""
        if not structured_answer:
            return ""
        
        # If it's a string, try to clean it based on the key
        if isinstance(structured_answer, str):
            val = structured_answer.strip().replace("\\", "").replace("\"", "")
            if key == "daily_sales_target" and val.isdigit():
                return f"{val} sales per day"
            if key == "monthly_rent" and val.isdigit():
                return f"RM{val} per month"
            if key == "competitor_price" and val.isdigit():
                return f"Competitor price: RM{val}"
            if key == "cost_per_unit" and val.isdigit():
                return f"RM{val} cost per unit"
            if key == "differentiation" and len(val) < 20:
                if "better" in val.lower():
                    return f"Differentiation: User claims product is better, but needs more specific proof."
            return val
        
        if isinstance(structured_answer, dict):
            # Flatten common structures
            parts = []
            data = structured_answer.get("answers") or structured_answer.get("values") or structured_answer
            if isinstance(data, dict):
                for k, v in data.items():
                    if v:
                        clean_k = k.replace("_", " ").capitalize()
                        # Recursively clean the value
                        clean_v = self._summarize_answer(v, k)
                        parts.append(f"{clean_k}: {clean_v}" if ":" not in clean_v else clean_v)
                return ", ".join(parts)
            
        if isinstance(structured_answer, list):
            return ", ".join([str(i) for i in structured_answer])
            
        return str(structured_answer)

    def derive_canonical_key(self, title: str) -> str:
        """Derive a canonical key from a task title."""
        if not title:
            return "general"
        
        normalized = _normalize_key_text(title)
        compact = normalized.replace(" ", "")
        
        for key, aliases in CANONICAL_KEY_MAP.items():
            for alias in aliases:
                alias_norm = _normalize_key_text(alias)
                if alias_norm in normalized or alias_norm.replace(" ", "") in compact:
                    return key
        
        if normalized in INPUT_PRIORITY:
            return normalized
        
        return normalized.replace(" ", "_") or "general"

    def normalize_input_key(self, key: Optional[str], title: str = "") -> str:
        """Normalize known input/task keys to their canonical document key."""
        if key:
            normalized_key = key.replace("-", "_").strip().lower()
            if normalized_key in INPUT_PRIORITY or normalized_key in CANONICAL_KEY_MAP:
                return normalized_key
            derived = self.derive_canonical_key(normalized_key.replace("_", " "))
            if derived != "general":
                return derived
        return self.derive_canonical_key(title)

    def get_answered_input_keys(self, case_data: dict, case_inputs: list[dict], latest_analysis: Optional[dict] = None, uploads: Optional[list] = None) -> set[str]:
        """Return input keys that already have reliable saved case memory."""
        answered = set()
        for inp in case_inputs or []:
            key = self.normalize_input_key(inp.get("key"))
            if inp.get("answer") not in (None, "") or inp.get("structured_answer") not in (None, {}, []):
                answered.add(key)

        if case_data.get("description") or case_data.get("title"):
            answered.add("business_idea")
        if (
            latest_analysis
            or case_data.get("latest_location_analysis_id")
            or case_data.get("latestLocationAnalysisId")
            or case_data.get("target_location")
            or case_data.get("latest_resolved_location_name")
        ):
            answered.add("target_location")
        if uploads:
            answered.add("evidence_upload")
        return answered

    def get_next_missing_input(self, case_data: dict, case_inputs: list[dict], latest_analysis: Optional[dict] = None, uploads: Optional[list] = None) -> Optional[dict]:
        """Find the next missing field using the shared follow-up priority."""
        answered = self.get_answered_input_keys(case_data, case_inputs, latest_analysis, uploads)

        core_keys = [
            "business_idea",
            "target_location",
            "target_customer",
            "pricing_strategy",
            "cost_per_unit",
            "monthly_rent",
            "daily_sales_target",
            "differentiation",
            "competitor_price",
        ]
        for key in core_keys:
            if key not in answered:
                return {
                    "key": key,
                    "question": INPUT_QUESTIONS[key],
                    "type": INPUT_TYPES[key],
                }

        return None

    def build_recommendation_from_context(self, case_data: dict, case_inputs: list[dict], latest_analysis: Optional[dict] = None) -> str:
        """Build a concise recommendation using saved memory when AI is unavailable."""
        input_map = {self.normalize_input_key(i.get("key")): i.get("answer") for i in (case_inputs or []) if i.get("answer")}
        location = (
            (latest_analysis or {}).get("resolved_name")
            or case_data.get("latest_resolved_location_name")
            or case_data.get("latestResolvedLocationName")
            or case_data.get("target_location")
            or "the target location"
        )
        risk_level = (latest_analysis or {}).get("risk_level") or case_data.get("latest_market_risk_level") or case_data.get("latestMarketRiskLevel")
        risk_score = (latest_analysis or {}).get("risk_score") or case_data.get("latest_market_risk_score") or case_data.get("latestMarketRiskScore")
        competitor_count = (latest_analysis or {}).get("competitor_count") or case_data.get("latest_competitor_count") or case_data.get("latestCompetitorCount")

        facts = []
        if risk_level:
            score_text = f" ({risk_score}/10)" if risk_score is not None else ""
            facts.append(f"{location} has {risk_level.lower()} market risk{score_text}")
        if competitor_count is not None:
            facts.append(f"{competitor_count} nearby competitors")
        if input_map.get("target_customer"):
            facts.append(f"target customer: {input_map['target_customer']}")
        if input_map.get("pricing_strategy"):
            facts.append(f"pricing: {input_map['pricing_strategy']}")
        if input_map.get("cost_per_unit"):
            facts.append(f"cost per unit: {input_map['cost_per_unit']}")
        if input_map.get("monthly_rent"):
            facts.append(f"monthly rent: {input_map['monthly_rent']}")
        if input_map.get("daily_sales_target"):
            facts.append(f"daily sales target: {input_map['daily_sales_target']}")
        if input_map.get("differentiation"):
            facts.append(f"differentiation: {input_map['differentiation']}")

        if not facts:
            return "I do not have enough saved inputs yet. Start with the business idea, exact location, target customer, pricing, unit cost, rent, and daily sales target."

        return (
            "Based on the saved case data, the next move is to validate margins and differentiation before committing. "
            + "; ".join(facts)
            + ". If the unit margin is thin, raise the bundle value or reduce cost before scaling."
        )

    def _extract_answers_dict(self, structured_answer: Any) -> dict:
        if isinstance(structured_answer, dict):
            answers = structured_answer.get("answers")
            if isinstance(answers, dict):
                return answers
            return structured_answer
        return {}

    def derive_related_inputs(self, key: str, structured_answer: Any) -> dict[str, dict]:
        """Extract clean secondary case inputs from a completed task answer."""
        answers = self._extract_answers_dict(structured_answer)
        if not answers:
            return {}

        related: dict[str, dict] = {}

        if key == "pricing_strategy":
            if answers.get("cost_per_unit"):
                related["cost_per_unit"] = {
                    "answer": self._summarize_answer(answers.get("cost_per_unit"), "cost_per_unit"),
                    "structured_answer": answers.get("cost_per_unit"),
                    "question": "What is your estimated cost per item?",
                }
            if answers.get("competitor_compare"):
                related["competitor_price"] = {
                    "answer": self._summarize_answer(answers.get("competitor_compare"), "competitor_price"),
                    "structured_answer": answers.get("competitor_compare"),
                    "question": "What competitor price or competitor benchmark should we compare against?",
                }

        return related

    async def upsert_task_by_canonical_key(self, db: firestore.Client, case_id: str, task_payload: dict):
        return await self.upsert_task(db, case_id, task_payload)

    async def upsert_task(self, db: firestore.Client, case_id: str, task_payload: dict):
        """Create or update a task based on its canonical key to prevent duplicates."""
        case_ref = db.collection("business_cases").document(case_id)
        tasks_ref = case_ref.collection("tasks")
        
        title = task_payload.get("title", "")
        canonical_key = self.normalize_input_key(task_payload.get("canonical_key"), title)
        incoming_completed = (
            task_payload.get("status") == "completed"
            or task_payload.get("submitted_value") is not None
            or task_payload.get("response_text") is not None
            or task_payload.get("structured_response") is not None
        )
        
        existing_tasks = tasks_ref.where("canonical_key", "==", canonical_key).get()
        active_tasks = [t for t in existing_tasks if t.to_dict().get("status") != "merged"]
        
        now = datetime.utcnow()
        task_payload["canonical_key"] = canonical_key
        task_payload["updated_at"] = now
        
        if active_tasks:
            active_pairs = [(t, t.to_dict()) for t in active_tasks]
            active_pairs.sort(
                key=lambda pair: (
                    1 if pair[1].get("status") == "completed" else 0,
                    _timestamp_sort_value(pair[1].get("updated_at")),
                ),
                reverse=True,
            )
            primary_doc, primary_data = active_pairs[0]
            task_ref = primary_doc.reference

            if primary_data.get("status") == "completed" and not incoming_completed:
                task_ref.set({"canonical_key": canonical_key, "updated_at": now}, merge=True)
                for other_doc, _ in active_pairs[1:]:
                    other_doc.reference.update({
                        "status": "merged",
                        "merged_into_task_id": task_ref.id,
                        "updated_at": now,
                    })
                return task_ref.id
            
            if incoming_completed:
                task_payload["status"] = "completed"
                task_payload.setdefault("completed_at", now)
            else:
                task_payload.setdefault("status", "pending")
            
            for other_doc, _ in active_pairs[1:]:
                other_doc.reference.update({
                    "status": "merged",
                    "merged_into_task_id": task_ref.id,
                    "updated_at": now,
                })
            
            task_ref.set(task_payload, merge=True)
            return task_ref.id
        
        norm_title = _normalize_key_text(title)
        all_tasks = tasks_ref.get()
        for t in all_tasks:
            t_data = t.to_dict()
            if t_data.get("status") == "merged":
                continue
            
            existing_key = t_data.get("canonical_key") or self.derive_canonical_key(t_data.get("title", ""))
            existing_norm = _normalize_key_text(t_data.get("title", ""))
            if existing_key == canonical_key or existing_norm == norm_title:
                if t_data.get("status") == "completed" and not incoming_completed:
                    t.reference.set({"canonical_key": canonical_key, "updated_at": now}, merge=True)
                    return t.id
                if incoming_completed:
                    task_payload["status"] = "completed"
                    task_payload.setdefault("completed_at", now)
                t.reference.set(task_payload, merge=True)
                return t.id

        task_payload.setdefault("status", "completed" if incoming_completed else "pending")
        task_payload["created_at"] = now
        doc_ref = tasks_ref.document()
        doc_ref.set(task_payload)
        return doc_ref.id

    async def sync_chat_answer_to_task(self, db: firestore.Client, case_id: str, key: str, answer: str):
        """Link a chat-provided answer to a task in the roadmap."""
        # Use upsert_task with canonical key
        canonical_key = self.normalize_input_key(key) # key from save_case_input is already the variable name
        
        task_payload = {
            "case_id": case_id,
            "title": f"Confirm {key.replace('_', ' ')}",
            "description": f"User provided {key.replace('_', ' ')} via chat.",
            "status": "completed",
            "submitted_value": answer,
            "response_text": answer,
            "structured_response": answer,
            "type": "provide_text_input",
            "source": "chat_follow_up",
            "canonical_key": canonical_key
        }
        
        await self.upsert_task_by_canonical_key(db, case_id, task_payload)

    async def save_case_input(self, db: firestore.Client, case_id: str, key: str, data: dict):
        """Save or update a structured case input with revision history."""
        key = self.normalize_input_key(key)
        case_ref = db.collection("business_cases").document(case_id)
        input_ref = case_ref.collection("case_inputs").document(key)
        input_doc = input_ref.get()
        
        now = datetime.utcnow()
        new_structured = data.get("structured_answer", data.get("structuredAnswer"))
        
        # Determine the best text answer
        new_answer = data.get("answer")
        if new_structured and (not new_answer or "{" in str(new_answer)):
            new_answer = self._summarize_answer(new_structured, key)
        
        # Sync to task roadmap if it's a direct chat answer
        if data.get("source") == "chat_direct":
            await self.sync_chat_answer_to_task(db, case_id, key, new_answer)
        
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
                    "key": key,
                    "question": data.get("question", old_data.get("question")),
                    "answer": new_answer,
                    "structured_answer": new_structured,
                    "status": data.get("status", "submitted"),
                    "source": data.get("source", "chat"),
                    "related_task_id": data.get("related_task_id", old_data.get("related_task_id")),
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
