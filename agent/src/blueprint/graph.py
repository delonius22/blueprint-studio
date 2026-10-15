"""The LangGraph graph served at /agent (SPECS S4.1, S5).

Nodes do the work; routing functions are pure functions of state (S5.1).
"""

import json
from typing import Any

from copilotkit.langgraph import copilotkit_customize_config
from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from blueprint.assets import Assets
from blueprint.design import (
    Draft,
    ToolFailure,
    bound_tool_names,
    run_tool,
    step_blockers,
    tool_schemas,
)
from blueprint.domain import Critique, Design, Model, Scorecard
from blueprint.gates import CONFIRM_STEP, OPEN_GATE_EVENT, last_answer, step_approved
from blueprint.llm import InvalidStructuredOutput, Meter, ModelCallFailed, ModelGateway
from blueprint.models import RoleModels
from blueprint.prompts import critic_prompt, interviewer_prompt, transcript
from blueprint.scoring import ScorecardError, make_scorecard
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


def _gate_calls(message: AIMessage) -> list[dict[str, Any]]:
    """confirm_step calls, which design_tools checks for blockers before any card opens (S5.6)."""
    return [dict(call) for call in message.tool_calls if call["name"] == CONFIRM_STEP]


# --- routing (pure) --------------------------------------------------------------------------


def route_start(state: DesignState) -> str:
    """Route a new run by what the user just sent (S5.1).

    A chat message goes to the interviewer; an approved ``confirm_step`` goes to the
    critic (S5.7, S5.8); any other gate answer, including a rejection, goes to the
    interviewer. A run with nothing new ends at once (used to re-sync a thread).
    """
    if state.get("last_error"):
        return END
    messages = list(state.get("messages") or [])
    answer = last_answer(messages)
    if answer is not None:
        name, content = answer
        if name == CONFIRM_STEP and step_approved(content):
            return "critic"
        return "interviewer"
    if isinstance(_last(state), HumanMessage):
        return "interviewer"
    return END


def route_interviewer(state: DesignState) -> str:
    """Backend calls and confirm_step go to design_tools; a text reply or an error ends the run."""
    if state.get("last_error"):
        return END
    last = _last(state)
    if isinstance(last, AIMessage) and (_backend_calls(state, last) or _gate_calls(last)):
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


async def open_gate(config: RunnableConfig, message: AIMessage, call: dict[str, Any]) -> None:
    """Stream a gate tool call to the browser so its card opens (S5.6, S11.4)."""
    await adispatch_custom_event(
        OPEN_GATE_EVENT,
        {"id": call["id"], "name": call["name"], "args": call["args"], "message_id": message.id},
        config=config,
    )


# --- critique ------------------------------------------------------------------------------


class CritiqueDraft(Model):
    """What the critic model returns (S2.8 Critique without the step)."""

    strengths: list[str]
    bottlenecks: list[str]
    questions: list[str]


def format_critique(critique: Critique) -> str:
    """The critique as a chat message in the three-part format of FR-9."""

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) or "- (none)"

    return (
        f"**Step {critique.step} critique**\n\n"
        f"🟢 **Strengths & Alignment**\n{bullets(critique.strengths)}\n\n"
        f"⚠️ **Bottlenecks & Unaddressed Trade-Offs**\n{bullets(critique.bottlenecks)}\n\n"
        f"❓ **Probing / Next-Step Questions**\n{bullets(critique.questions)}"
    )


def format_scorecard(scorecard: Scorecard) -> str:
    """The final scorecard as a chat message (FR-9)."""
    parts = ["**Final scorecard**"]
    for score in scorecard.dimensions:
        quotes = "\n".join(f'  > "{quote}"' for quote in score.evidence)
        parts.append(
            f"**{score.dimension.capitalize()}: {score.score}/4**\n{quotes}\n  Advice: {score.advice}"
        )
    return "\n\n".join(parts)


# --- nodes -----------------------------------------------------------------------------------


def build_graph(
    models: RoleModels,
    checkpointer: BaseCheckpointSaver[Any],
    assets: Assets,
    gateway: ModelGateway | None = None,
) -> Graph:
    calls = gateway or ModelGateway(models)

    async def interviewer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        step = state["current_step"]
        design = Design.model_validate(state["design"])
        system = interviewer_prompt(assets, state["stage"], step, design)
        tools = tool_schemas(bound_tool_names(step)) + frontend_actions(state)
        # Tool calls are not streamed to the browser: backend calls are internal, and a
        # confirm_step card may only open after design_tools has checked its blockers (S5.6).
        quiet = copilotkit_customize_config(config, emit_tool_calls=False)
        quiet["metadata"] = {**quiet.get("metadata", {}), "emit-tool-calls": False}
        meter = Meter.for_node(state, "interviewer")
        try:
            reply = await calls.chat(
                meter,
                "interview",
                [SystemMessage(system), *state["messages"]],
                quiet,
                tools,
                measure_ttft=True,
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}  # S13.2: nothing else changes
        return {"messages": [reply], "tokens_used": meter.used, "last_error": None}

    async def design_tools(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
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
        for call in _gate_calls(last):
            blockers = step_blockers(state["current_step"], draft.design)
            if blockers:
                content = json.dumps(
                    {
                        "error": f"Step {state['current_step']} cannot be confirmed yet.",
                        "blockers": blockers,
                    }
                )
                results.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
            else:
                await open_gate(config, last, call)
        written = draft.design.model_dump(mode="json")
        return {
            "messages": results,
            "design": written,
            "agent_design": written,
            "id_counters": draft.counters,
        }

    async def critic(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        """S5.7 approval and S5.8 critique: confirm the step, critique it, move on."""
        step = state["current_step"]
        design = Design.model_validate(state["design"])
        meter = Meter.for_node(state, "critic")
        try:
            draft = await calls.structured(
                meter,
                "interview",
                CritiqueDraft,
                [
                    SystemMessage(critic_prompt(assets, step, design)),
                    HumanMessage("Conversation so far:\n\n" + transcript(state["messages"])),
                ],
                config,
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}
        except InvalidStructuredOutput as invalid:
            error = ModelCallFailed("invalid_output", str(invalid), retryable=True)
            return {"last_error": error.info(), "tokens_used": meter.used}
        critique = Critique(step=step, **draft.model_dump())
        update: dict[str, Any] = {
            "tokens_used": meter.used,
            "last_error": None,
            "confirmed_steps": sorted({*state["confirmed_steps"], step}),
            "current_step": min(step + 1, 5),
            "critiques": [*state["critiques"], critique.model_dump(mode="json")],
        }
        messages = [AIMessage(format_critique(critique))]
        if step == 5:
            try:
                scorecard = await make_scorecard(
                    calls, meter, assets, design, state["messages"], config
                )
            except ModelCallFailed as failure:
                return {"last_error": failure.info()}  # S13.2: the critique is not stored either
            except ScorecardError as invalid:
                error = ModelCallFailed(
                    "invalid_output",
                    f"The scorecard could not be produced: {invalid}",
                    retryable=True,
                )
                return {"last_error": error.info(), "tokens_used": meter.used}
            update |= {
                "scorecard": scorecard.model_dump(mode="json"),
                "stage": "design_review",
                "tokens_used": meter.used,
            }
            messages.append(AIMessage(format_scorecard(scorecard)))
        return update | {"messages": messages}

    builder = StateGraph(DesignState)
    builder.add_node("interviewer", interviewer)
    builder.add_node("design_tools", design_tools)
    builder.add_node("critic", critic)
    builder.add_conditional_edges(START, route_start, ["interviewer", "critic", END])
    builder.add_edge("critic", END)
    builder.add_conditional_edges("interviewer", route_interviewer, ["design_tools", END])
    builder.add_conditional_edges("design_tools", route_design_tools, ["interviewer", END])
    return builder.compile(checkpointer=checkpointer)
