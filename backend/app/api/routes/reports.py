# app/api/routes/reports.py

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

# ── AI imports ──
from app.ai.review_layer import run_audit
from app.ai.schemas import BusinessCase as AICase

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
    """Fetch the latest generated report for the UI."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    rec_ref = case_ref.collection(Recommendation.SUBCOLLECTION).order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).stream()
    
    latest_rec = None
    for doc in rec_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        return snake_dict_to_camel(data)

    # No official report found yet — return a location-aware summary if available
    doc = case_ref.get()
    case_data = doc.to_dict()
    
    if case_data.get("latest_location_analysis_id"):
        risk_level = case_data.get("latest_market_risk_level")
        risk_score = case_data.get("latest_market_risk_score")
        competitor_count = case_data.get("latest_competitor_count")
        strong_threats = case_data.get("latest_strong_competitor_count")
        resolved_name = case_data.get("latest_resolved_location_name")
        summary = case_data.get("latest_market_summary")

        return snake_dict_to_camel({
            "status": "gathering",
            "summary": f"Location Intelligence for {resolved_name} is ready. {summary}",
            "executive_summary": f"{resolved_name} shows a {risk_level} market risk ({risk_score}/10) with {competitor_count} nearby competitors and {strong_threats} high-rated threats.",
            "strengths": [
                "Detailed location intelligence gathered",
                f"Resolved exact address: {case_data.get('latest_resolved_address')}",
                "Competitor density mapped"
            ],
            "risks": [
                f"Market risk level is {risk_level}",
                f"{strong_threats} strong competitors within walking distance",
                "Market saturated with similar concepts" if risk_level == "High" else "Unverified demand in low-density area"
            ],
            "next_steps": [
                "Define target customer segment",
                "Compare competitor pricing",
                "Analyze unique value proposition"
            ]
        })

    return {
        "status": "pending",
        "summary": "No report generated yet. Please run Market Analysis or talk to AI to gather data.",
    }


@router.get("/{case_id}/report/pdf")
async def export_report_pdf(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Generate and download the PDF report using the PDFGenerator utility."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = case_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = doc.to_dict()
    verdict_raw = case_data.get("verdict")
    
    if not verdict_raw:
        raise HTTPException(status_code=400, detail="Generate verdict first before downloading PDF")

    # Import your utility here
    from app.utils.pdf_generator import PDFGenerator

    # Pass the data directly from Firestore into your PDF Generator
    pdf_bytes = PDFGenerator().generate_feasibility_report(
        case_id=case_id,
        idea=case_data.get("description") or case_data.get("title") or "Unknown",
        location=case_data.get("target_location") or "Malaysia",
        budget_myr=float(case_data.get("budget_myr") or 30000),
        verdict={
            "decision":         verdict_raw.get("verdict"),
            "confidence":       verdict_raw.get("confidence", 0.8),
            "summary":          verdict_raw.get("summary", ""),
            "pivot_suggestion": verdict_raw.get("pivot_suggestion"),
        },
        fact_sheet=case_data.get("fact_sheet") or {},
        audit_risks=verdict_raw.get("audit_risks") or [],
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=fnb-genie-{case_id[:8]}.pdf"
        }
    )


@router.post("/{case_id}/final-verdict")
async def generate_verdict(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Trigger the AI Auditor to finalize the investigation and create the verdict data."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = case_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = doc.to_dict()

    # Build the AI Case model to pass to the auditor
    ai_case = AICase(
        id=case_id,
        idea=case_data.get("description", case_data.get("title", "")),
        location=case_data.get("target_location", ""),
        budget_myr=float(case_data.get("budget_myr", 30000)),
        phase=case_data.get("ai_phase", "VERDICT"),
        fact_sheet=case_data.get("fact_sheet", {}),
        messages=case_data.get("ai_messages", []),
    )

    # Get the last verdict output from the AI's messages
    verdict_data = None
    for msg in reversed(ai_case.messages):
        try:
            import json
            content = json.loads(msg.get("content", "{}"))
            if content.get("type") == "verdict":
                verdict_data = content
                break
        except Exception:
            continue

    if not verdict_data:
        raise HTTPException(status_code=400, detail="No verdict found in chat history. Complete the investigation first.")

    # Run the auditor (Pass 2) to find the 3 failure risks
    audit_result = await run_audit(ai_case, verdict_data.get("summary", ""))

    # Structure the final result to save to Firestore
    result = {
        "verdict":          verdict_data.get("decision"),
        "confidence":       verdict_data.get("confidence"),
        "summary":          verdict_data.get("summary"),
        "pivot_suggestion": verdict_data.get("pivot_suggestion"),
        "audit_risks":      [r.model_dump() for r in audit_result.risks],
        "fact_sheet":       ai_case.fact_sheet,
        "created_at":       datetime.utcnow(),
    }
    
    # Save the recommendation and update the main case document
    case_ref.collection(Recommendation.SUBCOLLECTION).add(result)
    case_ref.update({"status": "verdict_ready", "verdict": result})

    return result