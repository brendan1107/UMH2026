# ZAI API wrapper
# app/ai/glm_client.py
import os, json
import httpx
from dotenv import load_dotenv
load_dotenv()
from app.ai.schemas import AgentOutput

ZAI_BASE = os.getenv("GLM_API_BASE_URL")
ZAI_KEY  = os.getenv("GLM_API_KEY")

async def glm_call(
    messages: list[dict],
    system: str,
) -> AgentOutput:
    payload = {
        "model": os.getenv("GLM_MODEL_NAME", "ilmu-glm-5.1"),
        "messages": [
            {"role": "system", "content": system},
            *messages,
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }

    async with httpx.AsyncClient(timeout=60, http2=False) as client:
        resp = await client.post(
            f"{ZAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {ZAI_KEY}"},
            json=payload,
        )
        resp.raise_for_status()
        raw = resp.json()

    content = raw["choices"][0]["message"]["content"]

    if content is None:
        raise ValueError(f"GLM returned null content. Full response: {raw}")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    data = json.loads(content)

    # GLM sometimes wraps response in a list — unwrap it
    if isinstance(data, list):
        data = data[0]

    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Unexpected GLM response shape: {data}")

    type_map = {
        "tool_call":  "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify":    "ClarifyOutput",
        "verdict":    "VerdictOutput",
    }
    from app.ai import schemas
    model_cls = getattr(schemas, type_map[data["type"]])
    return model_cls(**data)