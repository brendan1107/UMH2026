# app/ai/review_layer.py
import json

import httpx

from app.ai.prompts_templates import AUDITOR_PROMPT
from app.ai.schemas import AuditResult, BusinessCase
from app.config import settings


async def run_audit(case: BusinessCase, plan_summary: str) -> AuditResult:
    base_url = settings.GLM_API_BASE_URL.strip().rstrip("/")
    api_key = settings.GLM_API_KEY.strip()
    model_name = settings.GLM_MODEL_NAME.strip() or "gemini-2.5-flash"

    if "generativelanguage.googleapis.com" in base_url and not base_url.endswith("/openai"):
        base_url = f"{base_url}/openai"

    missing = []
    if not base_url:
        missing.append("GLM_API_BASE_URL")
    if not api_key:
        missing.append("GLM_API_KEY")
    if missing:
        raise RuntimeError(f"Missing GLM configuration: {', '.join(missing)}")

    user_content = json.dumps({
        "business_plan_summary": plan_summary,
        "fact_sheet": case.fact_sheet,
        "location": case.location,
        "budget_myr": case.budget_myr,
    })

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": AUDITOR_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.2,
                "max_tokens": 5000,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API Error: {resp.text}")
        resp.raise_for_status()

    raw_data = resp.json()
    content = raw_data["choices"][0]["message"].get("content")

    if content is None:
        raise ValueError(f"GLM returned null content. Full response: {raw_data}")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    data = json.loads(content.strip())
    return AuditResult(**data)
