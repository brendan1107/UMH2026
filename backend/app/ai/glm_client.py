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
    """
    Read GLM config from settings.
    Strips the /openai suffix so the native Gemini endpoint is used,
    which supports Google Search grounding.
    """
    base_url = settings.GLM_API_BASE_URL.strip().rstrip("/").replace("/openai", "")
    api_key = settings.GLM_API_KEY.strip()
    model = settings.GLM_MODEL_NAME.strip() or "gemini-2.5-flash"

    if not api_key:
        raise RuntimeError("Missing GLM configuration: GLM_API_KEY")

    return base_url, api_key, model


def _extract_text_from_gemini(raw: dict) -> str:
    """
    Extract text content from native Gemini API response.
    Gemini may return multiple parts — join them all.
    """
    try:
        parts = raw["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p)
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Gemini response shape: {raw}") from e


def _convert_messages_to_gemini(system: str, messages: list[dict]) -> tuple[str, list[dict]]:
    """
    Convert OpenAI-style messages (including Multimodal Data URIs) 
    to Gemini native format.
    """
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Gemini uses 'model' instead of 'assistant'
        gemini_role = "model" if role == "assistant" else "user"
        
        parts = []
        if isinstance(content, str) and content.strip():
            parts.append({"text": content})
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    parts.append({"text": item["text"]})
                elif item.get("type") == "image_url":
                    # Convert Base64 Data URI to Native Gemini Inline Data
                    url = item["image_url"]["url"]
                    if url.startswith("data:"):
                        mime_type = url.split(";")[0].replace("data:", "")
                        b64_data = url.split(",")[1]
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data
                            }
                        })
        if parts:
            contents.append({
                "role": gemini_role,
                "parts": parts
            })
            
    return system, contents


async def glm_call(
    messages: list[dict],
    system: str,
    max_retries: int = 3,
    _retry: int = 0,
) -> AgentOutput:
    
    base_url, api_key, model = _get_glm_config()

    # Convert to Gemini native format and translate images
    system_instruction, contents = _convert_messages_to_gemini(system, messages)

    # If no contents, add a starter message
    if not contents:
        contents = [{
            "role": "user",
            "parts": [{"text": "Begin your investigation. What do you need to find out first?"}]
        }]

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "tools": [
            # Google Search grounding
            {"google_search": {}}
        ],
        "generation_config": {
            "temperature": 0.2,
            "max_output_tokens": 2500,
            "response_mime_type": "text/plain", 
        },
    }

    async with httpx.AsyncClient(timeout=60, http2=False) as client:
        try:
            resp = await client.post(
                f"{base_url}/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key},
                json=payload,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Handle rate limits and server errors with recursion
            if exc.response.status_code in (429, 503, 504) and _retry < max_retries:
                wait = (_retry + 1) * 5
                logger.warning(f"HTTP {exc.response.status_code}, retrying in {wait}s...")
                await asyncio.sleep(wait)
                return await glm_call(messages, system, max_retries, _retry + 1)
                
            if settings.APP_ENV == "development" and exc.response.status_code == 401:
                return _development_fallback_output()
            raise
        except httpx.TimeoutException:
            if _retry < max_retries:
                wait = (_retry + 1) * 5
                logger.warning(f"Timeout, retrying in {wait}s...")
                await asyncio.sleep(wait)
                return await glm_call(messages, system, max_retries, _retry + 1)
            raise RuntimeError("Gemini timeout after 60s")

        raw = resp.json()

    # Check if Gemini used search grounding
    candidates = raw.get("candidates", [])
    if candidates:
        grounding = candidates[0].get("groundingMetadata", {})
        search_queries = grounding.get("webSearchQueries", [])
        if search_queries:
            print(f"🔍 Gemini searched Google for: {search_queries}")
        else:
            print("ℹ️  Gemini did not use Google Search this turn")

    # Extract text from Gemini native response format
    content = _extract_text_from_gemini(raw)

    # ── LOGICAL RETRIES (Empty content or Prose) ──
    if not content or not content.strip():
        if _retry < max_retries:
            logger.warning("Gemini returned empty content — retrying")
            messages.append({"role": "assistant", "content": "[Search completed. Now output JSON decision.]"})
            return await glm_call(messages, system, max_retries, _retry + 1)
        raise ValueError(f"Gemini returned empty content. Full response: {raw}")

    content = content.strip()

    # Strip markdown fences
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    if not content.startswith("{") and not content.startswith("["):
        if _retry < max_retries:
            logger.warning("Gemini returned prose instead of JSON — retrying")
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "You MUST output only a valid JSON object starting with {."})
            return await glm_call(messages, system, max_retries, _retry + 1)
        raise ValueError(f"Gemini returned prose: {content[:200]}")

    # ── JSON PARSING ──
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        if _retry < max_retries:
            logger.warning("JSON parse error — retrying")
            return await glm_call(messages, system, max_retries, _retry + 1)
        raise ValueError(f"Invalid JSON: {e}")

    if isinstance(data, list):
        data = data[0]

    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Unexpected shape: {data}")

    type_map = {
        "tool_call":  "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify":    "ClarifyOutput",
        "verdict":    "VerdictOutput",
    }
    
    from app.ai import schemas
    cls_name = type_map.get(data["type"])
    if not cls_name:
        raise ValueError(f"Unknown type: {data['type']}")

    return getattr(schemas, cls_name)(**data)