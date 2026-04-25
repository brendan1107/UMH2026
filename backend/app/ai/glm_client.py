# app/ai/glm_client.py
# Merged: supports both Gemini native API and ZAI GLM (OpenAI-compatible)
# Includes: retry logic, Google Search grounding, task_batch + field_task, dual-mode detection
 
import json
import logging
import asyncio
 
import httpx
 
from app.ai.schemas import AgentOutput
from app.config import settings
 
logger = logging.getLogger(__name__)
 
 
# ── Fallback output when AI auth fails in development ────────────────────────
 
def _development_fallback_output() -> AgentOutput:
    """Return a usable fallback when the AI key is unavailable in development."""
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
 
 
# ── Config loader ─────────────────────────────────────────────────────────────
 
def _get_glm_config() -> tuple[str, str, str, int]:
    """Read and validate GLM config from settings."""
    base_url   = settings.GLM_API_BASE_URL.strip().rstrip("/")
    api_key    = settings.GLM_API_KEY.strip()
    model      = settings.GLM_MODEL_NAME.strip() or "ilmu-glm-5.1"
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
 
 
# ── Endpoint detection ────────────────────────────────────────────────────────
 
def _is_google_gemini_endpoint(base_url: str) -> bool:
    """Return True when the configured URL points to Google's Gemini API."""
    return "generativelanguage.googleapis.com" in base_url.lower()
 
 
def _gemini_generate_content_url(base_url: str, model: str) -> str:
    """Build the native Gemini generateContent URL from the configured base URL."""
    api_base = base_url.rstrip("/")
    # Strip /openai suffix if present (some configs point to OpenAI-compat endpoint)
    if api_base.endswith("/openai"):
        api_base = api_base[: -len("/openai")]
    # Strip /models if accidentally included
    if "/models" in api_base:
        api_base = api_base.split("/models", 1)[0]
    # Ensure versioned path
    if "generativelanguage.googleapis.com" in api_base and "/v1" not in api_base:
        api_base = f"{api_base}/v1beta"
 
    model_name = model.removeprefix("models/")
    return f"{api_base}/models/{model_name}:generateContent"
 
 
# ── Gemini response extraction ────────────────────────────────────────────────
 
def _extract_gemini_text(raw: dict) -> str | None:
    """Extract and join all text parts from a Gemini generateContent response."""
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
 
 
# ── JSON content cleaner ──────────────────────────────────────────────────────
 
def _clean_json_content(content: str) -> str:
    """Strip markdown fences and whitespace from AI output."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()
 
 
# ── Output type dispatcher ────────────────────────────────────────────────────
 
_TYPE_MAP = {
    "tool_call":  "ToolCallOutput",
    "task_batch": "TaskBatchOutput",   # Gemini batch tasks
    "field_task": "FieldTaskOutput",   # ZAI single field task
    "clarify":    "ClarifyOutput",
    "verdict":    "VerdictOutput",
}
 
def _parse_agent_output(content: str) -> AgentOutput:
    """Parse cleaned JSON string into a typed AgentOutput."""
    data = json.loads(content)
 
    if isinstance(data, list):
        data = data[0]
 
    if not isinstance(data, dict) or "type" not in data:
        raise ValueError(f"Unexpected AI response shape: {data}")
 
    from app.ai import schemas
    cls_name = _TYPE_MAP.get(data["type"])
    if not cls_name:
        raise ValueError(f"Unknown output type: {data['type']!r}")
 
    return getattr(schemas, cls_name)(**data)
 
 
# ── Main entry point ──────────────────────────────────────────────────────────
 
async def glm_call(
    messages: list[dict],
    system: str,
    _retry: int = 0,
    max_retries: int = 3,
) -> AgentOutput:
    """
    Call the configured AI endpoint (Gemini or ZAI GLM) and return a typed AgentOutput.
 
    Handles:
    - Dual-mode: Gemini native API vs ZAI GLM (OpenAI-compatible)
    - Google Search grounding (Gemini only)
    - Retry on empty content, prose instead of JSON, 504 gateway errors
    - Development fallback on auth failure
    """
    base_url, api_key, model, max_tokens = _get_glm_config()
 
    # Strip empty messages — APIs reject them
    messages = [m for m in messages if m.get("content", "").strip()]
 
    raw: dict
    content: str | None
 
    # ── Branch: Gemini native API ─────────────────────────────────────────────
    if _is_google_gemini_endpoint(base_url):
        gemini_contents = [
            {
                "role": "model" if msg.get("role") == "assistant" else "user",
                "parts": [{"text": msg["content"]}],
            }
            for msg in messages
        ] or [{
            "role": "user",
            "parts": [{"text": "Begin your investigation. What do you need to find out first?"}]
        }]
 
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": gemini_contents,
            "tools": [{"googleSearch": {}}],   # Google Search grounding
            "generation_config": {
                "temperature": 0.2,
                "max_output_tokens": max_tokens,
                "response_mime_type": "text/plain",
            },
        }
 
        async with httpx.AsyncClient(timeout=90, http2=False) as client:
            try:
                resp = await client.post(
                    _gemini_generate_content_url(base_url, model),
                    headers={"x-goog-api-key": api_key},
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Gemini API failed: status=%s body=%s",
                    exc.response.status_code, exc.response.text[:500],
                )
                if settings.APP_ENV == "development" and exc.response.status_code in {400, 401, 403}:
                    logger.warning("Using development fallback — Gemini auth failed.")
                    return _development_fallback_output()
                raise
            except httpx.HTTPError:
                logger.exception("Gemini request failed before receiving a response.")
                raise
 
            raw = resp.json()
 
        # Log whether Gemini used Google Search this turn
        candidates = raw.get("candidates", [])
        if candidates:
            grounding      = candidates[0].get("groundingMetadata", {})
            search_queries = grounding.get("webSearchQueries", [])
            if search_queries:
                logger.info("Gemini searched Google for: %s", search_queries)
            else:
                logger.debug("Gemini did not use Google Search this turn.")
 
        content = _extract_gemini_text(raw)
 
    # ── Branch: ZAI GLM (OpenAI-compatible) ──────────────────────────────────
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
 
        async with httpx.AsyncClient(timeout=90, http2=False) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
 
                # 504 gateway timeout — retry with backoff
                if resp.status_code == 504:
                    if _retry < max_retries:
                        wait = (_retry + 1) * 5
                        logger.warning("GLM 504 timeout, retrying in %ss (%s/%s)", wait, _retry + 1, max_retries)
                        await asyncio.sleep(wait)
                        return await glm_call(messages=messages, system=system, _retry=_retry + 1, max_retries=max_retries)
                    raise RuntimeError(f"GLM returned 504 after {max_retries} retries.")
 
                resp.raise_for_status()
 
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "GLM API failed: status=%s body=%s",
                    exc.response.status_code, exc.response.text[:500],
                )
                if settings.APP_ENV == "development" and exc.response.status_code == 401:
                    logger.warning("Using development fallback — GLM auth failed.")
                    return _development_fallback_output()
                raise
            except httpx.TimeoutException:
                if _retry < max_retries:
                    wait = (_retry + 1) * 5
                    logger.warning("GLM timeout, retrying in %ss (%s/%s)", wait, _retry + 1, max_retries)
                    await asyncio.sleep(wait)
                    return await glm_call(messages=messages, system=system, _retry=_retry + 1, max_retries=max_retries)
                raise
            except httpx.HTTPError:
                logger.exception("GLM request failed before receiving a response.")
                raise
 
            raw = resp.json()
 
        try:
            message = raw["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected GLM response structure: {raw}") from exc
 
        content = message.get("content")
 
        # finish_reason=length means response was cut off — retry
        finish_reason = raw["choices"][0].get("finish_reason", "")
        if finish_reason == "length":
            if _retry < max_retries:
                logger.warning("GLM response truncated (finish_reason=length), retrying (%s/%s)", _retry + 1, max_retries)
                await asyncio.sleep(2)
                return await glm_call(messages=messages, system=system, _retry=_retry + 1, max_retries=max_retries)
            raise ValueError("GLM response truncated after max retries — increase max_tokens.")
 
        # GLM used native tool_calls instead of JSON content
        if content is None:
            tool_calls = message.get("tool_calls")
            if tool_calls:
                tc       = tool_calls[0]
                fn_name  = tc.get("function", {}).get("name", "fetch_competitors")
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
                logger.info("Extracted tool_call from native tool_calls: %s", fn_name)
            else:
                raise ValueError(f"GLM returned null content with no tool_calls. Message: {message}")
 
    # ── Shared: content cleaning + retry logic ────────────────────────────────
 
    if not content or not content.strip():
        if _retry < max_retries:
            logger.warning("AI returned empty content, retrying (%s/%s)", _retry + 1, max_retries)
            messages.append({
                "role": "assistant",
                "content": "[No output. Output your JSON decision now.]"
            })
            await asyncio.sleep(2)
            return await glm_call(messages=messages, system=system, _retry=_retry + 1, max_retries=max_retries)
        raise ValueError(f"AI returned empty content after {max_retries} retries. Response: {raw}")
 
    content = _clean_json_content(content)
 
    if not content:
        raise ValueError("AI returned empty content after stripping markdown fences.")
 
    # Content is prose instead of JSON — nudge and retry
    if not content.startswith("{") and not content.startswith("["):
        if _retry < max_retries:
            logger.warning(
                "AI returned prose instead of JSON (%s/%s): %s",
                _retry + 1, max_retries, content[:100]
            )
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": (
                    "You returned prose instead of JSON. "
                    "You MUST output only a valid JSON object. "
                    "No explanation, no markdown. Start your response with the { character."
                )
            })
            await asyncio.sleep(1)
            return await glm_call(messages=messages, system=system, _retry=_retry + 1, max_retries=max_retries)
        raise ValueError(f"AI returned prose after {max_retries} retries: {content[:200]}")
 
    # Parse and return typed output
    try:
        return _parse_agent_output(content)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        if _retry < max_retries:
            logger.warning("JSON parse failed (%s/%s): %s — %s", _retry + 1, max_retries, exc, content[:100])
            await asyncio.sleep(1)
            return await glm_call(messages=messages, system=system, _retry=_retry + 1, max_retries=max_retries)
        raise ValueError(f"JSON parse failed after {max_retries} retries: {exc} | content: {repr(content[:200])}")