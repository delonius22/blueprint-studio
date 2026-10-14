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
    _script: list[ScriptEntry] = PrivateAttr(default_factory=list)
    _calls: list[Call] = PrivateAttr(default_factory=list)

    @classmethod
    def with_script(cls, *entries: ScriptEntry, name: str = "scripted") -> ScriptedChatModel:
        model = cls(name=name)
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
        return entry

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
        self, schema: type[BaseModel], *, method: str = "json_schema", **kwargs: Any
    ) -> Runnable[LanguageModelInput, BaseModel]:
        def answer(value: LanguageModelInput, config: RunnableConfig | None = None) -> BaseModel:
            messages = value if isinstance(value, list) else []
            self._calls.append(Call(messages=messages, tools=[], structured_method=method))
            entry = self._next()
            if not isinstance(entry, dict):
                raise AssertionError(f"{self.name}: expected a structured call, got {entry!r}")
            return schema.model_validate(entry)

        return RunnableLambda(answer)


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name") or tool.get("function", {}).get("name"))
    return str(getattr(tool, "name", None) or getattr(tool, "__name__", tool))


def tool_call(name: str, args: dict[str, Any], call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])
