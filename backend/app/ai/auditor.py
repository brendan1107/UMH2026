import json
import os

import httpx

from app.ai.prompts import AUDITOR_PROMPT
from app.ai.schemas import AuditResult, BusinessCase

ZAI_BASE = "https://api.ilmu.ai/v1"
ZAI_KEY = os.getenv("ZAI_API_KEY")


async def run_audit(case: BusinessCase, plan_summary: str) -> AuditResult:
    user_content = json.dumps({
        "business_plan_summary": plan_summary,
        "fact_sheet": case.fact_sheet,
        "verdict": case.phase,
        "location": case.location,
        "budget_myr": case.budget_myr,
    })

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{ZAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {ZAI_KEY}"},
            json={
                "model": "ilmu-glm-5.1",
                "messages": [
                    {"role": "system", "content": AUDITOR_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.2,
                "max_tokens": 1000,
            },
        )
        resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    data = json.loads(content.strip())
    return AuditResult(**data)
