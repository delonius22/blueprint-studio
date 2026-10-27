"""The `blueprint` AG-UI agent endpoint (SPECS S4.1, S4.2, S2.15).

Runs only on existing sessions, starts every run from the server's own state (the browser may
only clear ``last_error``, for Retry), syncs the attachments table into it, opens gate cards
the graph asks for, and records progress for the session list.
"""

import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, Self

from ag_ui.core import (
    CustomEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from copilotkit import LangGraphAGUIAgent

from blueprint.domain.state import SESSION_FIELDS
from blueprint.graph.gates import OPEN_GATE_EVENT
from blueprint.imports.proposal import sync_attachments
from blueprint.storage.sessions import AttachmentRow

AGENT_NAME = "blueprint"


def browser_state(checkpoint: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """The state a run starts from: the browser's copy with every session field taken from the
    checkpoint. The canvas is read-only, so the one thing the browser may change is clearing
    ``last_error`` (the Retry action, S11.6)."""
    if not checkpoint:
        return incoming
    state = {k: v for k, v in incoming.items() if k not in SESSION_FIELDS}
    state |= {k: checkpoint[k] for k in SESSION_FIELDS if k in checkpoint}
    if "last_error" in incoming and incoming["last_error"] is None:
        state["last_error"] = None
    return state


class SessionAgent(LangGraphAGUIAgent):
    """The `blueprint` AG-UI agent; runs only on existing sessions and records progress."""

    exists: Callable[[str], Awaitable[bool]] | None = None
    after_run: Callable[[str], Awaitable[None]] | None = None
    attachments: Callable[[str], Awaitable[list[AttachmentRow]]] | None = None

    def clone(self) -> Self:
        copy: Self = super().clone()
        copy.exists, copy.after_run = self.exists, self.after_run
        copy.attachments = self.attachments
        return copy

    async def run(self, input: RunAgentInput) -> AsyncGenerator[Any]:
        if self.exists is not None and not await self.exists(input.thread_id):
            yield RunErrorEvent(
                type=EventType.RUN_ERROR, message="unknown session", code="not_found"
            )
            return
        # S2.15: the browser's state is checked against the checkpoint before the graph sees it.
        checkpoint = await self.graph.aget_state({"configurable": {"thread_id": input.thread_id}})
        state = browser_state(dict(checkpoint.values or {}), dict(input.state or {}))
        if self.attachments is not None:  # SPEC-document-import §2.1: the table is the source
            state |= sync_attachments(state, await self.attachments(input.thread_id))
        input = input.model_copy(update={"state": state})
        async for event in super().run(input):  # type: ignore[no-untyped-call]
            yield event
            if isinstance(event, CustomEvent) and event.name == OPEN_GATE_EVENT:
                for gate_event in gate_tool_call_events(event.value):
                    yield gate_event
        if self.after_run is not None:
            await self.after_run(input.thread_id)


def gate_tool_call_events(value: dict[str, Any]) -> list[Any]:
    """The AG-UI events that make the browser open a gate card for this tool call."""
    call_id = value["id"]
    return [
        ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=call_id,
            tool_call_name=value["name"],
            parent_message_id=value.get("message_id") or call_id,
        ),
        ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS, tool_call_id=call_id, delta=json.dumps(value["args"])
        ),
        ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id=call_id),
    ]
