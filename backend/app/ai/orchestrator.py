# app/ai/orchestrator.py
import json
from app.ai.schemas import BusinessCase, AgentOutput
from app.ai.glm_client import glm_call
from app.ai.prompts_templates import build_agent_prompt
from app.ai.tools import TOOL_REGISTRY
from app.ai.state import next_phase, apply_tool_result

MAX_TOOL_DEPTH = 5

async def run_agent_turn(
    case: BusinessCase,
    _depth: int = 0,
) -> tuple[BusinessCase, AgentOutput]:
    if _depth >= MAX_TOOL_DEPTH:
        raise RuntimeError(f"Agent exceeded max tool call depth ({MAX_TOOL_DEPTH}).")

    system = build_agent_prompt(case)

    messages = case.messages
    if not messages:
        messages = [{
            "role": "user",
            "content": "Begin your investigation. What do you need to find out first?",
        }]

    output = await glm_call(
        messages=messages,
        system=system,
    )

    case.messages.append({
        "role": "assistant",
        "content": output.model_dump_json(),
    })

    if output.type == "tool_call":
        tool_fn = TOOL_REGISTRY.get(output.tool)
        if tool_fn:
            result = await tool_fn(**output.args)
            case = apply_tool_result(case, output.tool, result.model_dump())
            case.messages.append({
                "role": "user",
                "content": json.dumps({
                    "tool_result": output.tool,
                    "data": result.model_dump(),
                })
            })
            return await run_agent_turn(case, _depth=_depth + 1)

    # If verdict, mark phase but don't lock —
    # user can add more info and get a revised verdict
    if output.type == "verdict":
        case.phase = "VERDICT"
    else:
        # If case was in VERDICT but user added new info, reopen to EVIDENCE
        if case.phase == "VERDICT":
            case.phase = "EVIDENCE"
        else:
            case.phase = next_phase(case, output)

    return case, output