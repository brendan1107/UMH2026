# all pydantic models for ai agent

# app/ai/schemas.py
from pydantic import BaseModel, UUID4
from typing import Any, Literal, Optional
from datetime import datetime

# ── Phase machine ──────────────────────────────────────────
Phase = Literal[
    "INTAKE",
    "MARKET_SCAN",
    "TASK_ASSIGNMENT",
    "EVIDENCE",
    "VERDICT",
]

# ── What the GLM is allowed to output ─────────────────────
class ToolCallOutput(BaseModel):
    type: Literal["tool_call"]
    tool: Literal["fetch_competitors", "estimate_footfall", "calculate_breakeven"]
    args: dict[str, Any]

class TaskOption(BaseModel):
    id: str
    title: str

class TaskQuestion(BaseModel):
    id: str
    label: str

class TaskDef(BaseModel):
    title: str
    instruction: str
    ai_message: Optional[str] = None
    follow_up_action: Optional[str] = None
    evidence_type: Literal["count", "photo", "rating", "text", "location", "schedule", "decision", "questions"]
    options: Optional[list[TaskOption]] = None
    questions: Optional[list[TaskQuestion]] = None
    event_title: Optional[str] = None
    event_duration: Optional[str] = None

class TaskBatchOutput(BaseModel):
    type: Literal["task_batch"]
    chat_message: Optional[str] = None
    tasks: list[TaskDef]

class ClarifyOutput(BaseModel):
    type: Literal["clarify"]
    question: str
    options: list[str]

class VerdictOutput(BaseModel):
    type: Literal["verdict"]
    decision: Literal["GO", "PIVOT", "STOP"]
    confidence: float          # 0.0 – 1.0
    summary: str               # 2–3 sentence exec summary
    pivot_suggestion: Optional[str] = None  # only if PIVOT

# Union — every GLM response must be one of these
AgentOutput = ToolCallOutput | TaskBatchOutput | ClarifyOutput | VerdictOutput

# ── Tool return types ──────────────────────────────────────
class CompetitorResult(BaseModel):
    count: int
    avg_rating: float
    nearest_m: int             # distance to nearest competitor
    price_levels: list[int]    # 1=cheap, 4=expensive

class FootfallEstimate(BaseModel):
    estimated_pax_per_hour: int
    peak_hours: list[str]
    confidence: str            # "high" | "medium" | "low"

class BreakevenModel(BaseModel):
    breakeven_covers_per_day: int
    months_to_breakeven: float
    min_viable_revenue_myr: float

# ── Auditor output ─────────────────────────────────────────
class RiskItem(BaseModel):
    category: Literal["financial", "market", "ops", "regulatory"]
    severity: Literal["high", "medium", "low"]
    title: str
    reasoning: str             # must cite a number from fact_sheet
    mitigation: str

class AuditResult(BaseModel):
    risks: list[RiskItem]      # always exactly 3

# ── Business case (mirrors Supabase table) ─────────────────
class BusinessCase(BaseModel):
    id: str
    idea: str
    location: str
    budget_myr: Optional[float] = None
    phase: Phase
    fact_sheet: dict[str, Any]   # grows as tools return data
    messages: list[dict]          # full GLM conversation history
    market_context: Optional[str] = None
    tasks: Optional[list[dict[str, Any]]] = None
    location_analysis: Optional[dict[str, Any]] = None
    case_inputs: Optional[list[dict[str, Any]]] = None
