# app/ai/review_layer.py
import json
import os
import httpx
from pathlib import Path

# Force load .env — walk up until we find it
_env = Path(__file__)
for _ in range(5):
    _env = _env.parent
    if (_env / ".env").exists():
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_env / ".env", override=True)
        break

from app.ai.prompts_templates import AUDITOR_PROMPT
from app.ai.schemas import AuditResult, BusinessCase

ZAI_BASE = os.getenv("GLM_API_BASE_URL", "").rstrip("/")
ZAI_KEY  = os.getenv("GLM_API_KEY", "")

async def run_audit(case: BusinessCase, plan_summary: str) -> AuditResult:
    # 1. Define the model explicitly here!
    model_name = os.getenv("GLM_MODEL_NAME", "ilmu-glm-5.1")

    user_content = json.dumps({
        "business_plan_summary": plan_summary,
        "fact_sheet": case.fact_sheet,
        "location": case.location,
        "budget_myr": case.budget_myr,
    })

    # 2. Use 120s timeout to give AI time to think
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{ZAI_BASE}/chat/completions",  # 3. Correct endpoint
            headers={"Authorization": f"Bearer {ZAI_KEY}"},
            json={
                "model": model_name,         # 4. Use the fixed variable
                "messages": [
                    {"role": "system", "content": AUDITOR_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                "temperature": 0.2,
                "max_tokens": 2500,
            },
        )
        resp.raise_for_status()

    # 1. Safely parse the raw JSON first
    raw_data = resp.json()
    content = raw_data["choices"][0]["message"].get("content")
    
    # 2. Check if the AI returned null/None
    if content is None:
        raise ValueError(f"GLM returned null content. Full response: {raw_data}")

    # 3. Now it is safe to strip
    content = content.strip()
    
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
            
    data = json.loads(content.strip())
    return AuditResult(**data)