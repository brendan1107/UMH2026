# app/ai/glm_client.py
# Merged: supports both Gemini native API and ZAI GLM (OpenAI-compatible)
# Includes: retry logic, Google Search grounding, task_batch + field_task, dual-mode detection
 
import json
import logging
import asyncio
import re
from typing import Any, Optional
 
import httpx
 
from app.ai.schemas import AgentOutput
from app.config import settings
 
logger = logging.getLogger(__name__)
 
 
# ── Fallback output when AI auth fails in development ────────────────────────
 
def _development_fallback_output(case: Optional["BusinessCase"] = None) -> AgentOutput:
    """Return a context-aware fallback when the AI key is unavailable."""
    from app.ai.schemas import TaskBatchOutput, TaskDef
    
    idea = case.idea if case else "your business"
    location = case.location if case else "your target area"
    
    msg = (
        f"I'm currently unable to reach my high-level reasoning service, but let's keep moving. "
        f"To assess '{idea}' in {location}, I need a few more details."
    )
    
    return TaskBatchOutput(
        type="task_batch",
        chat_message=msg,
        tasks=[
            TaskDef(
                title="Confirm target area and rent",
                instruction=f"Provide the exact street or neighborhood in {location} and the expected monthly rent.",
                evidence_type="text",
                ai_message="Detailed location and rent are critical for our first-pass feasibility check.",
                follow_up_action="Analyze Audience"
            )
        ]
    )
 
 
# ── Config loader ─────────────────────────────────────────────────────────────
 
def _get_glm_config() -> tuple[str, str, str, int]:
    """Read and validate GLM config from settings."""
    base_url   = settings.GLM_API_BASE_URL.strip().rstrip("/")
    api_key    = settings.GLM_API_KEY.strip()
    model      = settings.GLM_MODEL_NAME.strip() or "gemini-2.5-flash"
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
    """Return True when the configured URL points to Google's Gemini NATIVE API."""
    # If the URL explicitly includes /openai/, we treat it as an OpenAI-compatible endpoint
    # to avoid double-appending or incorrect path transformations.
    url_lower = base_url.lower()
    return "generativelanguage.googleapis.com" in url_lower and "/openai" not in url_lower
 
 
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
        match = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
    return content.strip()


def _extract_json_candidate(content: str) -> str | None:
    """Find a structured JSON object/array embedded in useful prose."""
    stripped = content.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped

    object_match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if object_match:
        return object_match.group(0).strip()

    array_match = re.search(r"\[.*\]", stripped, flags=re.DOTALL)
    if array_match:
        return array_match.group(0).strip()

    return None


def _normalize_agent_data(data: Any) -> dict:
    """Accept small schema variants from Gemini/OpenAI-compatible responses."""
    if isinstance(data, list):
        data = data[0] if data else {}

    if not isinstance(data, dict):
        raise ValueError(f"Unexpected AI response shape: {data}")

    if "task_batch" in data and "tasks" not in data:
        data["tasks"] = data.get("task_batch")
    if "field_task" in data and isinstance(data.get("field_task"), dict):
        data = {"type": "field_task", **data["field_task"]}
    if "type" not in data:
        if "tasks" in data:
            data["type"] = "task_batch"
        elif "decision" in data or "verdict" in data:
            data["type"] = "verdict"
        elif "tool" in data or "tool_name" in data:
            data["type"] = "tool_call"
        elif "content" in data or "message" in data or "text" in data:
            data = {
                "type": "text",
                "content": data.get("content") or data.get("message") or data.get("text") or "",
            }
        else:
            raise ValueError(f"Unexpected AI response shape: {data}")

    data["type"] = str(data["type"]).strip().lower().replace("-", "_").replace(" ", "_")
    if data["type"] in {"task", "tasks"}:
        data["type"] = "task_batch" if data.get("tasks") else "field_task"
    if data["type"] in {"recommendation", "final_verdict"}:
        data["type"] = "verdict"

    if data["type"] == "task_batch":
        data.setdefault("tasks", [])
        normalized_tasks = []
        for task in data.get("tasks") or []:
            if isinstance(task, dict):
                task.setdefault("instruction", task.get("description") or task.get("aiMessage") or task.get("title") or "Provide this information.")
                task.setdefault("evidence_type", task.get("evidenceType") or "text")
            normalized_tasks.append(task)
        data["tasks"] = normalized_tasks
        data["chat_message"] = data.get("chat_message") or data.get("chatMessage") or data.get("aiMessage") or data.get("message")
    if data["type"] == "field_task":
        data.setdefault("instruction", data.get("description") or data.get("title") or "Provide this information.")
        data.setdefault("evidence_type", data.get("evidenceType") or "text")
    if data["type"] == "clarify":
        data["question"] = str(
            data.get("question")
            or data.get("message")
            or data.get("content")
            or "Please clarify the missing detail."
        )
        options = data.get("options")
        data["options"] = options if isinstance(options, list) and options else ["Answer question", "Add evidence"]
    if data["type"] == "verdict":
        decision = str(data.get("decision") or data.get("verdict") or "PIVOT").upper()
        data["decision"] = decision if decision in {"GO", "PIVOT", "STOP"} else "PIVOT"
        try:
            data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.55))))
        except (TypeError, ValueError):
            data["confidence"] = 0.55
        data["summary"] = str(
            data.get("summary")
            or data.get("reasoning")
            or "Verdict generated from the current investigation evidence."
        )
        data["pivot_suggestion"] = data.get("pivot_suggestion") or data.get("pivotSuggestion") or data.get("next_step")
        if not isinstance(data.get("strengths"), list):
            data["strengths"] = []
    if data["type"] == "tool_call":
        data["tool"] = data.get("tool") or data.get("tool_name") or "fetch_competitors"
        if data["tool"] not in {"fetch_competitors", "estimate_footfall", "calculate_breakeven"}:
            data["tool"] = "fetch_competitors"
        if not isinstance(data.get("args"), dict):
            data["args"] = {}
    if data["type"] == "text":
        data["content"] = data.get("content") or data.get("message") or data.get("text") or ""

    return data
 
 
# ── Output type dispatcher ────────────────────────────────────────────────────
 
_TYPE_MAP = {
    "tool_call":  "ToolCallOutput",
    "task_batch": "TaskBatchOutput",   # Gemini batch tasks
    "field_task": "FieldTaskOutput",   # ZAI single field task
    "clarify":    "ClarifyOutput",
    "verdict":    "VerdictOutput",
    "text":       "TextOutput",
}
 
def _parse_agent_output(content: str) -> AgentOutput:
    """Parse cleaned JSON string into a typed AgentOutput."""
    data = _normalize_agent_data(json.loads(content))
 
    from app.ai import schemas
    cls_name = _TYPE_MAP.get(data["type"])
    if not cls_name:
        raise ValueError(f"Unknown output type: {data['type']!r}")
 
    return getattr(schemas, cls_name)(**data)


def _content_to_agent_output(content: str) -> AgentOutput:
    """Return structured output when possible, otherwise preserve useful text."""
    from app.ai.schemas import TextOutput

    cleaned = _clean_json_content(content)
    if not cleaned:
        raise ValueError("AI returned empty content after stripping markdown fences.")

    json_candidate = _extract_json_candidate(cleaned)
    if json_candidate:
        try:
            parsed = _parse_agent_output(json_candidate)
            if parsed.type == "task_batch" and not getattr(parsed, "chat_message", None):
                prose = cleaned.replace(json_candidate, "").strip()
                if prose:
                    parsed.chat_message = prose
            return parsed
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.info("AI structured parse failed, preserving useful text: %s", exc)

    return TextOutput(type="text", content=cleaned)


async def glm_json_call(
    messages: list[dict],
    system: str,
    max_tokens: int = 1200,
    timeout: float = 20,
    max_retries: int = 1,
) -> dict:
    """Call the AI endpoint and return a JSON-like dict for legacy fact analysis."""
    output = await glm_call(
        messages=messages,
        system=system,
        timeout=timeout,
        max_tokens=max_tokens,
        max_retries=max_retries,
    )
    return output.model_dump(by_alias=True)
 
 
# ── Main entry point ──────────────────────────────────────────────────────────
 
async def glm_call(
    messages: list[dict],
    system: str,
    case: Optional["BusinessCase"] = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
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
    base_url, api_key, model, configured_max_tokens = _get_glm_config()
    request_timeout = timeout or 90
    output_tokens = max_tokens or configured_max_tokens
 
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
                "max_output_tokens": output_tokens,
                "response_mime_type": "text/plain",
            },
        }
 
        async with httpx.AsyncClient(timeout=request_timeout, http2=False) as client:
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
                if False:
                    logger.warning(f"Using development fallback — Gemini API error {exc.response.status_code}")
                    return _development_fallback_output(case)
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
            "max_tokens": output_tokens,
        }
 
        async with httpx.AsyncClient(timeout=request_timeout, http2=False) as client:
            try:
                target_url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
                logger.info(f"AI Request: POST {target_url} (model={model})")
                resp = await client.post(
                    target_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                )
 
                # 504 gateway timeout — retry with backoff
                if resp.status_code == 504:
                    if _retry < max_retries:
                        wait = (_retry + 1) * 5
                        logger.warning("GLM 504 timeout, retrying in %ss (%s/%s)", wait, _retry + 1, max_retries)
                        await asyncio.sleep(wait)
                        return await glm_call(messages=messages, system=system, case=case, timeout=request_timeout, max_tokens=output_tokens, _retry=_retry + 1, max_retries=max_retries)
                    raise RuntimeError(f"GLM returned 504 after {max_retries} retries.")
 
                resp.raise_for_status()
 
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "GLM API failed: status=%s body=%s",
                    exc.response.status_code, exc.response.text[:500],
                )
                if False:
                    logger.warning(f"Using development fallback — GLM auth failed: {exc.response.status_code}")
                    return _development_fallback_output(case)
                raise
            except httpx.TimeoutException:
                if _retry < max_retries:
                    wait = (_retry + 1) * 5
                    logger.warning("GLM timeout, retrying in %ss (%s/%s)", wait, _retry + 1, max_retries)
                    await asyncio.sleep(wait)
                    return await glm_call(messages=messages, system=system, case=case, timeout=request_timeout, max_tokens=output_tokens, _retry=_retry + 1, max_retries=max_retries)
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
                return await glm_call(messages=messages, system=system, case=case, timeout=request_timeout, max_tokens=output_tokens, _retry=_retry + 1, max_retries=max_retries)
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
            return await glm_call(messages=messages, system=system, case=case, timeout=request_timeout, max_tokens=output_tokens, _retry=_retry + 1, max_retries=max_retries)
        raise ValueError(f"AI returned empty content after {max_retries} retries. Response: {raw}")

    return _content_to_agent_output(content)
