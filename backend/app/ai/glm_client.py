# app/ai/glm_client.py
import os, json, asyncio
from pathlib import Path
from dotenv import load_dotenv

_env = Path(__file__)
for _ in range(5):
    _env = _env.parent
    if (_env / ".env").exists():
        load_dotenv(dotenv_path=_env / ".env", override=True)
        break

import httpx
from app.ai.schemas import AgentOutput

ZAI_BASE = os.getenv("GLM_API_BASE_URL", "").rstrip("/")
ZAI_KEY  = os.getenv("GLM_API_KEY", "")

async def glm_call(
    messages: list[dict],
    system: str,
    max_retries: int = 3,
) -> AgentOutput:

    payload = {
        "model": os.getenv("GLM_MODEL_NAME", "ilmu-glm-5.1"),
        "messages": [
            {"role": "system", "content": system},
            *messages,
        ],
        "temperature": 0.1,
        "max_tokens":5000,   # increased — verdict needs ~500 tokens
    }

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=90, http2=False) as client:
                resp = await client.post(
                    f"{ZAI_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {ZAI_KEY}"},
                    json=payload,
                )

            # Handle 504 gateway timeout — retry
            if resp.status_code == 504:
                wait = attempt * 3
                print(f"  [glm_call] 504 gateway timeout, retrying in {wait}s (attempt {attempt}/{max_retries})")
                await asyncio.sleep(wait)
                continue

            resp.raise_for_status()

            raw     = resp.json()
            choice  = raw["choices"][0]
            message = choice.get("message", {})
            content = message.get("content")
            finish  = choice.get("finish_reason", "")

            # If truncated due to token limit — retry with a warning
            if finish == "length":
                print(f"  [glm_call] WARNING: response truncated (finish_reason=length). Retrying attempt {attempt}/{max_retries}")
                await asyncio.sleep(2)
                last_error = ValueError("GLM response truncated — increase max_tokens or shorten prompt")
                continue

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
                else:
                    print(f"  [glm_call] content is None, no tool_calls. Full message: {message}")
                    last_error = ValueError(f"GLM returned null content. Message: {message}")
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
                last_error = ValueError(f"Invalid JSON from GLM: {e} | content: {repr(content[:100])}")
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
            last_error = Exception("GLM timeout after 90s")
            continue

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503, 504):
                wait = attempt * 5
                print(f"  [glm_call] HTTP {e.response.status_code}, retrying in {wait}s")
                await asyncio.sleep(wait)
                last_error = e
                continue
            raise

    raise RuntimeError(
        f"GLM failed after {max_retries} attempts. Last error: {last_error}"
    )