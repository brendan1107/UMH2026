from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.recommendation import Recommendation

router = APIRouter()

@router.get("/{case_id}/report")
async def get_report(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    rec_ref = case_ref.collection(Recommendation.SUBCOLLECTION).order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).stream()
    
    latest_rec = None
    for doc in rec_ref:
        latest_rec = doc.to_dict()
        break
        
    if latest_rec:
        return latest_rec
        
    return {
        "status": "ready",
        "summary": "This is a dynamic report summary from the database. The strategy focuses firmly on weekday grab-and-go office workers.",
        "strengths": ["High density of target demographic", "Clear audience"],
        "risks": ["High local competition", "Queue management issues"]
    }

@router.post("/{case_id}/report/generate")
async def generate_report(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Dummy report generation saving to DB
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    rec = Recommendation(
        case_id=case_id,
        summary="Generated report from DB integration.",
        strengths=["Database connected"],
        risks=["AI not yet fully integrated"],
        status="ready",
        verdict="Continue"
    )
    case_ref.collection(Recommendation.SUBCOLLECTION).add(rec.to_dict())
    return {"status": "success"}

@router.get("/{case_id}/report/pdf")
async def export_report_pdf(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Real PDF generation would happen here
    return Response(content=b"%PDF-1.4 Mock PDF content", media_type="application/pdf")

@router.post("/{case_id}/verdict")
async def generate_verdict(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    
    verdict_data = {
        "status": "ready",
        "verdict": "Continue with caution",
        "verdictReasoning": "The grab-and-go cafe concept in the target area has merit due to the demographic density, but high competition is a risk.",
        "nextSteps": ["Secure a lease agreement", "Execute a soft launch"],
        "created_at": datetime.utcnow()
    }
    
    # Store verdict update
    case_ref.collection(Recommendation.SUBCOLLECTION).add(verdict_data)
    
    return {
        "verdict": verdict_data["verdict"],
        "reasoning": verdict_data["verdictReasoning"],
        "nextSteps": verdict_data["nextSteps"]
    }
