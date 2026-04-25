# app/ai/test/run_all_tests.py
# Master test runner — runs all 5 test stages in order
# Run: python app/ai/test/run_all_tests.py
 
import asyncio, sys, os, time
from pathlib import Path
 
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT / ".env")
 
PASS = "PASS"
FAIL = "FAIL"
 
results = {}
 
def header(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")
 
 
# ── Stage 0: Environment check ───────────────────────────────
def stage_0_env():
    header("Stage 0: Environment variables")
    required = [
        "GLM_API_KEY",
        "GLM_API_BASE_URL",
        "GLM_MODEL_NAME",
        "GOOGLE_PLACES_API_KEY",
    ]
    all_ok = True
    for key in required:
        val = os.getenv(key, "")
        status = "OK " if val else "MISSING"
        preview = f"({val[:14]}...)" if val else ""
        print(f"  {status}  {key} {preview}")
        if not val:
            all_ok = False
 
    results["Stage 0: Env vars"] = PASS if all_ok else FAIL
    if not all_ok:
        print("\n  FAIL -- Add missing keys to backend/.env before continuing")
    else:
        print("\n  PASS -- All environment variables present")
    return all_ok
 
 
# ── Stage 1: GLM raw connection ──────────────────────────────
async def stage_1_glm():
    header("Stage 1: GLM API connection (raw)")
    import httpx, json

    base  = os.getenv("GLM_API_BASE_URL", "").rstrip("/")
    key   = os.getenv("GLM_API_KEY", "")
    model = os.getenv("GLM_MODEL_NAME", "gemini-1.5-flash") # Fallback to correct model

    try:
        t0 = time.time()
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": 'Reply with only: {"status":"ok"}'}],
                    "temperature": 0.1,
                    "max_tokens": 50,
                },
            )
        elapsed = time.time() - t0

        print(f"  HTTP status  : {resp.status_code}")
        print(f"  Response time: {elapsed:.2f}s")

        if resp.status_code == 401:
            print("  FAIL -- 401 Unauthorized.")
            results["Stage 1: GLM connection"] = FAIL
            return False

        resp.raise_for_status()

        data    = resp.json()
        choices = data.get("choices")
        if not choices:
            print(f"  FAIL -- No choices. Keys: {list(data.keys())}")
            results["Stage 1: GLM connection"] = FAIL
            return False

        content = choices[0].get("message", {}).get("content") or ""
        print(f"  Raw reply    : {content[:80]}")
        print(f"  PASS -- GLM API reachable, {elapsed:.1f}s")
        results["Stage 1: GLM connection"] = PASS
        return True

    except httpx.ReadTimeout:
        print("  FAIL -- Timeout after 90s.")
        results["Stage 1: GLM connection"] = FAIL
        return False
    except Exception as e:
        print(f"  FAIL -- {type(e).__name__}: {e}")
        results["Stage 1: GLM connection"] = FAIL
        return False
 
# ── Stage 2: Google Maps tools ───────────────────────────────
async def stage_2_tools():
    header("Stage 2: Google Maps API (real tool calls)")
 
    try:
        from app.ai.tools import fetch_competitors, calculate_breakeven
 
        # 2a: fetch_competitors
        print("  Calling fetch_competitors(SS15)...")
        comp = await fetch_competitors("SS15, Subang Jaya", "restaurant")
        print(f"  count={comp.count}, avg_rating={comp.avg_rating}")
        assert comp.count >= 0
        print("  fetch_competitors : PASS")
 
        # 2b: calculate_breakeven (pure math, no API)
        bev = await calculate_breakeven(15.0, 3200.0, 2)
        print(f"  breakeven={bev.breakeven_covers_per_day} covers/day")
        assert bev.breakeven_covers_per_day > 0
        print("  calculate_breakeven : PASS")
 
        results["Stage 2: Google Maps tools"] = PASS
        print("  PASS -- Google Maps API working")
        return True
 
    except Exception as e:
        print(f"  FAIL -- {e}")
        results["Stage 2: Google Maps tools"] = FAIL
        return False
 
 
# ── Stage 3: GLM prompt → structured JSON output ─────────────
async def stage_3_prompt():
    header("Stage 3: GLM prompt → valid JSON output (4 scenarios)")
    import httpx, json
    from pydantic import BaseModel, ValidationError
    from typing import Literal, Any
 
    class ToolCallOutput(BaseModel):
        type: Literal["tool_call"]
        tool: str
        args: dict[str, Any]
 
    class FieldTaskOutput(BaseModel):
        type: Literal["field_task"]
        title: str
        instruction: str
        evidence_type: Literal["count", "photo", "rating", "text"]
 
    class ClarifyOutput(BaseModel):
        type: Literal["clarify"]
        question: str
        options: list[str]
 
    class VerdictOutput(BaseModel):
        type: Literal["verdict"]
        decision: Literal["GO", "PIVOT", "STOP"]
        confidence: float
        summary: str
 
    TYPE_MAP = {
        "tool_call": ToolCallOutput,
        "field_task": FieldTaskOutput,
        "clarify": ClarifyOutput,
        "verdict": VerdictOutput,
    }
 
    base  = os.getenv("GLM_API_BASE_URL", "").rstrip("/")
    key   = os.getenv("GLM_API_KEY", "")
    model = os.getenv("GLM_MODEL_NAME", "gemini-1.5-flash") # Ensure correct model
 
    SYSTEM = """You are F&B Genie, a cynical business auditor.
Output valid JSON only. No preamble, no markdown fences.
Choose exactly one type:
- {"type":"tool_call","tool":"fetch_competitors","args":{"location":"...","category":"..."}}
- {"type":"field_task","title":"...","instruction":"...","evidence_type":"count|photo|rating|text"}
- {"type":"clarify","question":"...","options":["...","..."]}
- {"type":"verdict","decision":"GO|PIVOT|STOP","confidence":0.0-1.0,"summary":"..."}"""
 
    scenarios = [
        {
            "name": "tool_call — no competitor data",
            "user": "Case: RM15 Nasi Lemak in SS15. Budget: RM30k. Known facts: {}. Missing: competitor_count. What next?",
            "expect": "tool_call",
        },
        {
            "name": "field_task — missing footfall",
            "user": 'Case: RM15 Nasi Lemak in SS15. Known facts: {"competitor_count":6}. Missing: estimated_footfall_lunch. What next?',
            "expect": "field_task",
        },
        {
            "name": "clarify — ambiguous format",
            "user": "Case: A cafe in Bangsar. Format unknown (dine-in/takeaway/cloud-kitchen). What next?",
            "expect": "clarify",
        },
        {
            "name": "verdict — all facts present",
            "user": 'Case: RM15 Nasi Lemak in SS15. Known facts: {"competitor_count":6,"avg_competitor_rating":4.1,"estimated_footfall_lunch":90,"confirmed_rent_myr":3200,"break_even_covers":87}. All facts collected. Issue verdict now.',
            "expect": "verdict",
        },
    ]
 
    passed = 0
    for s in scenarios:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": SYSTEM},
                            {"role": "user",   "content": s["user"]},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000, # <-- FIX: INCREASED TO 2000
                    },
                )
            
            if resp.status_code != 200:
                print(f"  FAIL  [{s['name']}] — API Error {resp.status_code}: {resp.text}")
                continue

            content = resp.json()["choices"][0]["message"]["content"]
            if content is None:
                print(f"  FAIL  [{s['name']}] — AI returned null content")
                continue
                
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
 
            data = json.loads(content)
            cls  = TYPE_MAP.get(data.get("type"))
            if not cls:
                raise ValueError(f"Unknown type: {data.get('type')}")
            obj = cls(**data)
 
            if obj.type == s["expect"]:
                print(f"  PASS  [{s['name']}]")
                passed += 1
            else:
                print(f"  FAIL  [{s['name']}] — expected {s['expect']}, got {obj.type}")
 
        except Exception as e:
            print(f"  FAIL  [{s['name']}] — {e}")
 
    if passed == len(scenarios):
        results["Stage 3: GLM prompt output"] = PASS
        print(f"  PASS -- {passed}/{len(scenarios)} scenarios correct")
        return True
    else:
        results["Stage 3: GLM prompt output"] = FAIL
        print(f"  FAIL -- {passed}/{len(scenarios)} scenarios correct")
        return False
 
 
# ── Stage 4: Full agent loop (with simulated field tasks) ────
async def stage_4_agent_loop():
    header("Stage 4: Full agent loop (GLM + real tools)")
 
    from app.ai.schemas import BusinessCase as AICase
    from app.ai.orchestrator import run_agent_turn
    import json
 
    REQUIRED_FACTS = [
        "competitor_count", "avg_competitor_rating",
        "estimated_footfall_lunch", "confirmed_rent_myr", "break_even_covers",
    ]
 
    case = AICase(
        id="run-all-test",
        idea="A RM15 Nasi Lemak cafe in SS15 targeting office workers",
        location="SS15, Subang Jaya",
        budget_myr=30000.0,
        phase="INTAKE",
        fact_sheet={},
        messages=[],
    )
 
    max_turns = 12
    turn = 0
    output = None
 
    try:
        while case.phase != "VERDICT" and turn < max_turns:
            turn += 1
            case, output = await run_agent_turn(case)
            print(f"  Turn {turn}: phase={case.phase} output={output.type}")
 
            if output.type == "field_task":
                # Simulate user completing field tasks with REALISTIC data
                case.fact_sheet.update({
                    "competitor_count":         case.fact_sheet.get("competitor_count", 6),
                    "avg_competitor_rating":    case.fact_sheet.get("avg_competitor_rating", 4.1),
                    "estimated_footfall_lunch": case.fact_sheet.get("estimated_footfall_lunch", 90),
                    "confirmed_rent_myr":       3200,
                    "break_even_covers":        case.fact_sheet.get("break_even_covers", 87),
                })
                case.messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "task_completed": output.title, 
                        "submitted_facts": "User has successfully collected all missing facts in the real world."
                    })
                })
 
            elif output.type == "clarify":
                case.messages.append({
                    "role": "user",
                    "content": f"Answer: {output.options[0]}"
                })
 
        if case.phase == "VERDICT" and output and output.type == "verdict":
            assert output.decision in ("GO", "PIVOT", "STOP")
            missing = [f for f in REQUIRED_FACTS if f not in case.fact_sheet]
            assert not missing, f"Missing facts: {missing}"
            print(f"  Verdict: {output.decision} ({output.confidence*100:.0f}% confidence)")
            print(f"  Facts collected: {list(case.fact_sheet.keys())}")
            results["Stage 4: Agent loop"] = PASS
            print("  PASS -- Agent loop completed correctly")
            return True, case, output
        else:
            print(f"  FAIL -- Loop ended at phase {case.phase} without verdict")
            results["Stage 4: Agent loop"] = FAIL
            return False, case, output
 
    except Exception as e:
        print(f"  FAIL -- {e}")
        import traceback
        traceback.print_exc()
        results["Stage 4: Agent loop"] = FAIL
        return False, case, output
 
 
# ── Stage 5: Auditor on real verdict ─────────────────────────
async def stage_5_auditor(case, verdict_output):
    header("Stage 5: Auditor (Pass 2) on real verdict data")
 
    try:
        from app.ai.review_layer import run_audit
 
        audit = await run_audit(case, verdict_output.summary)
 
        print(f"  Risks returned: {len(audit.risks)}")
        for r in audit.risks:
            print(f"  [{r.severity.upper()}] {r.title}")
 
        assert len(audit.risks) == 3, f"Expected 3 risks, got {len(audit.risks)}"
        assert all(r.severity in ("high","medium","low") for r in audit.risks)
        assert all(r.category in ("financial","market","ops","regulatory") for r in audit.risks)
 
        results["Stage 5: Auditor"] = PASS
        print("  PASS -- Auditor returned 3 valid risk items")
        return True
 
    except Exception as e:
        print(f"  FAIL -- {e}")
        results["Stage 5: Auditor"] = FAIL
        return False
 
 
# ── Final summary ─────────────────────────────────────────────
def print_summary():
    header("FINAL RESULTS")
    all_passed = True
    for stage, result in results.items():
        icon = "✓" if result == PASS else "✗"
        print(f"  {icon}  {stage}: {result}")
        if result == FAIL:
            all_passed = False
 
    print()
    if all_passed:
        print("  ALL STAGES PASSED")
        print("  Your AI system is fully verified end-to-end.")
        print("  Ready for Firestore integration and demo.")
    else:
        failed = [s for s, r in results.items() if r == FAIL]
        print(f"  {len(failed)} stage(s) failed: {failed}")
        print("  Fix the failed stages before demo.")
 
 
if __name__ == "__main__":
    async def main():
        # Stage 0 — env check (sync)
        env_ok = stage_0_env()
        if not env_ok:
            print_summary()
            sys.exit(1)
 
        # Stage 1 — GLM connection
        glm_ok = await stage_1_glm()
        if not glm_ok:
            print_summary()
            sys.exit(1)
 
        # Stage 2 — Google Maps tools
        await stage_2_tools()
 
        # Stage 3 — GLM prompt scenarios
        await stage_3_prompt()
 
        # Stage 4 — Full agent loop
        loop_ok, final_case, final_output = await stage_4_agent_loop()
 
        # Stage 5 — Auditor (only if loop passed)
        if loop_ok and final_output and final_output.type == "verdict":
            await stage_5_auditor(final_case, final_output)
        else:
            results["Stage 5: Auditor"] = FAIL
            print("\nSkipping Stage 5 — agent loop must pass first")
 
        print_summary()
 
    asyncio.run(main())