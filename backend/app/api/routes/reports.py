"""
Reports Routes

Handles report generation, retrieval, and PDF export for business cases.
Reports/recommendations are stored in Firestore:
  business_cases/{case_id}/recommendations/{rec_id}
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.recommendation import Recommendation
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()


def _get_case_ref(db, case_id: str, user_uid: str):
    """Verify case exists and belongs to user."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")
    if case_doc.to_dict().get("user_id") != user_uid:
        raise HTTPException(status_code=403, detail="Not authorized")
    return case_ref


@router.get("/{case_id}/report")
async def get_report(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get the latest recommendation/report for a case."""
    case_ref = _get_case_ref(db, case_id, user["uid"])

    rec_ref = (
        case_ref.collection(Recommendation.SUBCOLLECTION)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )

    for doc in rec_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        return snake_dict_to_camel(data)

    # No report found yet — return a "gathering" status
    return {
        "status": "gathering",
        "summary": "No report generated yet. Complete more tasks and evidence gathering to generate insights.",
        "strengths": [],
        "risks": [],
    }


@router.post("/{case_id}/report/generate")
async def generate_report(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Generate a report and store it in Firestore.

    Currently creates a placeholder report. Will be enhanced with
    real AI-generated content when the GLM integration is ready.
    """
    case_ref = _get_case_ref(db, case_id, user["uid"])
    case_data = case_ref.get().to_dict()

    now = datetime.utcnow()
    rec = Recommendation(
        case_id=case_id,
        summary=f"Generated report for: {case_data.get('title', 'Untitled Case')}",
        strengths=["Database connected", "Evidence gathered"],
        weaknesses=["AI analysis not yet fully integrated"],
        verdict="proceed",
        confidence_score=65,
        is_provisional=True,
        version=1,
        created_at=now,
    )

    doc_ref = case_ref.collection(Recommendation.SUBCOLLECTION).document()
    rec_dict = rec.to_dict()
    doc_ref.set(rec_dict)

    rec_dict["id"] = doc_ref.id
    rec_dict["status"] = "ready"
    return snake_dict_to_camel(rec_dict)


@router.get("/{case_id}/report/pdf")
async def export_report_pdf(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Export report as PDF. MVP returns a simple placeholder PDF."""
    _get_case_ref(db, case_id, user["uid"])

    # Simple MVP PDF — real PDF generation with reportlab/weasyprint can be
    # added later when report content is richer.
    pdf_content = b"%PDF-1.4 F&B Genie Report - MVP placeholder"
    return Response(content=pdf_content, media_type="application/pdf")


@router.post("/{case_id}/final-verdict")
async def generate_verdict(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Generate and store a final verdict for the case.

    Currently uses placeholder logic. Will be enhanced with real AI
    analysis when the GLM integration is complete.
    """
    case_ref = _get_case_ref(db, case_id, user["uid"])
    case_data = case_ref.get().to_dict()

    now = datetime.utcnow()
    verdict_data = {
        "case_id": case_id,
        "status": "ready",
        "verdict": "Continue with caution",
        "verdict_reasoning": (
            f"The {case_data.get('business_type', 'F&B')} concept in "
            f"{case_data.get('target_location', 'the target area')} has merit "
            f"based on available evidence, but competition risk should be monitored."
        ),
        "next_steps": [
            "Finalize lease negotiation",
            "Execute a soft launch with limited menu",
            "Collect customer feedback for first 2 weeks",
        ],
        "created_at": now,
    }

    doc_ref = case_ref.collection(Recommendation.SUBCOLLECTION).document()
    doc_ref.set(verdict_data)

    # Update case status
    case_ref.update({
        "status": "insight_generated",
        "updated_at": now,
    })

    return {
        "verdict": verdict_data["verdict"],
        "reasoning": verdict_data["verdict_reasoning"],
        "nextSteps": verdict_data["next_steps"],
    }
