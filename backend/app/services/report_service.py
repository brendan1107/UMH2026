"""
Report Service

Compiles business reports and handles PDF export.
"""

from datetime import datetime, timezone
from io import BytesIO
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from google.cloud.firestore_v1 import Query
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.db.database import db as default_db
from app.models.api_place_result import ApiPlaceResult
from app.models.business_case import BusinessCase
from app.models.evidence_upload import EvidenceUpload
from app.models.extracted_fact import ExtractedFact
from app.models.investigation_task import InvestigationTask
from app.models.recommendation import Recommendation
from app.models.report_export import ReportExport
from app.services.mvp_store import store

_DB_CLIENT_UNSET = object()

# What is report_service.py for?
# The report_service.py file defines a service class, ReportService, that contains the core business logic for generating comprehensive business reports and exporting them as PDFs in our application. This includes functions for retrieving the latest report and recommendation for a specific business case, compiling all available evidence (such as facts, tasks, and uploaded files) into a detailed report, and generating a PDF version of the report for users to download. By centralizing this logic in a service class, we can keep our API route handlers clean and focused on handling HTTP requests and responses, while the ReportService takes care of the underlying mechanics of report generation and export. This separation of concerns allows us to maintain a clear structure in our codebase and makes it easier to manage and update our reporting logic as needed.

class ReportService:
    """Service for report generation and export."""

    _fallback_recommendations: dict[tuple[str, str], list[dict]] = {}
    _fallback_exports: dict[tuple[str, str], list[dict]] = {}

    def __init__(
        self,
        db_client: Any = _DB_CLIENT_UNSET,
        storage_client: Any | None = None,
    ):
        self.db = default_db if db_client is _DB_CLIENT_UNSET else db_client
        self.storage_client = storage_client

    async def get_latest_report(self, case_id: str, user_id: str | None = None):
        """Get the latest recommendation and report for a case."""
        case_id = (case_id or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )
        if self.db is None and user_id:
            return self._fallback_get_latest_report(user_id, case_id)
        self._require_firestore()

        case_ref = self._get_existing_case_ref(case_id, user_id=user_id)
        recommendation_doc = self._latest_document(
            case_ref.collection(Recommendation.SUBCOLLECTION),
            order_field="created_at",
        )
        if recommendation_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No report has been generated for this case",
            )

        recommendation = Recommendation.from_dict(
            recommendation_doc.id,
            recommendation_doc.to_dict() or {},
        )
        latest_export = self._latest_report_export(case_id)

        return {
            "case_id": case_id,
            "recommendation": self._serialize_recommendation(recommendation),
            "report": recommendation.full_report,
            "export": self._serialize_export(latest_export) if latest_export else None,
        }

    async def generate_full_report(self, case_id: str, user_id: str | None = None):
        """Compile all evidence into a comprehensive business report."""
        case_id = (case_id or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )
        if self.db is None and user_id:
            return self._fallback_generate_full_report(user_id, case_id)
        self._require_firestore()

        case_ref = self._get_existing_case_ref(case_id, user_id=user_id)
        try:
            case_snapshot = case_ref.get()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to load business case: {exc}",
            )

        business_case = BusinessCase.from_dict(
            case_id,
            case_snapshot.to_dict() or {},
        )
        facts = self._load_extracted_facts(case_ref)
        uploads = self._load_evidence_uploads(case_ref)
        places = self._load_place_results(case_ref)
        recommendation_docs = self._documents(
            case_ref.collection(Recommendation.SUBCOLLECTION),
            order_field="created_at",
            descending=False,
        )
        prior_recommendations = [
            Recommendation.from_dict(doc.id, doc.to_dict() or {})
            for doc in recommendation_docs
        ]
        latest_recommendation = (
            prior_recommendations[-1] if prior_recommendations else None
        )
        tasks = self._load_investigation_tasks(case_ref, recommendation_docs)
        report_context = {
            "case": self._serialize_case(business_case),
            "facts": [self._serialize_fact(fact) for fact in facts],
            "uploads": [self._serialize_upload(upload) for upload in uploads],
            "places": [self._serialize_place(place) for place in places],
            "tasks": [self._serialize_task(task) for task in tasks],
            "latest_recommendation": (
                self._serialize_recommendation(latest_recommendation)
                if latest_recommendation
                else None
            ),
        }
        full_report = self._build_full_report(report_context)
        summary = self._build_report_summary(
            business_case,
            facts,
            uploads,
            places,
            tasks,
        )
        now = datetime.now(timezone.utc)
        recommendation_ref = case_ref.collection(
            Recommendation.SUBCOLLECTION
        ).document()
        recommendation = Recommendation(
            id=recommendation_ref.id,
            case_id=case_id,
            verdict=latest_recommendation.verdict if latest_recommendation else None,
            confidence_score=(
                latest_recommendation.confidence_score
                if latest_recommendation
                else None
            ),
            summary=summary,
            strengths=(
                latest_recommendation.strengths
                if latest_recommendation and latest_recommendation.strengths
                else self._infer_strengths(facts, uploads, places)
            ),
            weaknesses=(
                latest_recommendation.weaknesses
                if latest_recommendation and latest_recommendation.weaknesses
                else self._infer_weaknesses(facts, uploads, tasks)
            ),
            action_items=(
                latest_recommendation.action_items
                if latest_recommendation and latest_recommendation.action_items
                else self._infer_action_items(tasks, facts)
            ),
            full_report=full_report,
            is_provisional=True if latest_recommendation is None else latest_recommendation.is_provisional,
            version=(latest_recommendation.version + 1 if latest_recommendation else 1),
            created_at=now,
        )

        try:
            recommendation_ref.set(recommendation.to_dict())
            self._merge_document(
                case_ref,
                {
                    "updated_at": now,
                    "status": "report_generated",
                },
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save generated report: {exc}",
            )

        return {
            "case_id": case_id,
            "recommendation": self._serialize_recommendation(recommendation),
            "report": recommendation.full_report,
            "context": report_context,
        }

    async def export_pdf(self, case_id: str, user_id: str | None = None):
        """Generate and return a PDF version of the report."""
        case_id = (case_id or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )

        try:
            report_data = await self.get_latest_report(case_id, user_id=user_id)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
            report_data = await self.generate_full_report(case_id, user_id=user_id)

        if not report_data.get("report"):
            report_data = await self.generate_full_report(case_id, user_id=user_id)

        pdf_bytes = self._render_pdf(report_data)
        now = datetime.now(timezone.utc)
        file_name = self._build_pdf_file_name(case_id, now)
        storage_path = f"reports/{case_id}/{file_name}"
        download_url = None

        if self.db is None and user_id:
            report_export = {
                "id": f"report_exports-{uuid4().hex}",
                "case_id": case_id,
                "file_name": file_name,
                "storage_path": None,
                "download_url": None,
                "file_size": len(pdf_bytes),
                "format": "pdf",
                "created_at": now,
            }
            self._fallback_exports.setdefault((user_id, case_id), []).append(
                report_export
            )
            return {
                "case_id": case_id,
                "file_name": file_name,
                "content_type": "application/pdf",
                "pdf_bytes": pdf_bytes,
                "export": report_export,
            }

        if self.storage_client is not None:
            try:
                download_url = await self.storage_client.upload_file(
                    destination_path=storage_path,
                    file_data=pdf_bytes,
                    content_type="application/pdf",
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to upload PDF report: {exc}",
                )

        export_ref = self.db.collection(ReportExport.COLLECTION).document()
        report_export = ReportExport(
            id=export_ref.id,
            case_id=case_id,
            file_name=file_name,
            storage_path=storage_path if download_url else None,
            download_url=download_url,
            file_size=len(pdf_bytes),
            format="pdf",
            created_at=now,
        )
        try:
            export_ref.set(report_export.to_dict())
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save PDF export metadata: {exc}",
            )

        return {
            "case_id": case_id,
            "file_name": file_name,
            "content_type": "application/pdf",
            "pdf_bytes": pdf_bytes,
            "export": self._serialize_export(report_export),
        }

    def _require_firestore(self):
        if self.db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firestore is not configured",
            )

    def _get_existing_case_ref(self, case_id: str, user_id: str | None = None):
        refs = []
        if user_id:
            refs.append(
                self.db.collection("users")
                .document(user_id)
                .collection("cases")
                .document(case_id)
            )
        refs.append(self.db.collection(BusinessCase.COLLECTION).document(case_id))

        try:
            for case_ref in refs:
                if case_ref.get().exists:
                    return case_ref
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business case not found",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to load business case: {exc}",
            )

    def _fallback_get_latest_report(self, user_id: str, case_id: str):
        self._require_fallback_case(user_id, case_id)
        recommendations = self._fallback_recommendations.get((user_id, case_id), [])
        if not recommendations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No report has been generated for this case",
            )
        latest = recommendations[-1]
        exports = self._fallback_exports.get((user_id, case_id), [])
        return {
            "case_id": case_id,
            "recommendation": latest,
            "report": latest.get("full_report"),
            "export": exports[-1] if exports else None,
        }

    def _fallback_generate_full_report(self, user_id: str, case_id: str):
        case = self._require_fallback_case(user_id, case_id)
        tasks = store.list_tasks(user_id, case_id)
        uploads = store.list_uploads(user_id, case_id)
        context = {
            "case": {
                "id": case["id"],
                "user_id": user_id,
                "title": case["title"],
                "description": case.get("description"),
                "mode": case.get("businessStage") or "pre_launch",
                "business_type": None,
                "target_location": None,
                "status": case["status"],
                "created_at": case["createdAt"],
                "updated_at": case["updatedAt"],
            },
            "facts": [],
            "uploads": [
                {
                    "id": upload["id"],
                    "case_id": case_id,
                    "file_name": upload["fileName"],
                    "file_type": upload.get("fileType"),
                    "file_size": upload.get("fileSize"),
                    "storage_path": None,
                    "download_url": upload.get("url"),
                    "ai_summary": None,
                    "analysis_status": "uploaded",
                    "created_at": upload["createdAt"],
                }
                for upload in uploads
            ],
            "places": [],
            "tasks": [
                {
                    "id": task["id"],
                    "recommendation_id": "",
                    "title": task["title"],
                    "description": task.get("description"),
                    "location": None,
                    "priority": "medium",
                    "status": task["status"],
                    "findings": None,
                    "calendar_event_id": None,
                    "due_date": None,
                    "completed_at": None,
                    "created_at": task["createdAt"],
                }
                for task in tasks
            ],
            "latest_recommendation": None,
        }
        full_report = self._build_full_report(context)
        recommendations = self._fallback_recommendations.setdefault(
            (user_id, case_id),
            [],
        )
        now = datetime.now(timezone.utc)
        recommendation = {
            "id": f"recommendations-{uuid4().hex}",
            "case_id": case_id,
            "verdict": None,
            "confidence_score": None,
            "summary": (
                f"Generated report for {case['title']} using "
                f"{len(uploads)} uploads and {len(tasks)} tasks."
            ),
            "strengths": ["Initial report created for the business case."],
            "weaknesses": [],
            "action_items": [
                "Review the generated report and decide whether more evidence is needed."
            ],
            "full_report": full_report,
            "is_provisional": True,
            "version": len(recommendations) + 1,
            "created_at": now,
        }
        recommendations.append(recommendation)
        return {
            "case_id": case_id,
            "recommendation": recommendation,
            "report": full_report,
            "context": context,
        }

    def _require_fallback_case(self, user_id: str, case_id: str) -> dict:
        case = store.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business case not found",
            )
        return case

    def _latest_report_export(self, case_id: str) -> ReportExport | None:
        query = self.db.collection(ReportExport.COLLECTION).where(
            "case_id",
            "==",
            case_id,
        )
        export_doc = self._latest_document(query, order_field="created_at")
        if export_doc is None:
            return None
        return ReportExport.from_dict(export_doc.id, export_doc.to_dict() or {})

    @staticmethod
    def _latest_document(query: Any, order_field: str):
        try:
            query = query.order_by(order_field, direction=Query.DESCENDING).limit(1)
            return next(iter(query.stream()), None)
        except AttributeError:
            documents = list(getattr(query, "documents", {}).values())
            existing_documents = [doc for doc in documents if doc.get().exists]
            existing_documents.sort(
                key=lambda doc: (doc.to_dict() or {}).get(order_field),
                reverse=True,
            )
            return existing_documents[0] if existing_documents else None

    def _load_extracted_facts(self, case_ref: Any) -> list[ExtractedFact]:
        return [
            ExtractedFact.from_dict(doc.id, doc.to_dict() or {})
            for doc in self._documents(
                case_ref.collection(ExtractedFact.SUBCOLLECTION),
                order_field="created_at",
            )
        ]

    def _load_evidence_uploads(self, case_ref: Any) -> list[EvidenceUpload]:
        documents = self._documents(
            case_ref.collection(EvidenceUpload.SUBCOLLECTION),
            order_field="created_at",
        )
        documents.extend(
            self._documents(
                case_ref.collection("uploads"),
                order_field="createdAt",
            )
        )
        return [
            EvidenceUpload.from_dict(doc.id, doc.to_dict() or {})
            for doc in documents
        ]

    def _load_place_results(self, case_ref: Any) -> list[ApiPlaceResult]:
        return [
            ApiPlaceResult.from_dict(doc.id, doc.to_dict() or {})
            for doc in self._documents(
                case_ref.collection(ApiPlaceResult.SUBCOLLECTION),
                order_field="created_at",
            )
        ]

    def _load_investigation_tasks(
        self,
        case_ref: Any,
        recommendation_docs: list,
    ) -> list[InvestigationTask]:
        tasks = []
        direct_task_docs = self._documents(
            case_ref.collection(InvestigationTask.SUBCOLLECTION),
            order_field="createdAt",
        )
        tasks.extend(
            InvestigationTask.from_dict(doc.id, doc.to_dict() or {})
            for doc in direct_task_docs
        )
        for recommendation_doc in recommendation_docs:
            task_docs = self._documents(
                case_ref.collection(Recommendation.SUBCOLLECTION)
                .document(recommendation_doc.id)
                .collection(InvestigationTask.SUBCOLLECTION),
                order_field="created_at",
            )
            tasks.extend(
                InvestigationTask.from_dict(doc.id, doc.to_dict() or {})
                for doc in task_docs
            )
        return tasks

    @staticmethod
    def _documents(query: Any, order_field: str | None = None, descending: bool = False):
        try:
            if order_field:
                direction = Query.DESCENDING if descending else Query.ASCENDING
                query = query.order_by(order_field, direction=direction)
            return list(query.stream())
        except AttributeError:
            documents = [
                doc
                for doc in getattr(query, "documents", {}).values()
                if doc.get().exists
            ]
            if order_field:
                documents.sort(
                    key=lambda doc: (doc.to_dict() or {}).get(order_field),
                    reverse=descending,
                )
            return documents

    def _build_full_report(self, context: dict) -> str:
        case = context["case"]
        latest = context.get("latest_recommendation") or {}
        lines = [
            f"# F&B Genie Business Report: {case.get('title') or 'Untitled Case'}",
            "",
            "## Case Overview",
            f"- Mode: {case.get('mode') or 'unknown'}",
            f"- Business type: {case.get('business_type') or 'not specified'}",
            f"- Target location: {case.get('target_location') or 'not specified'}",
            f"- Description: {case.get('description') or 'not provided'}",
            "",
            "## Current Recommendation",
            f"- Verdict: {latest.get('verdict') or 'not ready'}",
            f"- Confidence: {latest.get('confidence_score') if latest.get('confidence_score') is not None else 'not scored'}",
            f"- Summary: {latest.get('summary') or 'No previous recommendation summary available.'}",
            "",
            "## Evidence Summary",
            f"- Structured facts captured: {len(context['facts'])}",
            f"- Evidence uploads reviewed: {len(context['uploads'])}",
            f"- Place results available: {len(context['places'])}",
            f"- Investigation tasks tracked: {len(context['tasks'])}",
            "",
            "## Structured Facts",
            *self._bullet_lines(
                context["facts"],
                lambda fact: (
                    f"{fact.get('category') or 'general'}: "
                    f"{fact.get('key')} = {fact.get('value')} "
                    f"({fact.get('confidence')})"
                ),
            ),
            "",
            "## Evidence Uploads",
            *self._bullet_lines(
                context["uploads"],
                lambda upload: (
                    f"{upload.get('file_name')} "
                    f"[{upload.get('analysis_status')}]"
                    + (
                        f" - {upload.get('ai_summary')}"
                        if upload.get("ai_summary")
                        else ""
                    )
                ),
            ),
            "",
            "## Nearby Place Context",
            *self._bullet_lines(
                context["places"],
                lambda place: (
                    f"{place.get('name') or 'Unnamed place'}"
                    f" - {place.get('address') or 'no address'}"
                    f" - rating {place.get('rating') or 'n/a'}"
                ),
            ),
            "",
            "## Investigation Tasks",
            *self._bullet_lines(
                context["tasks"],
                lambda task: (
                    f"{task.get('title')} [{task.get('status')}]"
                    + (f" - findings: {task.get('findings')}" if task.get("findings") else "")
                ),
            ),
            "",
            "## Next Actions",
            *self._bullet_lines(
                [{"text": item} for item in (latest.get("action_items") or [])],
                lambda item: item["text"],
            ),
        ]
        return "\n".join(lines)

    @staticmethod
    def _bullet_lines(items: list[dict], formatter) -> list[str]:
        if not items:
            return ["- None recorded"]
        return [f"- {formatter(item)}" for item in items]

    @staticmethod
    def _build_report_summary(
        business_case: BusinessCase,
        facts: list[ExtractedFact],
        uploads: list[EvidenceUpload],
        places: list[ApiPlaceResult],
        tasks: list[InvestigationTask],
    ) -> str:
        return (
            f"Generated report for {business_case.title or 'this case'} using "
            f"{len(facts)} facts, {len(uploads)} uploads, {len(places)} place results, "
            f"and {len(tasks)} investigation tasks."
        )

    @staticmethod
    def _infer_strengths(
        facts: list[ExtractedFact],
        uploads: list[EvidenceUpload],
        places: list[ApiPlaceResult],
    ) -> list[str]:
        strengths = []
        if facts:
            strengths.append("Structured business facts are available for analysis.")
        if uploads:
            strengths.append("User-provided evidence has been uploaded.")
        if places:
            strengths.append("External place context is available.")
        return strengths or ["Initial report created for the business case."]

    @staticmethod
    def _infer_weaknesses(
        facts: list[ExtractedFact],
        uploads: list[EvidenceUpload],
        tasks: list[InvestigationTask],
    ) -> list[str]:
        weaknesses = []
        if not facts:
            weaknesses.append("No structured facts have been captured yet.")
        if not uploads:
            weaknesses.append("No supporting evidence uploads are available yet.")
        pending_tasks = [task for task in tasks if task.status != "completed"]
        if pending_tasks:
            weaknesses.append("Some investigation tasks are still incomplete.")
        return weaknesses or ["No major evidence gaps were detected from stored data."]

    @staticmethod
    def _infer_action_items(
        tasks: list[InvestigationTask],
        facts: list[ExtractedFact],
    ) -> list[str]:
        pending_tasks = [task.title for task in tasks if task.status != "completed"]
        if pending_tasks:
            return pending_tasks[:5]
        if not facts:
            return ["Provide key business facts such as location, budget, rent, and expected demand."]
        return ["Review the generated report and decide whether more evidence is needed."]

    @staticmethod
    def _serialize_case(business_case: BusinessCase) -> dict:
        return {
            "id": business_case.id,
            "user_id": business_case.user_id,
            "title": business_case.title,
            "description": business_case.description,
            "mode": business_case.mode,
            "business_type": business_case.business_type,
            "target_location": business_case.target_location,
            "status": business_case.status,
            "created_at": business_case.created_at,
            "updated_at": business_case.updated_at,
        }

    @staticmethod
    def _serialize_fact(fact: ExtractedFact) -> dict:
        return {
            "id": fact.id,
            "case_id": fact.case_id,
            "category": fact.category,
            "key": fact.key,
            "value": fact.value,
            "confidence": fact.confidence,
            "source": fact.source,
            "created_at": fact.created_at,
        }

    @staticmethod
    def _serialize_upload(upload: EvidenceUpload) -> dict:
        return {
            "id": upload.id,
            "case_id": upload.case_id,
            "file_name": upload.file_name,
            "file_type": upload.file_type,
            "file_size": upload.file_size,
            "storage_path": upload.storage_path,
            "download_url": upload.download_url,
            "ai_summary": upload.ai_summary,
            "analysis_status": upload.analysis_status,
            "created_at": upload.created_at,
        }

    @staticmethod
    def _serialize_place(place: ApiPlaceResult) -> dict:
        return {
            "id": place.id,
            "case_id": place.case_id,
            "place_id": place.place_id,
            "name": place.name,
            "address": place.address,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "place_type": place.place_type,
            "rating": place.rating,
            "review_count": place.review_count,
            "price_level": place.price_level,
            "raw_data": place.raw_data,
            "created_at": place.created_at,
        }

    @staticmethod
    def _serialize_task(task: InvestigationTask) -> dict:
        return {
            "id": task.id,
            "recommendation_id": task.recommendation_id,
            "title": task.title,
            "description": task.description,
            "location": task.location,
            "priority": task.priority,
            "status": task.status,
            "findings": task.findings,
            "calendar_event_id": task.calendar_event_id,
            "due_date": task.due_date,
            "completed_at": task.completed_at,
            "created_at": task.created_at,
        }

    def _merge_document(self, doc_ref: Any, data: dict):
        try:
            doc_ref.update(data)
            return
        except AttributeError:
            pass

        existing = {}
        try:
            snapshot = doc_ref.get()
            if snapshot.exists:
                existing = snapshot.to_dict()
        except Exception:
            existing = {}
        existing.update(data)
        doc_ref.set(existing)

    def _render_pdf(self, report_data: dict) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            title="F&B Genie Business Report",
            leftMargin=48,
            rightMargin=48,
            topMargin=48,
            bottomMargin=48,
        )
        styles = getSampleStyleSheet()
        story = []
        recommendation = report_data.get("recommendation") or {}
        story.append(Paragraph("F&B Genie Business Report", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                f"Case ID: {self._escape_pdf_text(report_data.get('case_id', ''))}",
                styles["Normal"],
            )
        )
        if recommendation.get("verdict"):
            story.append(
                Paragraph(
                    f"Verdict: {self._escape_pdf_text(recommendation['verdict'])}",
                    styles["Heading2"],
                )
            )
        if recommendation.get("summary"):
            story.append(
                Paragraph(
                    self._escape_pdf_text(recommendation["summary"]),
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 12))

        for line in str(report_data.get("report") or "").splitlines():
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 8))
                continue
            if stripped.startswith("# "):
                story.append(
                    Paragraph(self._escape_pdf_text(stripped[2:]), styles["Heading1"])
                )
            elif stripped.startswith("## "):
                story.append(
                    Paragraph(self._escape_pdf_text(stripped[3:]), styles["Heading2"])
                )
            elif stripped.startswith("- "):
                story.append(
                    Paragraph(
                        f"- {self._escape_pdf_text(stripped[2:])}",
                        styles["BodyText"],
                    )
                )
            else:
                story.append(
                    Paragraph(self._escape_pdf_text(stripped), styles["BodyText"])
                )

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _escape_pdf_text(value: Any) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _build_pdf_file_name(case_id: str, created_at: datetime) -> str:
        safe_case_id = re.sub(r"[^A-Za-z0-9_-]+", "-", case_id).strip("-")
        timestamp = created_at.strftime("%Y%m%d%H%M%S")
        return f"fb-genie-report-{safe_case_id}-{timestamp}.pdf"

    @staticmethod
    def _serialize_recommendation(recommendation: Recommendation) -> dict:
        return {
            "id": recommendation.id,
            "case_id": recommendation.case_id,
            "verdict": recommendation.verdict,
            "confidence_score": recommendation.confidence_score,
            "summary": recommendation.summary,
            "strengths": recommendation.strengths or [],
            "weaknesses": recommendation.weaknesses or [],
            "action_items": recommendation.action_items or [],
            "full_report": recommendation.full_report,
            "is_provisional": recommendation.is_provisional,
            "version": recommendation.version,
            "created_at": recommendation.created_at,
        }

    @staticmethod
    def _serialize_export(report_export: ReportExport) -> dict:
        return {
            "id": report_export.id,
            "case_id": report_export.case_id,
            "file_name": report_export.file_name,
            "storage_path": report_export.storage_path,
            "download_url": report_export.download_url,
            "file_size": report_export.file_size,
            "format": report_export.format,
            "created_at": report_export.created_at,
        }
