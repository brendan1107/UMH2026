# ZAI/Gemini OpenAI-compatible API wrapper
# app/ai/glm_client.py
import asyncio
import json
import logging
from json import JSONDecodeError
from typing import Any

import httpx

from app.ai.schemas import AgentOutput
from app.config import settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 503, 504}


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
    if "generativelanguage.googleapis.com" in base_url and not base_url.endswith("/openai"):
        base_url = f"{base_url}/openai"

    api_key = settings.GLM_API_KEY.strip()
    model = settings.GLM_MODEL_NAME.strip() or "gemini-2.5-flash"

    missing = []
    if not base_url:
        missing.append("GLM_API_BASE_URL")
    if not api_key:
        missing.append("GLM_API_KEY")

    if missing:
        raise RuntimeError(f"Missing GLM configuration: {', '.join(missing)}")

    return base_url, api_key, model


def _response_error_text(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:500]

    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)[:500]
        return str(data)[:500]
    return str(data)[:500]


def _json_from_content(content: str | None, raw: dict) -> dict:
    if content is None:
        raise ValueError(f"GLM returned null content. Full response: {raw}")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    try:
        data = json.loads(content)
    except JSONDecodeError:
        data = _first_json_value(content)

    if isinstance(data, list):
        data = data[0] if data else {}

    if not isinstance(data, dict):
        raise ValueError(f"Unexpected GLM JSON response shape: {data}")

    return data


def _first_json_value(content: str) -> dict | list:
    """Extract the first JSON object/array when the model adds stray text."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(content):
        if char not in "{[":
            continue
        try:
            data, _ = decoder.raw_decode(content[index:])
            return data
        except JSONDecodeError:
            continue
    raise ValueError(f"Could not parse JSON from GLM content: {content[:500]}")


def _normalize_output_type(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "task": "field_task",
        "fieldtask": "field_task",
        "field_task_output": "field_task",
        "mission": "field_task",
        "question": "clarify",
        "ask": "clarify",
        "clarification": "clarify",
        "tool": "tool_call",
        "toolcall": "tool_call",
        "tool_call_output": "tool_call",
        "recommendation": "verdict",
        "final_verdict": "verdict",
    }
    return aliases.get(normalized, normalized)


def _infer_output_type(data: dict[str, Any]) -> str | None:
    if data.get("type"):
        output_type = _normalize_output_type(data["type"])
        if output_type in {"tool_call", "field_task", "clarify", "verdict"}:
            return output_type
    if data.get("decision"):
        return "verdict"
    if data.get("tool") or data.get("tool_name"):
        return "tool_call"
    if data.get("title") and (data.get("instruction") or data.get("instructions") or data.get("description")):
        return "field_task"
    if data.get("question") or data.get("message") or data.get("content") or data.get("answer"):
        return "clarify"
    return None


def _normalize_evidence_type(value: Any, data: dict[str, Any]) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "number": "count",
        "numeric": "count",
        "integer": "count",
        "image": "photo",
        "picture": "photo",
        "photos": "photo",
        "review": "rating",
        "ratings": "rating",
        "note": "text",
        "textarea": "text",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {"count", "photo", "rating", "text"}:
        return normalized

    combined = " ".join(
        str(data.get(key) or "")
        for key in ("title", "instruction", "instructions", "description")
    ).lower()
    if any(term in combined for term in ("rating", "review", "stars")):
        return "rating"
    if any(term in combined for term in ("photo", "image", "picture", "upload")):
        return "photo"
    if any(term in combined for term in ("count", "number", "how many", "footfall", "pax")):
        return "count"
    return "text"


def _normalize_tool_name(value: Any) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"fetch_competitors", "estimate_footfall", "calculate_breakeven"}:
        return normalized
    if "competitor" in normalized:
        return "fetch_competitors"
    if "footfall" in normalized or "traffic" in normalized:
        return "estimate_footfall"
    if "breakeven" in normalized or ("break" in normalized and "even" in normalized):
        return "calculate_breakeven"
    return None


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, number))


def _normalize_agent_data(data: dict[str, Any]) -> dict[str, Any]:
    """Repair common GLM output drift before validating with Pydantic."""
    output_type = _infer_output_type(data)
    if not output_type:
        raise ValueError(f"Unexpected GLM response shape: {data}")

    normalized = dict(data)
    normalized["type"] = output_type

    if output_type == "field_task":
        normalized["title"] = str(normalized.get("title") or "Collect missing evidence")
        normalized["instruction"] = str(
            normalized.get("instruction")
            or normalized.get("instructions")
            or normalized.get("description")
            or normalized.get("question")
            or "Provide the missing evidence needed to continue the investigation."
        )
        normalized["evidence_type"] = _normalize_evidence_type(
            normalized.get("evidence_type") or normalized.get("evidenceType"),
            normalized,
        )
    elif output_type == "clarify":
        normalized["question"] = str(
            normalized.get("question")
            or normalized.get("message")
            or normalized.get("content")
            or normalized.get("answer")
            or normalized.get("summary")
            or "Please clarify the missing detail."
        )
        options = normalized.get("options")
        normalized["options"] = (
            options if isinstance(options, list) and options else ["Answer question", "Add evidence"]
        )
    elif output_type == "verdict":
        normalized["decision"] = str(normalized.get("decision") or "PIVOT").upper()
        if normalized["decision"] not in {"GO", "PIVOT", "STOP"}:
            normalized["decision"] = "PIVOT"
        normalized["confidence"] = _confidence(normalized.get("confidence"))
        normalized["summary"] = str(
            normalized.get("summary")
            or normalized.get("reasoning")
            or "Verdict generated from the current investigation evidence."
        )
        if "pivot_suggestion" not in normalized:
            normalized["pivot_suggestion"] = normalized.get("next_step")
        if not isinstance(normalized.get("strengths"), list):
            normalized["strengths"] = []
    elif output_type == "tool_call":
        tool = _normalize_tool_name(normalized.get("tool") or normalized.get("tool_name"))
        if not tool:
            raise ValueError(f"Unexpected GLM tool name: {normalized.get('tool')}")
        normalized["tool"] = tool
        if not isinstance(normalized.get("args"), dict):
            normalized["args"] = {}

    return normalized


async def _post_chat_completions(
    payload: dict,
    timeout: float,
    max_retries: int,
    log_label: str,
) -> dict:
    base_url, api_key, _ = _get_glm_config()
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        async with httpx.AsyncClient(timeout=timeout, http2=False) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                error_detail = _response_error_text(exc.response)
                logger.error(
                    "%s request failed: status=%s error=%s",
                    log_label,
                    exc.response.status_code,
                    error_detail,
                )
                if exc.response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                raise RuntimeError(
                    f"{log_label} request failed ({exc.response.status_code}): {error_detail}"
                ) from exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                logger.warning("%s request failed before response: %s", log_label, exc)
                if attempt < max_retries:
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                raise

    raise RuntimeError(f"{log_label} request failed after retries: {last_error}")


async def glm_json_call(
    messages: list[dict],
    system: str,
    max_tokens: int = 1200,
    timeout: float = 20,
    max_retries: int = 1,
) -> dict:
    """Call GLM and return a raw JSON object."""
    _, _, model = _get_glm_config()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            *messages,
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }

    raw = await _post_chat_completions(payload, timeout, max_retries, "GLM JSON")
    return _json_from_content(raw["choices"][0]["message"]["content"], raw)


async def glm_call(
    messages: list[dict],
    system: str,
    timeout: float = 60,
    max_tokens: int = 2000,
    max_retries: int = 1,
) -> AgentOutput:
    _, _, model = _get_glm_config()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            *messages,
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }

    try:
        raw = await _post_chat_completions(payload, timeout, max_retries, "GLM API")
    except RuntimeError as exc:
        if settings.APP_ENV == "development" and "401" in str(exc):
            logger.warning("Using development fallback AI output because GLM authentication failed.")
            return _development_fallback_output()
        raise

    data = _json_from_content(raw["choices"][0]["message"]["content"], raw)
    data = _normalize_agent_data(data)

    type_map = {
        "tool_call": "ToolCallOutput",
        "field_task": "FieldTaskOutput",
        "clarify": "ClarifyOutput",
        "verdict": "VerdictOutput",
    }

    from app.ai import schemas

    model_name = type_map.get(data["type"])
    if not model_name:
        raise ValueError(f"Unexpected GLM output type: {data['type']}")
    model_cls = getattr(schemas, model_name)
    return model_cls(**data)
