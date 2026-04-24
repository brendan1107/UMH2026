# test_agent_output.py
# Run with: python test_agent_output.py
import httpx, os, json
from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv()

ZAI_KEY  = os.getenv("ZAI_API_KEY")
ZAI_BASE = "https://open.bigmodel.cn/api/paas/v4"



# ── Paste your actual schemas here for standalone testing ──
from typing import Literal, Any
from pydantic import BaseModel

class ToolCallOutput(BaseModel):
    type: Literal["tool_call"]
    tool: str
    args: dict[str, Any]

class FieldTaskOutput(BaseModel):
    type: Literal["field_task"]
    title: str
    instruction: str
    evidence_type: Literal["count", "photo", "rating", "text"]

class ClarifyOutput(BaseModel):
    type: Literal["clarify"]
    question: str
    options: list[str]

class VerdictOutput(BaseModel):
    type: Literal["verdict"]
    decision: Literal["GO", "PIVOT", "STOP"]
    confidence: float
    summary: str

TYPE_MAP = {
    "tool_call":  ToolCallOutput,
    "field_task": FieldTaskOutput,
    "clarify":    ClarifyOutput,
    "verdict":    VerdictOutput,
}

# ── Helper ─────────────────────────────────────────────────
def call_glm(system: str, user: str) -> str:
    resp = httpx.post(
        f"{ZAI_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {ZAI_KEY}"},
        json={
            "model": "ilmu-glm-5.1",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        },
        timeout=30,
    )
    content = resp.json()["choices"][0]["message"]["content"].strip()
    # Strip ```json fences if GLM adds them
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()


def parse_and_validate(raw: str):
    data = json.loads(raw)
    model_cls = TYPE_MAP.get(data.get("type"))
    if not model_cls:
        raise ValueError(f"Unknown type: {data.get('type')}")
    return model_cls(**data)


# ── Test cases ─────────────────────────────────────────────
SYSTEM = """You are F&B Genie, a cynical business auditor.
Always output valid JSON only — no preamble, no markdown.
Choose one of these types:
- {"type":"tool_call","tool":"fetch_competitors","args":{"location":"...","category":"..."}}
- {"type":"field_task","title":"...","instruction":"...","evidence_type":"count|photo|rating|text"}
- {"type":"clarify","question":"...","options":["...","..."]}
- {"type":"verdict","decision":"GO|PIVOT|STOP","confidence":0.0-1.0,"summary":"..."}
"""

SCENARIOS = [
    {
        "name": "Should trigger tool_call (no competitor data yet)",
        "user": """Case: RM15 Nasi Lemak cafe in SS15
Budget: RM30,000
Known facts: {}
Missing facts: competitor_count, avg_competitor_rating
What do you do next?""",
        "expect_type": "tool_call",
    },
    {
        "name": "Should trigger field_task (have market data, need footfall)",
        "user": """Case: RM15 Nasi Lemak cafe in SS15
Budget: RM30,000
Known facts: {"competitor_count": 6, "avg_competitor_rating": 4.1}
Missing facts: estimated_footfall_lunch
What do you do next?""",
        "expect_type": "field_task",
    },
    {
        "name": "Should trigger clarify (ambiguous format)",
        "user": """Case: A cafe in Bangsar
Budget: RM50,000
Known facts: {}
The business format (dine-in/takeaway/cloud-kitchen) is unknown.
What do you do next?""",
        "expect_type": "clarify",
    },
    {
        "name": "Should trigger verdict (all facts present)",
        "user": """Case: RM15 Nasi Lemak cafe in SS15
Budget: RM30,000
Known facts: {
  "competitor_count": 6,
  "avg_competitor_rating": 4.1,
  "estimated_footfall_lunch": 90,
  "confirmed_rent_myr": 3200,
  "break_even_covers": 87
}
Missing facts: none — all required facts are collected.
Issue your final verdict now.""",
        "expect_type": "verdict",
    },
]

# ── Run tests ───────────────────────────────────────────────
if __name__ == "__main__":
    passed = 0
    failed = 0

    for s in SCENARIOS:
        print(f"── {s['name']} ──")
        try:
            raw = call_glm(SYSTEM, s["user"])
            print(f"Raw output: {raw[:120]}...")

            result = parse_and_validate(raw)
            actual_type = result.type

            if actual_type == s["expect_type"]:
                print(f"PASS ✓ — got '{actual_type}' as expected\n")
                passed += 1
            else:
                print(f"FAIL ✗ — expected '{s['expect_type']}', got '{actual_type}'\n")
                failed += 1

        except json.JSONDecodeError as e:
            print(f"FAIL ✗ — GLM output is not valid JSON: {e}\n")
            failed += 1
        except ValidationError as e:
            print(f"FAIL ✗ — Pydantic validation error:\n{e}\n")
            failed += 1
        except Exception as e:
            print(f"FAIL ✗ — Unexpected error: {e}\n")
            failed += 1

    print(f"Results: {passed}/{passed+failed} passed")