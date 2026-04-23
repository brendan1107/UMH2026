#core loop

# ai/agent.py
import json
from ai.schemas import BusinessCase, AgentOutput
from ai.glm_client import glm_call
from ai.prompts import build_agent_prompt
from ai.tools import TOOL_REGISTRY
from ai.state import next_phase, apply_tool_result

async def run_agent_turn(case: BusinessCase) -> tuple[BusinessCase, AgentOutput]:
    """
    One turn of the ReAct loop.
    Returns the updated case + the output the GLM produced.
    Your teammate calls this from the FastAPI route.

    Usage:
        updated_case, output = await run_agent_turn(case)
        # save updated_case back to Supabase
        # push output to frontend via realtime
    """

    # 1. Build system prompt from current case state
    system = build_agent_prompt(case)

    # 2. Call GLM — get a validated AgentOutput back
    output = await glm_call(
        messages=case.messages,
        system=system,
    )

    # 3. Append GLM response to conversation history
    case.messages.append({
        "role": "assistant",
        "content": output.model_dump_json(),
    })

    # 4. If it's a tool call — execute the tool, write result to fact_sheet
    if output.type == "tool_call":
        tool_fn = TOOL_REGISTRY.get(output.tool)
        if tool_fn:
            result = await tool_fn(**output.args)
            case = apply_tool_result(case, output.tool, result.model_dump())

            # Append tool result to messages so GLM sees it next turn
            case.messages.append({
                "role": "user",
                "content": json.dumps({
                    "tool_result": output.tool,
                    "data": result.model_dump(),
                })
            })

            # After a tool call, immediately run another turn
            # (tool calls don't need user input — loop continues automatically)
            return await run_agent_turn(case)

    # 5. Advance the phase based on what just happened
    case.phase = next_phase(case, output)

    return case, output