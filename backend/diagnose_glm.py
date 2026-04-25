# diagnose_glm.py
# python diagnose_glm.py
 
import asyncio, httpx, os, sys, json
from pathlib import Path
 
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT / ".env")
 
base  = os.getenv("GLM_API_BASE_URL", "").rstrip("/")
key   = os.getenv("GLM_API_KEY", "")
model = os.getenv("GLM_MODEL_NAME", "ilmu-glm-5.1")
 
SYSTEM = """You are F&B Genie, a cynical business auditor for Malaysian F&B businesses.
You MUST respond with a single JSON object only.
Do NOT use markdown code fences.
Do NOT add any text before or after the JSON.
Do NOT use tool_calls. Put everything inside the JSON content field.
The JSON must match EXACTLY one of these four shapes:
 
Shape 1: {"type":"tool_call","tool":"fetch_competitors","args":{"location":"...","category":"..."}}
Shape 2: {"type":"field_task","title":"short title","instruction":"detailed instruction","evidence_type":"count"}
Shape 3: {"type":"clarify","question":"your question","options":["Option A","Option B","Option C"]}
Shape 4: {"type":"verdict","decision":"GO","confidence":0.75,"summary":"2-3 sentence summary","pivot_suggestion":null}
 
Start your response with the { character."""
 
SCENARIOS = [
    {
        "name": "tool_call",
        "user": "Case: RM15 Nasi Lemak cafe in SS15. Budget: RM30000. No facts collected yet. Call fetch_competitors tool now.",
    },
    {
        "name": "field_task",
        "user": "Case: RM15 Nasi Lemak cafe in SS15. competitor_count is 6. I need the user to physically visit SS15 at 1PM and count the queue length at nearby stalls. Assign a field task.",
    },
    {
        "name": "clarify",
        "user": "Case: A cafe in Bangsar. The business format is unknown. Ask user if dine-in, takeaway, or cloud kitchen.",
    },
    {
        "name": "verdict",
        "user": "All facts collected. competitor_count=6, avg_competitor_rating=4.1, estimated_footfall_lunch=90, confirmed_rent_myr=3200, break_even_covers=87. Issue verdict now. Decision must be GO, PIVOT, or STOP.",
    },
]
 
 
async def test_scenario(name: str, user_msg: str):
    print(f"\n{'='*55}")
    print(f"Scenario: {name}")
    print(f"{'='*55}")
 
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": user_msg},
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
        )
 
    print(f"HTTP status  : {resp.status_code}")
    print(f"Raw bytes    : {len(resp.content)} bytes")
    print(f"Raw text 200 : {repr(resp.text[:200])}")
 
    if not resp.text.strip():
        print("FAIL -- Empty response body")
        return
 
    try:
        data = resp.json()
    except Exception as e:
        print(f"FAIL -- Not valid JSON: {e}")
        print(f"Full text: {resp.text[:500]}")
        return
 
    choices = data.get("choices")
    if not choices:
        print(f"FAIL -- No choices. Keys: {list(data.keys())}")
        return
 
    message    = choices[0].get("message", {})
    content    = message.get("content")
    tool_calls = message.get("tool_calls")
 
    print(f"content      : {repr(content)}")
    print(f"tool_calls   : {tool_calls}")
    print(f"finish_reason: {choices[0].get('finish_reason')}")
 
    if content is None and tool_calls:
        tc      = tool_calls[0]
        fn_name = tc.get("function", {}).get("name", "fetch_competitors")
        args    = tc.get("function", {}).get("arguments", "{}")
        try:
            args_dict = json.loads(args) if isinstance(args, str) else args
        except Exception:
            args_dict = {}
        content = json.dumps({"type": "tool_call", "tool": fn_name, "args": args_dict})
        print(f"Extracted from tool_calls: {content}")
 
    if content is None:
        print("FAIL -- content is None and no tool_calls")
        return
 
    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        parsed  = json.loads(cleaned)
        print(f"Parsed type  : {parsed.get('type')}")
        print("PARSE: OK")
    except Exception as e:
        print(f"PARSE: FAIL -- {e}")
        print(f"Cleaned: {repr(cleaned[:300])}")
 
 
async def main():
    print(f"Base  : {base}")
    print(f"Model : {model}")
    print(f"Key   : {key[:15]}...")
    for s in SCENARIOS:
        await test_scenario(s["name"], s["user"])
        await asyncio.sleep(2)
 
asyncio.run(main())
 