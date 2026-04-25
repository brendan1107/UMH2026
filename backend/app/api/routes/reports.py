# app/api/routes/reports.py

"""
Reports Routes

Handles report generation, retrieval, and PDF export for business cases.
Reports/recommendations are stored in Firestore:
  business_cases/{case_id}/recommendations/{rec_id}
"""
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.chat import ChatSession, ChatMessage
from app.models.recommendation import Recommendation

# ── AI imports ──
from app.ai.review_layer import run_audit
from app.ai.schemas import BusinessCase as AICase
from app.ai.glm_client import glm_call
from app.ai.prompts_templates import REQUIRED_FACTS
from app.ai.fact_extractor import extract_required_facts_from_messages, extract_required_facts_from_task_submission
from app.ai.fact_deriver import derive_fact_sheet_values, remove_legacy_derived_assumptions

router = APIRouter()
logger = logging.getLogger(__name__)

REQUIRED_FACT_DETAILS = {
    "competitor_count": {
        "category": "market",
        "severity": "high",
        "title": "Missing competitor count",
        "reasoning": "Nearby competitor count is not confirmed, so market saturation cannot be assessed.",
        "mitigation": "Complete a competitor scan within the target catchment before committing to the location.",
    },
    "avg_competitor_rating": {
        "category": "market",
        "severity": "medium",
        "title": "Missing competitor ratings",
        "reasoning": "Average competitor rating is not confirmed, so the quality benchmark is unclear.",
        "mitigation": "Record ratings and review counts for the top nearby competitors.",
    },
    "estimated_footfall_lunch": {
        "category": "market",
        "severity": "high",
        "title": "Missing lunch footfall",
        "reasoning": "Lunch footfall is not estimated, so demand during the key daypart is uncertain.",
        "mitigation": "Run a lunch-period footfall count before relying on revenue projections.",
    },
    "confirmed_rent_myr": {
        "category": "financial",
        "severity": "high",
        "title": "Missing confirmed rent",
        "reasoning": "Monthly rent is not confirmed, so fixed cost and breakeven risk cannot be validated.",
        "mitigation": "Confirm monthly rent and all recurring location costs with the landlord.",
    },
    "break_even_covers": {
        "category": "financial",
        "severity": "high",
        "title": "Missing breakeven covers",
        "reasoning": "Breakeven covers are not calculated, so minimum viable sales volume is unknown.",
        "mitigation": "Calculate daily breakeven covers using rent, staffing, COGS, and expected ticket size.",
    },
}

def _get_case_ref(db, case_id: str, user_uid: str):
    """Verify case exists and belongs to user."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")
    if case_doc.to_dict().get("user_id") != user_uid:
        raise HTTPException(status_code=403, detail="Not authorized")
    return case_ref


def _build_ai_case(case_id: str, case_data: dict, phase: str = "VERDICT") -> AICase:
    """Build an AI case while normalizing nullable Firestore fields."""
    return AICase(
        id=case_id,
        idea=case_data.get("description") or case_data.get("title") or "",
        location=case_data.get("target_location") or "",
        budget_myr=float(case_data.get("budget_myr") or 30000),
        phase=phase,
        fact_sheet=remove_legacy_derived_assumptions(case_data.get("fact_sheet") or {}),
        messages=case_data.get("ai_messages") or [],
    )


def _recent_evidence_messages(messages: list[dict], limit: int = 12) -> list[dict]:
    evidence_messages = []

    for msg in messages:
        content = msg.get("content")
        parsed_content = None

        if isinstance(content, dict):
            parsed_content = content
        elif isinstance(content, str):
            try:
                parsed_content = json.loads(content)
            except (TypeError, ValueError):
                parsed_content = None

        if isinstance(parsed_content, list):
            parsed_content = parsed_content[0] if parsed_content else {}

        if isinstance(parsed_content, dict) and parsed_content.get("type") == "verdict":
            continue

        evidence_messages.append({
            "role": msg.get("role", "user"),
            "content": content,
        })

    return evidence_messages[-limit:]


def _stored_chat_messages(case_ref, limit: int = 100) -> list[dict]:
    messages = []
    session_refs = [case_ref.collection(ChatSession.SUBCOLLECTION).document("default_session")]

    for session_doc in case_ref.collection(ChatSession.SUBCOLLECTION).stream():
        if session_doc.id == "default_session":
            continue
        session_refs.append(session_doc.reference)

    for session_ref in session_refs:
        message_docs = (
            session_ref
            .collection(ChatMessage.SUBCOLLECTION)
            .order_by("created_at")
            .stream()
        )
        for message_doc in message_docs:
            data = message_doc.to_dict() or {}
            messages.append({
                "role": data.get("role", "user"),
                "content": data.get("content", ""),
            })

    return messages[-limit:]


def _task_submission_facts(case_ref) -> dict:
    facts = {}
    for task_doc in case_ref.collection("tasks").stream():
        task_data = task_doc.to_dict() or {}
        if task_data.get("status") != "completed":
            continue

        submitted_value = task_data.get("submitted_value")
        if submitted_value is None:
            continue

        facts.update(extract_required_facts_from_task_submission(task_data, submitted_value))

    return facts


def _number(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _computed_indicators(fact_sheet: dict) -> dict:
    lunch_footfall = _number(fact_sheet.get("estimated_footfall_lunch"))
    break_even = _number(fact_sheet.get("break_even_covers"))
    competitor_count = _number(fact_sheet.get("competitor_count"))
    avg_rating = _number(fact_sheet.get("avg_competitor_rating"))
    rent = _number(fact_sheet.get("confirmed_rent_myr"))
    budget = _number(fact_sheet.get("budget_myr"))

    indicators = {}
    if lunch_footfall and break_even:
        indicators["breakeven_capture_pct_of_lunch_footfall"] = round((break_even / lunch_footfall) * 100, 1)
        indicators["lunch_footfall_to_breakeven_ratio"] = round(lunch_footfall / break_even, 2)
    if competitor_count is not None and avg_rating is not None:
        if competitor_count >= 15 and avg_rating >= 4:
            indicators["market_pressure"] = "high: many competitors and customers rate existing options well"
        elif competitor_count >= 8:
            indicators["market_pressure"] = "medium: crowded market"
        else:
            indicators["market_pressure"] = "low: limited direct competition"
    if rent and budget:
        indicators["rent_months_covered_by_budget"] = round(budget / rent, 1)

    return indicators


def _verdict_strengths(fact_sheet: dict, indicators: dict | None = None) -> list[str]:
    indicators = indicators or _computed_indicators(fact_sheet)
    strengths = []

    lunch_footfall = _number(fact_sheet.get("estimated_footfall_lunch"))
    break_even = _number(fact_sheet.get("break_even_covers"))
    capture_pct = indicators.get("breakeven_capture_pct_of_lunch_footfall")
    if lunch_footfall and break_even and capture_pct is not None:
        if capture_pct <= 15:
            strengths.append(
                f"Demand cushion: break-even requires about {capture_pct:g}% of lunch footfall, so the location has room to work if conversion is realistic."
            )
        elif capture_pct <= 30:
            strengths.append(
                f"Demand is possible but must be proven: the concept needs about {capture_pct:g}% of lunch footfall to buy."
            )

    rent = _number(fact_sheet.get("confirmed_rent_myr"))
    budget = _number(fact_sheet.get("budget_myr"))
    rent_months = indicators.get("rent_months_covered_by_budget")
    if rent and budget and rent_months is not None:
        if rent_months >= 6:
            strengths.append(
                f"Rent pressure is manageable: RM {int(rent):,}/month is covered by the budget for roughly {rent_months:g} months before other costs."
            )
        elif rent_months >= 3:
            strengths.append(
                f"Rent is not immediately overwhelming, with the budget covering roughly {rent_months:g} months of rent before other costs."
            )

    competitor_count = _number(fact_sheet.get("competitor_count"))
    if competitor_count is not None and competitor_count > 0:
        strengths.append(
            f"Market demand is proven: {int(competitor_count)} existing competitors suggest customers already buy this type of product in the area."
        )

    seen = set()
    deduped = []
    for strength in strengths:
        if strength in seen:
            continue
        seen.add(strength)
        deduped.append(strength)

    return deduped[:3]


def _fallback_decision(ai_case: AICase, missing_facts: list[str]) -> tuple[str, float]:
    if len(missing_facts) >= 3:
        return "PIVOT", 0.35

    fact_sheet = ai_case.fact_sheet
    lunch_footfall = _number(fact_sheet.get("estimated_footfall_lunch"))
    break_even = _number(fact_sheet.get("break_even_covers"))
    competitor_count = _number(fact_sheet.get("competitor_count"))
    avg_rating = _number(fact_sheet.get("avg_competitor_rating"))

    capture_pct = (break_even / lunch_footfall) * 100 if lunch_footfall and break_even else None
    crowded_market = competitor_count is not None and competitor_count >= 15
    strong_competitors = avg_rating is not None and avg_rating >= 4.2

    if capture_pct is not None and capture_pct > 60:
        return "STOP", 0.72 if not missing_facts else 0.55
    if capture_pct is not None and capture_pct > 35:
        return "PIVOT", 0.65 if not missing_facts else 0.5
    if crowded_market and strong_competitors and (capture_pct is None or capture_pct > 15):
        return "PIVOT", 0.62 if not missing_facts else 0.5
    if missing_facts:
        return "GO", 0.55
    return "GO", 0.72


def _reasoned_fallback_summary(ai_case: AICase, decision: str, missing_facts: list[str]) -> str:
    fact_sheet = ai_case.fact_sheet
    indicators = _computed_indicators(fact_sheet)
    reasons = []

    competitor_count = _number(fact_sheet.get("competitor_count"))
    avg_rating = _number(fact_sheet.get("avg_competitor_rating"))
    if competitor_count is not None:
        if avg_rating is not None:
            reasons.append(
                f"{int(competitor_count)} competitors with a {avg_rating:g} average rating means the market is already served, so winning customers will depend on a clear differentiation or convenience advantage."
            )
        else:
            reasons.append(
                f"{int(competitor_count)} competitors means the market is crowded, but competitor quality is still unclear because ratings are missing."
            )

    lunch_footfall = _number(fact_sheet.get("estimated_footfall_lunch"))
    break_even = _number(fact_sheet.get("break_even_covers"))
    capture_pct = indicators.get("breakeven_capture_pct_of_lunch_footfall")
    if lunch_footfall is not None and break_even is not None and capture_pct is not None:
        reasons.append(
            f"With {int(lunch_footfall)} lunch footfall and {int(break_even)} break-even covers, the concept needs about {capture_pct:g}% of lunch traffic to buy, which is the key demand test."
        )
    elif break_even is not None:
        reasons.append(
            f"Break-even is {int(break_even)} covers/day, but without lunch footfall the demand side cannot be judged."
        )

    rent = _number(fact_sheet.get("confirmed_rent_myr"))
    budget = _number(fact_sheet.get("budget_myr")) or ai_case.budget_myr
    if rent is not None:
        rent_months = round(budget / rent, 1) if rent else None
        reasons.append(
            f"Confirmed rent of RM {int(rent):,}/month is manageable against a RM {budget:,.0f} budget, covering roughly {rent_months:g} months of rent before other costs."
        )

    if missing_facts:
        missing = ", ".join(fact.replace("_", " ") for fact in missing_facts)
        reasons.append(f"The verdict remains provisional because these facts are still missing: {missing}.")

    if not reasons:
        reasons.append("There is not enough structured evidence to explain the business risk beyond a provisional recommendation.")

    if decision == "GO":
        conclusion = "Continue is reasonable only if the operator validates conversion and differentiation before committing the full budget."
    elif decision == "PIVOT":
        conclusion = "Pivot is recommended because the current evidence shows meaningful uncertainty or pressure that should be resolved before committing."
    else:
        conclusion = "Stop is recommended because the current numbers imply the required demand or competitive position is not realistic enough."

    return " ".join([*reasons, conclusion])


def _report_verdict_system_prompt(missing_facts: list[str]) -> str:
    return f"""You are F&B Genie, a professional Malaysian F&B feasibility analyst.

Generate a fresh verdict report from the current case snapshot only.
Do not reuse, copy, or summarize any previous verdict.
Write for a user with little or no business experience. Be clear, practical, and calm.

Rules:
1. Output JSON only, matching this exact shape:
   {{"type":"verdict","decision":"GO|PIVOT|STOP","confidence":0.0-1.0,"summary":"5-7 short sentences in plain English","pivot_suggestion":"optional next move or null","strengths":["1-3 specific strengths from the evidence"]}}
2. Never invent numbers. Use only fact_sheet, computed_indicators, supporting_facts, evidence_assessment, missing_required_facts, and recent_evidence_messages.
3. Do not merely list facts. Every sentence must explain what a fact means for the decision.
4. Use simple business language. If you mention terms like break-even or capture rate, explain them briefly in the same sentence.
5. Cover these points when the facts exist:
   - Demand: whether footfall is enough, and what share of that footfall must buy.
   - Competition: what competitor count and ratings mean for customer switching difficulty.
   - Financial pressure: rent, fixed cost, break-even covers, and budget risk.
   - Uncertainty: which missing or suspicious facts reduce confidence.
6. Decision calibration:
   - Use GO only when the numbers look workable and the main risks are manageable.
   - Use PIVOT when the idea may work but needs a change, narrower target, better location, lower cost, or more evidence.
   - Use STOP when the current numbers suggest demand, competition, or cost risk is too high to proceed safely.
7. If evidence is incomplete, keep confidence below 0.65 and clearly say the verdict is provisional.
8. If a provided number looks unusual or too good to rely on, do not reject it automatically; say it should be verified.
9. Do not start the summary with "Known facts currently available".
10. The final sentence must clearly state why the selected decision follows from the facts.
11. Strengths must be evidence-based advantages only. Do not include generic praise.

Missing required facts: {missing_facts or "none"}"""


async def _generate_ai_report_verdict(
    ai_case: AICase,
    missing_facts: list[str],
    supporting_facts: list[dict] | None = None,
    evidence_assessment: dict | None = None,
) -> dict:
    user_payload = {
        "idea": ai_case.idea,
        "location": ai_case.location,
        "budget_myr": ai_case.budget_myr,
        "fact_sheet": ai_case.fact_sheet,
        "computed_indicators": _computed_indicators({**ai_case.fact_sheet, "budget_myr": ai_case.budget_myr}),
        "supporting_facts": supporting_facts or [],
        "evidence_assessment": evidence_assessment or {},
        "missing_required_facts": missing_facts,
        "recent_evidence_messages": _recent_evidence_messages(ai_case.messages),
    }
    output = await glm_call(
        system=_report_verdict_system_prompt(missing_facts),
        messages=[{
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=True, default=str),
        }],
    )

    if output.type != "verdict":
        raise ValueError(f"Report verdict generation returned {output.type}, expected verdict.")

    ai_case.messages.append({
        "role": "assistant",
        "content": output.model_dump_json(),
    })
    ai_case.phase = "VERDICT"
    return output.model_dump()


def _frontend_verdict_label(decision: str | None, confidence: float | None) -> str:
    if decision == "GO":
        return "Continue with caution" if (confidence or 0) < 0.65 else "Continue"
    if decision == "PIVOT":
        return "Pivot"
    if decision == "STOP":
        return "Stop / Cancel"
    return "Continue with caution"


def _frontend_next_steps(result: dict) -> list[str]:
    if result.get("pivot_suggestion"):
        return [result["pivot_suggestion"]]

    risks = result.get("audit_risks") or []
    mitigations = [risk.get("mitigation") for risk in risks if risk.get("mitigation")]
    if mitigations:
        return mitigations

    verdict = result.get("verdict")
    if verdict == "GO":
        return ["Validate launch assumptions with a small pilot before committing full budget."]
    if verdict == "PIVOT":
        return ["Refine the concept using the strongest evidence collected before continuing."]
    if verdict == "STOP":
        return ["Do not proceed until the major risks are resolved with new evidence."]
    return ["Collect any missing evidence before making the final decision."]


def _frontend_verdict_response(result: dict) -> dict:
    confidence = result.get("confidence")
    return {
        "verdict": _frontend_verdict_label(result.get("verdict"), confidence),
        "reasoning": result.get("summary") or "Verdict generated from the current investigation evidence.",
        "nextSteps": _frontend_next_steps(result),
        "strengths": result.get("strengths") or [],
        "confidence": confidence,
        "rawVerdict": result.get("verdict"),
        "risks": result.get("audit_risks") or [],
    }


def _missing_required_facts(fact_sheet: dict) -> list[str]:
    return [fact for fact in REQUIRED_FACTS if fact not in fact_sheet or fact_sheet.get(fact) in (None, "")]


def _missing_fact_risks(missing_facts: list[str]) -> list[dict]:
    risks = []
    for fact in missing_facts:
        detail = REQUIRED_FACT_DETAILS.get(fact)
        if detail:
            risks.append(detail | {"source": "missing_required_fact", "fact": fact})
        else:
            risks.append({
                "category": "ops",
                "severity": "medium",
                "title": f"Missing {fact.replace('_', ' ')}",
                "reasoning": f"{fact.replace('_', ' ').title()} is not available in the current evidence.",
                "mitigation": "Collect this missing evidence before making a high-confidence decision.",
                "source": "missing_required_fact",
                "fact": fact,
            })
    return risks


def _dedupe_risks(risks: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for risk in risks:
        key = (risk.get("title"), risk.get("reasoning"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(risk)
    return deduped


def _flexible_verdict_data(ai_case: AICase, missing_facts: list[str]) -> dict:
    decision, confidence = _fallback_decision(ai_case, missing_facts)
    summary = _reasoned_fallback_summary(ai_case, decision, missing_facts)

    if decision == "PIVOT":
        pivot_suggestion = "Collect the missing facts listed under Identified Risks, then regenerate the verdict."
    elif decision == "STOP":
        pivot_suggestion = "Do not proceed unless new evidence materially improves the demand or cost picture."
    else:
        pivot_suggestion = None

    return {
        "type": "verdict",
        "decision": decision,
        "confidence": confidence,
        "summary": summary,
        "strengths": _verdict_strengths({**ai_case.fact_sheet, "budget_myr": ai_case.budget_myr}),
        "pivot_suggestion": pivot_suggestion,
        "generated_from": "flexible_report",
        "missing_facts": missing_facts,
    }


def _frontend_report_response(result: dict) -> dict:
    risks = result.get("audit_risks") or []
    response = {
        "status": "ready",
        "summary": result.get("summary") or "No report generated yet. Please complete the investigation.",
        "strengths": result.get("strengths") or _verdict_strengths(result.get("fact_sheet") or {}),
        "risks": [
            f"{risk.get('title')}: {risk.get('reasoning')}"
            for risk in risks
            if risk.get("title") or risk.get("reasoning")
        ],
    }

    if result.get("verdict"):
        verdict_response = _frontend_verdict_response(result)
        response.update({
            "verdict": verdict_response["verdict"],
            "verdictReasoning": verdict_response["reasoning"],
            "nextSteps": verdict_response["nextSteps"],
        })

    return response


@router.get("/{case_id}/report")
async def get_report(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Fetch the latest generated report for the UI."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    rec_ref = case_ref.collection(Recommendation.SUBCOLLECTION).order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).stream()
    
    for doc in rec_ref:
        data = doc.to_dict()
        response = _frontend_report_response(data)
        response["id"] = doc.id
        return response

    # No report found yet — return a "gathering" status
    return {
        "status": "ready",
        "summary": "No report generated yet. Please complete the investigation.",
        "strengths": [],
        "risks": [],
    }


@router.get("/{case_id}/report/pdf")
async def export_report_pdf(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Generate and download the PDF report using the PDFGenerator utility."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    doc = case_ref.get()
    case_data = doc.to_dict()
    verdict_raw = case_data.get("verdict")

    if not verdict_raw:
        latest_recommendations = (
            case_ref
            .collection(Recommendation.SUBCOLLECTION)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for recommendation_doc in latest_recommendations:
            verdict_raw = recommendation_doc.to_dict()
            break

    if not verdict_raw:
        raise HTTPException(status_code=400, detail="Generate verdict first before downloading PDF")

    from app.utils.pdf_generator import PDFGenerator

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
        strengths=verdict_raw.get("strengths") or [],
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=fnb-genie-{case_id[:8]}.pdf"
        }
    )


@router.post("/{case_id}/verdict")
@router.post("/{case_id}/final-verdict")
async def generate_verdict(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Trigger verdict generation and return the frontend verdict shape."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    doc = case_ref.get()
    case_data = doc.to_dict()

    ai_case = _build_ai_case(case_id, case_data)
    fact_sheet_changed = ai_case.fact_sheet != (case_data.get("fact_sheet") or {})
    extracted_facts = extract_required_facts_from_messages(ai_case.messages)
    extracted_facts.update(extract_required_facts_from_messages(_stored_chat_messages(case_ref)))
    extracted_facts.update(_task_submission_facts(case_ref))
    if extracted_facts:
        ai_case.fact_sheet.update(extracted_facts)
    derived_facts = derive_fact_sheet_values(ai_case.fact_sheet, ai_case.budget_myr)
    if derived_facts:
        ai_case.fact_sheet.update(derived_facts)
    if fact_sheet_changed or extracted_facts or derived_facts:
        case_ref.update({
            "fact_sheet": ai_case.fact_sheet,
            "updated_at": datetime.utcnow(),
        })

    missing_facts = _missing_required_facts(ai_case.fact_sheet)
    missing_risks = _missing_fact_risks(missing_facts)

    try:
        verdict_data = await _generate_ai_report_verdict(
            ai_case,
            missing_facts,
            case_data.get("supporting_facts") or [],
            case_data.get("evidence_assessment") or {},
        )
        case_ref.update({
            "ai_phase": ai_case.phase,
            "ai_messages": ai_case.messages,
            "updated_at": datetime.utcnow(),
        })
    except httpx.TimeoutException:
        logger.exception("AI verdict generation timed out for case_id=%s", case_id)
        verdict_data = _flexible_verdict_data(ai_case, missing_facts)
    except httpx.HTTPError:
        logger.exception("AI verdict generation request failed for case_id=%s", case_id)
        verdict_data = _flexible_verdict_data(ai_case, missing_facts)
    except Exception:
        logger.exception("AI verdict generation failed for case_id=%s", case_id)
        verdict_data = _flexible_verdict_data(ai_case, missing_facts)

    if missing_facts:
        audit_risks = []
    else:
        try:
            audit_result = await run_audit(ai_case, verdict_data.get("summary", ""))
            audit_risks = [risk.model_dump() for risk in audit_result.risks]
        except httpx.TimeoutException:
            logger.exception("AI audit generation timed out for case_id=%s", case_id)
            audit_risks = []
        except httpx.HTTPError:
            logger.exception("AI audit generation request failed for case_id=%s", case_id)
            audit_risks = []
        except Exception:
            logger.exception("AI audit generation failed for case_id=%s", case_id)
            audit_risks = []

    audit_risks = _dedupe_risks([*missing_risks, *audit_risks])
    strengths = verdict_data.get("strengths") or _verdict_strengths({
        **ai_case.fact_sheet,
        "budget_myr": ai_case.budget_myr,
    })

    result = {
        "verdict":          verdict_data.get("decision"),
        "confidence":       verdict_data.get("confidence"),
        "summary":          verdict_data.get("summary"),
        "strengths":        strengths,
        "pivot_suggestion": verdict_data.get("pivot_suggestion"),
        "audit_risks":      audit_risks,
        "missing_facts":    missing_facts,
        "fact_sheet":       ai_case.fact_sheet,
        "supporting_facts": case_data.get("supporting_facts") or [],
        "evidence_assessment": case_data.get("evidence_assessment") or {},
        "created_at":       datetime.utcnow(),
    }

    case_ref.collection(Recommendation.SUBCOLLECTION).add(result)
    case_ref.update({"status": "verdict_ready", "verdict": result})

    return _frontend_verdict_response(result)
