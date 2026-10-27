"""What every graph node needs, and the steps nodes share (SPECS S5.1, S13.2).

Each stage package (``interview``, ``review``, ``planning``, ``imports``) holds its own nodes
as ``async def node(ctx, state, config)``; ``graph.build`` binds them to one ``Context``.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from blueprint.config.assets import Assets
from blueprint.graph.gates import OPEN_GATE_EVENT, gate_message
from blueprint.llm.gateway import InvalidStructuredOutput, Meter, ModelCallFailed, ModelGateway
from blueprint.storage.sessions import AttachmentSource

Update = dict[str, Any]


@dataclass(frozen=True)
class Context:
    calls: ModelGateway
    assets: Assets
    files: AttachmentSource | None = None

    async def structured_with_retry[T: BaseModel](
        self,
        meter: Meter,
        schema: type[T],
        prompt: Sequence[BaseMessage],
        check: Callable[[T], list[str]],
        config: RunnableConfig,
    ) -> tuple[T | None, list[str]]:
        """One structured call on the interview model plus one corrective retry (S7.2, S8.2,
        S9.2): the output and the problems ``check`` still finds in it (empty when usable)."""
        messages = list(prompt)
        out: T | None = None
        problems: list[str] = []
        for _attempt in range(2):
            try:
                out = await self.calls.structured(meter, "interview", schema, messages, config)
                problems = check(out)
            except InvalidStructuredOutput as invalid:
                problems = [str(invalid)]
            if not problems:
                break
            messages.append(
                HumanMessage(
                    "Your answer could not be used. Fix these and answer again:\n- "
                    + "\n- ".join(problems)
                )
            )
        return out, problems


def utc_now() -> str:
    """ISO 8601 UTC, to the second: the approval time a PRD version is frozen with (S2.12)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def invalid_output(message: str) -> dict[str, Any]:
    """The ``last_error`` for a model answer that could not be used; a retry may fix it."""
    return ModelCallFailed("invalid_output", message, retryable=True).info()


def broke_rules(what: str, problems: list[str], meter: Meter) -> Update:
    """The update for an answer that still broke its rules after the corrective retry."""
    message = f"{what} broke its rules: " + "; ".join(problems)
    return {"last_error": invalid_output(message), "tokens_used": meter.used}


async def ask(config: RunnableConfig, name: str, args: dict[str, Any], text: str) -> AIMessage:
    """A gate call made by the graph itself, streamed so its card opens (S5.6, S11.4); the
    returned message belongs in the node's update."""
    message, call = gate_message(name, args, text)
    await open_gate(config, message, call)
    return message


async def open_gate(config: RunnableConfig, message: AIMessage, call: dict[str, Any]) -> None:
    """Stream a gate tool call to the browser under its own ID, so its card opens."""
    await adispatch_custom_event(
        OPEN_GATE_EVENT,
        {"id": call["id"], "name": call["name"], "args": call["args"], "message_id": message.id},
        config=config,
    )
