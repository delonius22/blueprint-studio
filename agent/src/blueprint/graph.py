"""The LangGraph graph served at /agent (SPECS S4.1, S5).

Nodes do the work; routing functions are pure functions of state (S5.1).
"""

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from blueprint.assets import Assets
from blueprint.design import Draft, ToolFailure, bound_tool_names, run_tool, tool_schemas
from blueprint.domain import Design
from blueprint.models import RoleModels
from blueprint.prompts import interviewer_prompt
from blueprint.state import DesignState

Graph = CompiledStateGraph[DesignState, None, DesignState, DesignState]


def frontend_actions(state: DesignState) -> list[dict[str, Any]]:
    """The frontend tools CopilotKit sent with this run (PRD OQ-2, QUESTIONS Q-6)."""
    copilotkit: Any = state.get("copilotkit") or {}
    return list(copilotkit.get("actions") or [])


def frontend_names(state: DesignState) -> set[str]:
    return {str(action.get("name")) for action in frontend_actions(state)}


def _last(state: DesignState) -> BaseMessage | None:
    messages = state.get("messages") or []
    return messages[-1] if messages else None


def _backend_calls(state: DesignState, message: AIMessage) -> list[dict[str, Any]]:
    frontend = frontend_names(state)
    return [dict(call) for call in message.tool_calls if call["name"] not in frontend]


# --- routing (pure) --------------------------------------------------------------------------


def route_start(state: DesignState) -> str:
    """A run with nothing new from the user ends at once (used to re-sync a thread)."""
    last = _last(state)
    if isinstance(last, HumanMessage | ToolMessage):
        return "interviewer"
    return END


def route_interviewer(state: DesignState) -> str:
    """Backend tool calls run in design_tools; a text reply or a pending gate ends the run."""
    last = _last(state)
    if isinstance(last, AIMessage) and _backend_calls(state, last):
        return "design_tools"
    return END


def route_design_tools(state: DesignState) -> str:
    """Back to the interviewer, unless a frontend gate call from the same turn awaits the user."""
    messages = state.get("messages") or []
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    turn = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    if turn and any(call["id"] not in answered for call in turn.tool_calls):
        return END
    return "interviewer"


# --- nodes -----------------------------------------------------------------------------------


def build_graph(
    models: RoleModels, checkpointer: BaseCheckpointSaver[Any], assets: Assets
) -> Graph:
    async def interviewer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        step = state["current_step"]
        design = Design.model_validate(state["design"])
        system = interviewer_prompt(assets, state["stage"], step, design)
        tools = tool_schemas(bound_tool_names(step)) + frontend_actions(state)
        model = models.interview.bind_tools(tools)
        reply = await model.ainvoke([SystemMessage(system), *state["messages"]], config)
        return {"messages": [reply]}

    async def design_tools(state: DesignState) -> dict[str, Any]:
        last = _last(state)
        assert isinstance(last, AIMessage)
        draft = Draft(Design.model_validate(state["design"]), dict(state["id_counters"]))
        allowed = bound_tool_names(state["current_step"])
        results: list[ToolMessage] = []
        for call in _backend_calls(state, last):
            counters = dict(draft.counters)
            try:
                content = run_tool(call["name"], call["args"], draft, allowed)
            except ToolFailure as failure:
                draft.counters = counters
                content = json.dumps({"error": str(failure)})
            results.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
        written = draft.design.model_dump(mode="json")
        return {
            "messages": results,
            "design": written,
            "agent_design": written,
            "id_counters": draft.counters,
        }

    builder = StateGraph(DesignState)
    builder.add_node("interviewer", interviewer)
    builder.add_node("design_tools", design_tools)
    builder.add_conditional_edges(START, route_start, ["interviewer", END])
    builder.add_conditional_edges("interviewer", route_interviewer, ["design_tools", END])
    builder.add_conditional_edges("design_tools", route_design_tools, ["interviewer", END])
    return builder.compile(checkpointer=checkpointer)
