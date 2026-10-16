"""The one place the app talks to models (SPECS S1.6, S1.8 as overridden by MODEL-CONNECTION.md).

Each role gets an ``openai.AsyncOpenAI`` client for its OpenAI-compatible Chat
Completions endpoint. This module builds the clients, turns the graph's LangChain
messages into Chat Completions requests and turns the responses back into
``AIMessage`` objects. No other module imports the OpenAI SDK.
"""

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

import openai
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    convert_to_openai_messages,
    message_chunk_to_message,
)
from langchain_core.messages.ai import UsageMetadata
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel

from blueprint.settings import Role, RoleConfig, Settings

ROLES: tuple[Role, ...] = ("interview", "review")

# Requests time out so that S13.1 can retry them; the client's own retries are off so that
# S13.1 (blueprint.llm) is the only retry policy.
REQUEST_TIMEOUT_S = 120.0

# S13.4: JSON-schema mode first, then tool calling.
STRUCTURED_METHODS = ("json_schema", "function_calling")


class ChatModel:
    """One role's endpoint: an OpenAI SDK client and the model name it asks for."""

    def __init__(self, client: openai.AsyncOpenAI, model: str) -> None:
        self.client = client
        self.model = model


@dataclass(frozen=True)
class RoleModels:
    interview: ChatModel
    review: ChatModel

    def for_role(self, role: Role) -> ChatModel:
        return self.interview if role == "interview" else self.review


def build_chat_model(config: RoleConfig) -> ChatModel:
    client = openai.AsyncOpenAI(
        base_url=config.base_url,
        # A keyless local server still needs a non-empty bearer value.
        api_key=config.api_key.get_secret_value() or "not-needed",
        max_retries=0,
        timeout=REQUEST_TIMEOUT_S,
    )
    return ChatModel(client, config.model_name)


def build_models(settings: Settings) -> RoleModels:
    return RoleModels(
        interview=build_chat_model(settings.interview),
        review=build_chat_model(settings.review),
    )


def _identity(config: RoleConfig) -> tuple[str, str]:
    return (config.base_url.rstrip("/"), config.model_name)


def review_model_distinct(settings: Settings) -> bool:
    """True when the review model's (base URL, model name) differs from the interview model's."""
    return _identity(settings.review) != _identity(settings.interview)


# --- requests --------------------------------------------------------------------------------


def openai_tool(tool: Any) -> dict[str, Any]:
    """A Chat Completions tool from an OpenAI-format tool, a CopilotKit action or a model class."""
    if isinstance(tool, dict) and "function" in tool:
        return tool
    if isinstance(tool, dict):
        function = {key: tool[key] for key in ("name", "description", "parameters") if key in tool}
        function.setdefault("parameters", {"type": "object", "properties": {}})
        return {"type": "function", "function": function}
    if isinstance(tool, type) and issubclass(tool, BaseModel):
        function = {"name": tool.__name__, "parameters": tool.model_json_schema()}
        if tool.__doc__:
            function["description"] = tool.__doc__.strip()
        return {"type": "function", "function": function}
    raise TypeError(f"not a tool: {tool!r}")


def structured_request(schema: type[BaseModel], method: str) -> dict[str, Any]:
    """Request fields that ask for ``schema``: a strict JSON schema, or one forced tool call."""
    function = openai.pydantic_function_tool(schema)["function"]
    if method == "json_schema":
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": function["name"],
                    "schema": function["parameters"],
                    "strict": True,
                },
            }
        }
    tool = {"name": function["name"], "parameters": function["parameters"]}
    if "description" in function:
        tool["description"] = function["description"]
    return {
        "tools": [{"type": "function", "function": tool}],
        "tool_choice": {"type": "function", "function": {"name": tool["name"]}},
    }


def structured_value[T: BaseModel](schema: type[T], message: AIMessage, method: str) -> T:
    """The answer to a ``structured_request``; raises ValueError when it does not fit."""
    if method == "json_schema":
        return schema.model_validate_json(message.text)
    calls = [call for call in message.tool_calls if call["name"] == schema.__name__]
    if not calls:
        raise ValueError(f"the model did not call {schema.__name__}")
    return schema.model_validate(calls[0]["args"])


def _request(
    model: ChatModel, messages: Sequence[BaseMessage], tools: Sequence[Any], extra: dict[str, Any]
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model.model,
        "messages": convert_to_openai_messages(list(messages)),
    }
    if tools:
        request["tools"] = [openai_tool(tool) for tool in tools]
    return request | extra


# --- responses -------------------------------------------------------------------------------


def _usage(usage: CompletionUsage | None) -> UsageMetadata | None:
    if usage is None:
        return None
    return {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


def _message(completion: ChatCompletion) -> AIMessage:
    reply = completion.choices[0].message
    tool_calls: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for call in reply.tool_calls or []:
        if call.type != "function":
            continue
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            invalid.append(
                {
                    "name": call.function.name,
                    "args": call.function.arguments,
                    "id": call.id,
                    "error": str(exc),
                }
            )
            continue
        tool_calls.append({"name": call.function.name, "args": args, "id": call.id})
    return AIMessage(
        content=reply.content or "",
        tool_calls=tool_calls,
        invalid_tool_calls=invalid,
        usage_metadata=_usage(completion.usage),
    )


def _chunk(event: ChatCompletionChunk, message_id: str) -> AIMessageChunk:
    usage = _usage(event.usage)
    if not event.choices:
        return AIMessageChunk(content="", id=message_id, usage_metadata=usage)
    delta = event.choices[0].delta
    tool_chunks = [
        {
            "name": call.function.name if call.function else None,
            "args": call.function.arguments if call.function else None,
            "id": call.id,
            "index": call.index,
        }
        for call in delta.tool_calls or []
    ]
    return AIMessageChunk(
        content=delta.content or "",
        id=message_id,
        tool_call_chunks=tool_chunks,  # type: ignore[arg-type]
        usage_metadata=usage,
    )


# --- calls -----------------------------------------------------------------------------------


async def complete(
    model: ChatModel,
    messages: Sequence[BaseMessage],
    tools: Sequence[Any] = (),
    **extra: Any,
) -> AIMessage:
    """One Chat Completions call; ``extra`` adds request fields such as ``response_format``."""
    completion = await model.client.chat.completions.create(
        **_request(model, messages, tools, extra)
    )
    return _message(completion)


async def stream(
    model: ChatModel,
    messages: Sequence[BaseMessage],
    tools: Sequence[Any],
    on_chunk: Callable[[AIMessageChunk], Awaitable[None]],
    message_id: str,
) -> AIMessage:
    """One streamed Chat Completions call: each chunk goes to ``on_chunk``; returns the whole reply.

    The reply is named ``message_id``, never the completion ID: some OpenAI-compatible servers
    reuse one completion ID, and two messages with one ID would replace each other in state.
    """
    request = _request(model, messages, tools, {})
    events = await model.client.chat.completions.create(
        **request, stream=True, stream_options={"include_usage": True}
    )
    total: AIMessageChunk | None = None
    async for event in events:
        chunk = _chunk(event, message_id)
        await on_chunk(chunk)
        total = chunk if total is None else total + chunk
    if total is None:
        raise ValueError("the model sent an empty stream")
    message = message_chunk_to_message(total)
    assert isinstance(message, AIMessage)
    return message
