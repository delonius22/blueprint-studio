"""Approval gates: frontend tools answered by the user in a card (PRD D5, SPECS S11.4).

The graph never executes a gate tool; it ends the run while a gate call is
unanswered (S5.1) and reads the user's answer from the tool result that the
next run brings. These helpers are pure functions of the message list.
"""

import json
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

CONFIRM_STEP = "confirm_step"

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
    return name, parsed if isinstance(parsed, dict) else {}


def step_approved(answer: dict[str, Any]) -> bool:
    """S5.7: ``{"approved": true}``; anything else keeps the session on the step."""
    return answer.get("approved") is True
