"""Approval gates: frontend tools answered by the user in a card (PRD D5, SPECS S11.4).

The graph never executes a gate tool; it ends the run while a gate call is
unanswered (S5.1) and reads the user's answer from the tool result that the
next run brings. These helpers are pure functions of the message list.
"""

import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from pydantic import BaseModel, ValidationError

CONFIRM_STEP = "confirm_step"
DECIDE_GAPS = "decide_gaps"
SIGN_OFF_PRD = "sign_off_prd"
REVIEW_IMPORT = "review_import"
# Every approval gate (S11.4); the graph never executes these, the user answers them. Since the
# build, seams, proposed changes and tickets are accepted automatically and have no gate.
GATES = frozenset({CONFIRM_STEP, DECIDE_GAPS, SIGN_OFF_PRD, REVIEW_IMPORT})

# Custom graph event asking the agent endpoint to stream a gate tool call to the browser,
# under the tool call's own ID, once the graph has decided the card may open.
OPEN_GATE_EVENT = "blueprint_open_gate"


def call_name(messages: Sequence[BaseMessage], tool_call_id: str) -> str | None:
    """The name of the tool call that ``tool_call_id`` answers."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                if call["id"] == tool_call_id:
                    return str(call["name"])
    return None


def last_answer(messages: Sequence[BaseMessage]) -> tuple[str, dict[str, Any]] | None:
    """The newest message, when it is a tool result: (tool name, parsed JSON answer)."""
    if not messages or not isinstance(messages[-1], ToolMessage):
        return None
    result = messages[-1]
    name = call_name(messages, result.tool_call_id) or ""
    try:
        parsed = json.loads(result.text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        parsed = {"decisions": parsed}
    return name, parsed if isinstance(parsed, dict) else {}


def step_approved(answer: dict[str, Any]) -> bool:
    """S5.7: ``{"approved": true}``; anything else keeps the session on the step."""
    return answer.get("approved") is True


def gate_message(
    name: str, args: dict[str, Any], text: str = ""
) -> tuple[AIMessage, dict[str, Any]]:
    """A gate tool call made by the graph itself (not by a model), with its own IDs."""
    call = {
        "name": name,
        "args": args,
        "id": f"{name}-{uuid.uuid4().hex[:12]}",
        "type": "tool_call",
    }
    return AIMessage(content=text, tool_calls=[call], id=f"gate-{uuid.uuid4().hex[:12]}"), call


def close_unanswered(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """The history a model may see: a tool call the user never answered (they wrote a message
    instead) gets a placeholder result, as Chat Completions requires."""
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    result: list[BaseMessage] = []
    for message in messages:
        result.append(message)
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                if call["id"] not in answered:
                    result.append(
                        ToolMessage(
                            "(not answered: the user replied in the chat instead)",
                            tool_call_id=call["id"],
                        )
                    )
    # A trailing placeholder would hide a call the run is still waiting on; keep the tail as is.
    while (
        result and isinstance(result[-1], ToolMessage) and result[-1].tool_call_id not in answered
    ):
        result.pop()
    return result


class GapDecision(BaseModel):
    gap_id: str
    decision: str
    text: str = ""


def gap_decisions(answer: Any) -> list[GapDecision]:
    """S6.5: decide_gaps answers a list of {gap_id, decision: answer|accept, text}."""
    items = answer.get("decisions") if isinstance(answer, dict) else answer
    decisions: list[GapDecision] = []
    for item in items if isinstance(items, list) else []:
        try:
            decision = GapDecision.model_validate(item)
        except ValidationError:
            continue
        if decision.decision in ("answer", "accept"):
            decisions.append(decision)
    return decisions


def latest_answer_to(messages: Sequence[BaseMessage], name: str) -> Any:
    """The parsed content of the newest tool result answering a ``name`` call, if any."""
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and call_name(messages, message.tool_call_id) == name:
            try:
                return json.loads(message.text)
            except json.JSONDecodeError:
                return None
    return None


def pending_gate(messages: Sequence[BaseMessage]) -> str | None:
    """The gate the newest message is still waiting on, if any."""
    if not messages or not isinstance(messages[-1], AIMessage):
        return None
    for call in messages[-1].tool_calls:
        if call["name"] in GATES:
            return str(call["name"])
    return None


# --- the tools of one run ---------------------------------------------------------------------


def frontend_actions(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The frontend tools CopilotKit sent with this run (PRD OQ-2)."""
    copilotkit: Any = state.get("copilotkit") or {}
    return list(copilotkit.get("actions") or [])


def last_message(state: Mapping[str, Any]) -> BaseMessage | None:
    messages = state.get("messages") or []
    return messages[-1] if messages else None


def backend_calls(state: Mapping[str, Any], message: AIMessage) -> list[dict[str, Any]]:
    """The calls the graph executes itself: everything but frontend tools and gates."""
    frontend = {str(action.get("name")) for action in frontend_actions(state)} | GATES
    return [dict(call) for call in message.tool_calls if call["name"] not in frontend]


def confirm_calls(message: AIMessage) -> list[dict[str, Any]]:
    """confirm_step calls, which design_tools checks for blockers before any card opens (S5.6)."""
    return [dict(call) for call in message.tool_calls if call["name"] == CONFIRM_STEP]
