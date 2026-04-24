# ZAI API wrapper

# ai/glm_client.py
import os, json
import httpx
from ai.schemas import AgentOutput

ZAI_BASE = "https://api.ilmu.ai/v1"  # ZAI endpoint
ZAI_KEY  = os.getenv("ZAI_API_KEY")

async def glm_call(
    messages: list[dict],
    system: str,
) -> AgentOutput:
    """
    Call ZAI GLM-5.1 and return a validated AgentOutput.
    Retries once if the response fails Pydantic validation.
    """
    payload = {
        "model": "ilmu-glm-5.1",          # use whatever GLM model ZAI provides
        "messages": [
            {"role": "system", "content": system},
            *messages,
        ],
        "temperature": 0.2,        # low temp = more consistent JSON
        "max_tokens": 1000,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{ZAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {ZAI_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        raw = resp.json()

    content = raw["choices"][0]["message"]["content"]

    # Strip markdown fences if GLM wraps in ```json
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    data = json.loads(content)

    # Validate against our union schema
    # Try each type based on the "type" field
    type_map = {
        "tool_call":  "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify":    "ClarifyOutput",
        "verdict":    "VerdictOutput",
    }
    from ai import schemas
    model_cls = getattr(schemas, type_map[data["type"]])
    return model_cls(**data)