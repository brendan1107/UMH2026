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


def _get_glm_config() -> tuple[str, str, str]:
    """Read GLM config from the backend settings loader, including .env.backend."""
    base_url = settings.GLM_API_BASE_URL.strip().rstrip("/")
    api_key = settings.GLM_API_KEY.strip()
    model = settings.GLM_MODEL_NAME.strip() or "ilmu-glm-5.1"

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
) -> AgentOutput:
    base_url, api_key, model = _get_glm_config()
    
    # Check if we are actually using Gemini. If so, use the native API to support search.
    is_gemini = "gemini" in model.lower() or "generativelanguage" in base_url
    
    if is_gemini:
        # Use native Gemini API
        gemini_messages = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_messages.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2000,
            },
            "tools": [{"googleSearch": {}}]
        }
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        async with httpx.AsyncClient(timeout=60, http2=False) as client:
            try:
                resp = await client.post(api_url, json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Gemini API request failed: status=%s body=%s",
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                if settings.APP_ENV == "development" and exc.response.status_code == 400:
                    logger.warning("Using development fallback AI output due to API error.")
                    return _development_fallback_output()
                raise
                
            raw = resp.json()
            try:
                content = raw["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                raise ValueError(f"Unexpected Gemini response structure: {raw}")
    else:
        # Fallback to OpenAI compatibility layer for other models (e.g. Zhipu GLM)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            "temperature": 0.2,
            "max_tokens": 2000,
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
                    logger.warning("Using development fallback AI output because GLM auth failed.")
                    return _development_fallback_output()
                raise
    
            raw = resp.json()
            content = raw["choices"][0]["message"]["content"]

    if content is None:
        raise ValueError(f"AI returned null content. Full response: {raw}")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    data = json.loads(content)

    if isinstance(data, list):
        data = data[0]

    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Unexpected AI response shape: {data}")

    type_map = {
        "tool_call":  "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify":    "ClarifyOutput",
        "verdict":    "VerdictOutput",
    }
    from app.ai import schemas
    model_cls = getattr(schemas, type_map[data["type"]])
    return model_cls(**data)
