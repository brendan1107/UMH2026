# app/ai/glm_client.py
import json
import logging
import asyncio
import httpx

from app.ai.schemas import AgentOutput
from app.config import settings

logger = logging.getLogger(__name__)

def _development_fallback_output() -> AgentOutput:
    """Return a usable task when the configured local AI key is unavailable."""
    from app.ai.schemas import FieldTaskOutput

    return FieldTaskOutput(
        type="field_task",
        title="Confirm the target location and rent",
        instruction=(
            "Provide the exact target area or address and the expected monthly rent. "
            "These details are required before the business idea can be assessed."
        ),
        evidence_type="text",
    )

def _get_glm_config() -> tuple[str, str, str]:
    """Read config from settings, but force Gemini 2.5 Flash."""
    base_url = settings.GLM_API_BASE_URL.strip().rstrip("/")
    api_key = settings.GLM_API_KEY.strip()
    
    # ── CHANGE THIS LINE TO 2.5 ──
    model = "gemini-2.5-flash"

    missing = []
    if not base_url:
        missing.append("GLM_API_BASE_URL")
    if not api_key:
        missing.append("GLM_API_KEY")

    if missing:
        raise RuntimeError(f"Missing GLM configuration: {', '.join(missing)}")

    return base_url, api_key, model

async def glm_call(
    messages: list[dict],
    system: str,
    max_retries: int = 3,
) -> AgentOutput:
    base_url, api_key, model = _get_glm_config()

    # ── THE MULTIMODAL FIX ── 
    # Filter out empty messages safely (handling both string text AND image lists)
    valid_messages = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str) and content.strip():
            valid_messages.append(m)
        elif isinstance(content, list) and len(content) > 0:
            valid_messages.append(m)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            *valid_messages,
        ],
        "temperature": 0.2,
        "max_tokens": 2500, # Gives AI enough room to write verdicts
    }

    last_error = None

    async with httpx.AsyncClient(timeout=60, http2=False) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                
                if resp.status_code != 200:
                    last_error = ValueError(f"API Error {resp.status_code}: {resp.text}")
                    if resp.status_code in (429, 503, 504):
                        wait = attempt * 5
                        print(f"  [glm_call] HTTP {resp.status_code}, retrying in {wait}s")
                        await asyncio.sleep(wait)
                        continue
                    raise last_error

                raw = resp.json()
                choice = raw["choices"][0]
                message = choice.get("message", {})
                content = message.get("content")
                finish = choice.get("finish_reason", "")

                # If truncated due to token limit
                if finish == "length":
                    print(f"  [glm_call] WARNING: response truncated. Retrying {attempt}/{max_retries}")
                    await asyncio.sleep(2)
                    last_error = ValueError("GLM response truncated")
                    continue

                # Handle native tool_calls instead of JSON content
                if content is None:
                    tool_calls = message.get("tool_calls")
                    if tool_calls:
                        tc = tool_calls[0]
                        fn_name = tc.get("function", {}).get("name", "fetch_competitors")
                        args_raw = tc.get("function", {}).get("arguments", "{}")
                        try:
                            args_dict = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                        except Exception:
                            args_dict = {}
                        content = json.dumps({
                            "type": "tool_call",
                            "tool": fn_name,
                            "args": args_dict,
                        })
                    else:
                        print(f"  [glm_call] content is None, no tool_calls. Message: {message}")
                        last_error = ValueError(f"GLM returned null content.")
                        await asyncio.sleep(2)
                        continue

                # Clean markdown fences
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()

                # Parse JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"  [glm_call] JSON parse error: {e} | content: {repr(content[:100])}")
                    last_error = ValueError(f"Invalid JSON from GLM: {e}")
                    await asyncio.sleep(2)
                    continue

                if isinstance(data, list):
                    data = data[0]

                if not isinstance(data, dict) or "type" not in data:
                    last_error = ValueError(f"Unexpected shape: {data}")
                    await asyncio.sleep(2)
                    continue

                type_map = {
                    "tool_call":  "ToolCallOutput",
                    "field_task": "FieldTaskOutput",
                    "clarify":    "ClarifyOutput",
                    "verdict":    "VerdictOutput",
                }
                
                from app.ai import schemas
                cls_name = type_map.get(data["type"])
                if not cls_name:
                    last_error = ValueError(f"Unknown type: {data['type']}")
                    await asyncio.sleep(2)
                    continue

                return getattr(schemas, cls_name)(**data)

            except httpx.TimeoutException:
                wait = attempt * 5
                print(f"  [glm_call] Timeout on attempt {attempt}/{max_retries}, retrying in {wait}s")
                await asyncio.sleep(wait)
                last_error = Exception("GLM timeout after 60s")
                continue

    raise RuntimeError(
        f"GLM failed after {max_retries} attempts. Last error: {last_error}"
    )