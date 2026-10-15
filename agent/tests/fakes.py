"""Scripted fake chat models for the graph seam (PRD Testing Decisions).

A ``ScriptedChatModel`` answers each call with the next entry of its script and
records what it was sent, so tests drive the real graph and assert on state.
Script entries: an ``AIMessage`` for a chat call, a ``dict`` for a structured
output call, or an ``Exception`` to raise.
"""

import json
from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from pydantic import BaseModel, PrivateAttr

ScriptEntry = AIMessage | dict[str, Any] | Exception


class ScriptExhausted(AssertionError):
    pass


class Call(BaseModel):
    messages: list[BaseMessage]
    tools: list[str]
    structured_method: str | None = None


class ScriptedChatModel(BaseChatModel):
    name: str = "scripted"
    # When set, every response reports this (input, output) token usage, like a provider would.
    usage: tuple[int, int] | None = None
    _script: list[ScriptEntry] = PrivateAttr(default_factory=list)
    _calls: list[Call] = PrivateAttr(default_factory=list)

    @classmethod
    def with_script(
        cls, *entries: ScriptEntry, name: str = "scripted", usage: tuple[int, int] | None = None
    ) -> ScriptedChatModel:
        model = cls(name=name, usage=usage)
        model._script = list(entries)
        return model

    @property
    def calls(self) -> list[Call]:
        return self._calls

    @property
    def remaining(self) -> int:
        return len(self._script)

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def _next(self) -> ScriptEntry:
        if not self._script:
            raise ScriptExhausted(f"{self.name}: script exhausted")
        entry = self._script.pop(0)
        if isinstance(entry, Exception):
            raise entry
        return entry

    def _record(self, messages: Sequence[BaseMessage], kwargs: dict[str, Any]) -> AIMessage:
        tools = [_tool_name(tool) for tool in kwargs.get("tools", [])]
        self._calls.append(Call(messages=list(messages), tools=tools))
        entry = self._next()
        if not isinstance(entry, AIMessage):
            raise AssertionError(f"{self.name}: expected a chat call, script has {entry!r}")
        return self._with_usage(entry)

    def _with_usage(self, message: AIMessage) -> AIMessage:
        if self.usage is None or message.usage_metadata:
            return message
        tokens_in, tokens_out = self.usage
        return message.model_copy(
            update={
                "usage_metadata": {
                    "input_tokens": tokens_in,
                    "output_tokens": tokens_out,
                    "total_tokens": tokens_in + tokens_out,
                }
            }
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._record(messages, kwargs))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        reply = self._record(messages, kwargs)
        text = reply.text
        words = text.split(" ")
        for i, word in enumerate(words):
            piece = word if i == len(words) - 1 else word + " "
            yield ChatGenerationChunk(message=AIMessageChunk(content=piece, id=reply.id))
        if reply.usage_metadata:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content="", id=reply.id, usage_metadata=reply.usage_metadata)
            )
        # Like OpenAI-compatible servers: the name and id first, then the arguments.
        for i, call in enumerate(reply.tool_calls):
            for part in (
                {"name": call["name"], "args": "", "id": call["id"], "index": i},
                {"name": None, "args": json.dumps(call["args"]), "id": None, "index": i},
            ):
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content="", tool_call_chunks=[part], id=reply.id)  # type: ignore[list-item]
                )

    def bind_tools(
        self, tools: Sequence[Any], **kwargs: Any
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self.bind(tools=list(tools), **kwargs)

    def with_structured_output(  # type: ignore[override]
        self,
        schema: type[BaseModel],
        *,
        method: str = "json_schema",
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, Any]:
        """Like LangChain: with include_raw, parse failures come back as parsing_error."""

        def answer(value: LanguageModelInput, config: RunnableConfig | None = None) -> Any:
            messages = value if isinstance(value, list) else []
            self._calls.append(Call(messages=messages, tools=[], structured_method=method))
            entry = self._next()
            if not isinstance(entry, dict):
                raise AssertionError(f"{self.name}: expected a structured call, got {entry!r}")
            raw = self._with_usage(AIMessage(content=json.dumps(entry)))
            try:
                parsed = schema.model_validate(entry)
            except Exception as exc:
                if not include_raw:
                    raise
                return {"raw": raw, "parsed": None, "parsing_error": exc}
            return {"raw": raw, "parsed": parsed, "parsing_error": None} if include_raw else parsed

        return RunnableLambda(answer)


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name") or tool.get("function", {}).get("name"))
    return str(getattr(tool, "name", None) or getattr(tool, "__name__", tool))


def tool_call(name: str, args: dict[str, Any], call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


class ProviderError(Exception):
    """An HTTP error from a provider, shaped like the OpenAI SDK's APIStatusError."""

    def __init__(self, status_code: int, retry_after: str | None = None) -> None:
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code
        headers = {"retry-after": retry_after} if retry_after else {}
        self.response = type("Response", (), {"headers": headers})()


class FakeTimeout(Exception):
    """Shaped like openai.APITimeoutError."""


FakeTimeout.__name__ = "APITimeoutError"


class RoutedChatModel(ScriptedChatModel):
    """Answers structured calls with ``route(messages, schema)``: for calls made in parallel,
    where the order of a script would be arbitrary."""

    route: Any = None

    @classmethod
    def answering(
        cls, route: Any, name: str = "routed", usage: tuple[int, int] | None = None
    ) -> RoutedChatModel:
        model = cls(name=name, usage=usage)
        model.route = route
        return model

    def _next(self) -> ScriptEntry:  # pragma: no cover - structured calls use route()
        raise AssertionError(f"{self.name}: unexpected chat call")

    def with_structured_output(  # type: ignore[override]
        self,
        schema: type[BaseModel],
        *,
        method: str = "json_schema",
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, Any]:
        def answer(value: LanguageModelInput, config: RunnableConfig | None = None) -> Any:
            messages = value if isinstance(value, list) else []
            self._calls.append(Call(messages=messages, tools=[], structured_method=method))
            entry = self.route(messages, schema)
            if isinstance(entry, Exception):
                raise entry
            raw = self._with_usage(AIMessage(content=json.dumps(entry)))
            parsed = schema.model_validate(entry)
            return {"raw": raw, "parsed": parsed, "parsing_error": None} if include_raw else parsed

        return RunnableLambda(answer)
