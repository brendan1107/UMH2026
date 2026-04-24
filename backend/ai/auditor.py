# # pass 2 critic

# # ai/auditor.py
# import json
# from ai.glm_client import glm_call
# from ai.prompts import AUDITOR_PROMPT
# from ai.schemas import AuditResult, BusinessCase

# async def run_audit(case: BusinessCase, plan_summary: str) -> AuditResult:
#     """
#     Completely separate GLM call with a different system prompt.
#     The auditor sees the plan + fact sheet and finds 3 failure risks.
#     Call this AFTER the main agent issues its verdict.
#     """

#     user_message = {
#         "role": "user",
#         "content": json.dumps({
#             "business_plan_summary": plan_summary,
#             "fact_sheet": case.fact_sheet,
#             "verdict": case.phase,
#             "location": case.location,
#             "budget_myr": case.budget_myr,
#         })
#     }

#     raw_output = await glm_call(
#         messages=[user_message],
#         system=AUDITOR_PROMPT,
#     )

#     # The auditor returns a different schema — parse manually
#     # because AuditResult is not an AgentOutput type
#     if hasattr(raw_output, '__dict__'):
#         data = raw_output.__dict__
#     else:
#         data = json.loads(raw_output.model_dump_json())

#     return AuditResult(**data)

# ai/auditor.py
import json, httpx, os
from ai.schemas import AuditResult, BusinessCase

ZAI_BASE = "https://open.bigmodel.cn/api/paas/v4"
ZAI_KEY  = os.getenv("ZAI_API_KEY")

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
                    {"role": "user",   "content": user_content},
                ],
                "temperature": 0.2,
                "max_tokens": 1000,
            }
        )
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    data = json.loads(content.strip())
    return AuditResult(**data)
