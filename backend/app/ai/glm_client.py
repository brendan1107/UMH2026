# app/ai/glm_client.py
import json
import logging
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
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected Gemini response shape: {raw}") from e


def _convert_messages_to_gemini(
    system: str, messages: list[dict]
) -> tuple[str, list[dict]]:
    """
    Convert OpenAI-style messages to Gemini native format.
    Gemini uses 'contents' with 'role: user/model' and 'parts'.
    System prompt goes into system_instruction separately.
    """
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Gemini uses 'model' instead of 'assistant'
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({
            "role": gemini_role,
            "parts": [{"text": content}]
        })
    return system, contents


async def glm_call(
    messages: list[dict],
    system: str,
    _retry: int = 0,
) -> AgentOutput:
    base_url, api_key, model = _get_glm_config()

    # Filter out empty messages — API rejects them
    messages = [m for m in messages if m.get("content", "").strip()]

    # Convert to Gemini native format
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
            # Google Search grounding — Gemini searches automatically
            # when it needs real-world data like rental prices,
            # competitor counts, footfall, market rates etc.
            {"google_search": {}}
        ],
        "generation_config": {
            "temperature": 0.2,
            "max_output_tokens": int(settings.GLM_MAX_TOKENS),
            "response_mime_type": "text/plain",  # we parse JSON ourselves
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
            logger.error(
                "Gemini API request failed: status=%s body=%s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            if settings.APP_ENV == "development" and exc.response.status_code == 401:
                logger.warning("Using development fallback — Gemini auth failed.")
                return _development_fallback_output()
            raise
        except httpx.HTTPError:
            logger.exception("Gemini API request failed before receiving a response.")
            raise

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

    # If content is empty — Gemini may still be processing after search
    if not content or not content.strip():
        if _retry < 2:
            logger.warning(
                "Gemini returned empty content — retrying (%s/2)", _retry + 1
            )
            messages.append({
                "role": "assistant",
                "content": "[Search completed. Now output your JSON decision based on the search results.]"
            })
            return await glm_call(messages=messages, system=system, _retry=_retry + 1)
        raise ValueError(f"Gemini returned empty content after {_retry} retries. Full response: {raw}")

    content = content.strip()

    # Strip markdown fences if Gemini wraps in ```json
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    # If still empty after stripping fences
    if not content:
        if _retry < 2:
            logger.warning(
                "Gemini returned empty JSON after fence strip — retrying (%s/2)", _retry + 1
            )
            messages.append({
                "role": "assistant",
                "content": "[Search completed. Now output your JSON decision based on the search results.]"
            })
            return await glm_call(messages=messages, system=system, _retry=_retry + 1)
        raise ValueError("Gemini returned empty JSON after fence strip.")

    # If content doesn't start with { or [ — Gemini returned prose instead of JSON
    # Nudge it to output JSON and retry
    if not content.startswith("{") and not content.startswith("["):
        if _retry < 2:
            logger.warning(
                "Gemini returned prose instead of JSON — retrying (%s/2): %s",
                _retry + 1, content[:100]
            )
            messages.append({
                "role": "assistant",
                "content": content  # include Gemini's prose so it has context
            })
            messages.append({
                "role": "user",
                "content": (
                    "You returned prose instead of JSON. "
                    "You MUST output only a valid JSON object matching one of the required types. "
                    "No explanation, no markdown, just raw JSON starting with {."
                )
            })
            return await glm_call(messages=messages, system=system, _retry=_retry + 1)
        raise ValueError(f"Gemini returned prose after {_retry} retries: {content[:200]}")

    data = json.loads(content)

    # Gemini sometimes wraps response in a list — unwrap it
    if isinstance(data, list):
        data = data[0]

    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Unexpected agent response shape: {data}")

    type_map = {
        "tool_call":  "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify":    "ClarifyOutput",
        "verdict":    "VerdictOutput",
    }
    from app.ai import schemas
    model_cls = getattr(schemas, type_map[data["type"]])
    return model_cls(**data)