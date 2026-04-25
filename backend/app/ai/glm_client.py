# ZAI API wrapper
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


def _get_glm_config() -> tuple[str, str, str, int]:
    """Read GLM config from the backend settings loader, including .env.backend."""
    base_url = settings.GLM_API_BASE_URL.strip().rstrip("/")
    api_key = settings.GLM_API_KEY.strip()
    model = settings.GLM_MODEL_NAME.strip() or "ilmu-glm-5.1"
    max_tokens = settings.GLM_MAX_TOKENS

    missing = []
    if not base_url:
        missing.append("GLM_API_BASE_URL")
    if not api_key:
        missing.append("GLM_API_KEY")

    if missing:
        raise RuntimeError(f"Missing GLM configuration: {', '.join(missing)}")
    if max_tokens <= 0:
        raise RuntimeError("GLM_MAX_TOKENS must be greater than 0")

    return base_url, api_key, model, max_tokens


def _is_google_gemini_endpoint(base_url: str) -> bool:
    """Return true when the configured OpenAI-compatible URL is Google's Gemini API."""
    return "generativelanguage.googleapis.com" in base_url.lower()


def _gemini_generate_content_url(base_url: str, model: str) -> str:
    """Build the native Gemini URL from the configured GLM base URL."""
    api_base = base_url.rstrip("/")
    if api_base.endswith("/openai"):
        api_base = api_base[: -len("/openai")]
    if "/models" in api_base:
        api_base = api_base.split("/models", 1)[0]
    if "generativelanguage.googleapis.com" in api_base and "/v1" not in api_base:
        api_base = f"{api_base}/v1beta"

    model_name = model.removeprefix("models/")
    return f"{api_base}/models/{model_name}:generateContent"


def _extract_gemini_text(raw: dict) -> str | None:
    """Extract all text parts from a Gemini generateContent response."""
    try:
        parts = raw["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return None

    text_parts = [
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    return "\n".join(text_parts) if text_parts else None


async def glm_call(
    messages: list[dict],
    system: str,
) -> AgentOutput:
    base_url, api_key, model, max_tokens = _get_glm_config()

    # Filter out empty messages because chat APIs reject them.
    messages = [m for m in messages if m.get("content", "").strip()]

    raw: dict
    content: str | None

    if _is_google_gemini_endpoint(base_url):
        gemini_messages = [
            {
                "role": "model" if msg.get("role") == "assistant" else "user",
                "parts": [{"text": msg["content"]}],
            }
            for msg in messages
        ]

        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_tokens,
            },
            "tools": [{"googleSearch": {}}],
        }

        async with httpx.AsyncClient(timeout=60, http2=False) as client:
            try:
                resp = await client.post(
                    _gemini_generate_content_url(base_url, model),
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
                if (
                    settings.APP_ENV == "development"
                    and exc.response.status_code in {400, 401, 403}
                ):
                    logger.warning(
                        "Using development fallback AI output because Gemini request failed."
                    )
                    return _development_fallback_output()
                raise
            except httpx.HTTPError:
                logger.exception("Gemini API request failed before receiving a response.")
                raise

            raw = resp.json()

        content = _extract_gemini_text(raw)
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60, http2=False) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "GLM API request failed: status=%s body=%s",
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                if settings.APP_ENV == "development" and exc.response.status_code == 401:
                    logger.warning(
                        "Using development fallback AI output because GLM authentication failed."
                    )
                    return _development_fallback_output()
                raise
            except httpx.HTTPError:
                logger.exception("GLM API request failed before receiving a response.")
                raise

            raw = resp.json()

        try:
            message = raw["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected GLM response structure: {raw}") from exc

        content = message.get("content")

    if not content or not content.strip():
        raise ValueError(f"AI returned empty content. Full response: {raw}")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    data = json.loads(content)

    # GLM sometimes wraps response in a list; unwrap it.
    if isinstance(data, list):
        data = data[0]

    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Unexpected AI response shape: {data}")

    type_map = {
        "tool_call": "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify": "ClarifyOutput",
        "verdict": "VerdictOutput",
    }
    from app.ai import schemas

    model_cls = getattr(schemas, type_map[data["type"]])
    return model_cls(**data)
