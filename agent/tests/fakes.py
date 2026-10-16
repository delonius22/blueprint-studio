"""Scripted fake models for the graph seam (PRD Testing Decisions).

A ``ScriptedChatModel`` is a real ``ChatModel``: its OpenAI SDK client talks to an
in-memory Chat Completions endpoint that answers each request with the next entry
of its script and records what it was sent, so tests drive the real graph, the
real SDK calls and the real request and response conversion, and assert on state.
Script entries: an ``AIMessage`` for a chat call, a ``dict`` for a structured
output call, or an ``Exception`` for the endpoint to fail with (see ``_failure``).
"""

import json
import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx2
import openai
from langchain_core.messages import AIMessage, BaseMessage, convert_to_messages
from pydantic import BaseModel

from blueprint.models import ChatModel

ScriptEntry = AIMessage | dict[str, Any] | Exception


class ScriptExhausted(AssertionError):
    pass


class Call(BaseModel):
    messages: list[BaseMessage]
    tools: list[str]
    structured_method: str | None = None


class ProviderError(Exception):
    """An HTTP error from a provider; the fake endpoint answers with this status."""

    def __init__(self, status_code: int, retry_after: str | None = None) -> None:
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code
        headers = {"retry-after": retry_after} if retry_after else {}
        self.response = type("Response", (), {"headers": headers})()


class FakeTimeout(Exception):
    """The fake endpoint does not answer in time (the SDK raises APITimeoutError)."""


FakeTimeout.__name__ = "APITimeoutError"


class ScriptedChatModel(ChatModel):
    def __init__(self, name: str = "scripted", usage: tuple[int, int] | None = None) -> None:
        # When set, every response reports this (input, output) token usage, like a provider would.
        self.name = name
        self.usage = usage
        self._script: list[ScriptEntry] = []
        self._calls: list[Call] = []
        client = openai.AsyncOpenAI(
            base_url="http://scripted.test/v1",
            api_key="test-key",
            max_retries=0,
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(self._handle)),
        )
        super().__init__(client, name)

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

    def _next(self) -> ScriptEntry:
        if not self._script:
            raise ScriptExhausted(f"{self.name}: script exhausted")
        return self._script.pop(0)

    # --- the endpoint ------------------------------------------------------------------------

    async def _handle(self, request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        messages = convert_to_messages(body["messages"])
        method = _structured_method(body)
        tools = [] if method else [tool["function"]["name"] for tool in body.get("tools", [])]
        self._calls.append(Call(messages=messages, tools=tools, structured_method=method))
        entry = self._answer(messages, method, body)
        if isinstance(entry, Exception):
            return _failure(entry)
        if method is None and not isinstance(entry, AIMessage):
            raise AssertionError(f"{self.name}: expected a chat call, script has {entry!r}")
        if method is not None and not isinstance(entry, dict):
            raise AssertionError(f"{self.name}: expected a structured call, got {entry!r}")
        reply = entry if isinstance(entry, AIMessage) else _structured_reply(entry, method, body)
        # Like some OpenAI-compatible servers, every response carries the same completion ID.
        completion_id = "chatcmpl-scripted"
        usage = self._usage(reply)
        if body.get("stream"):
            include_usage = (body.get("stream_options") or {}).get("include_usage", False)
            events = _chunks(reply, completion_id, usage if include_usage else None)
            return httpx2.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content="".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n",
            )
        return httpx2.Response(200, json=_completion(reply, completion_id, usage))

    def _answer(self, messages: list[BaseMessage], method: str | None, body: dict[str, Any]) -> Any:
        return self._next()

    def _usage(self, reply: AIMessage) -> dict[str, int] | None:
        if reply.usage_metadata:
            tokens_in, tokens_out = (
                reply.usage_metadata["input_tokens"],
                reply.usage_metadata["output_tokens"],
            )
        elif self.usage is not None:
            tokens_in, tokens_out = self.usage
        else:
            return None
        return {
            "prompt_tokens": tokens_in,
            "completion_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
        }


class RoutedChatModel(ScriptedChatModel):
    """Answers structured calls with ``route(messages, schema_name)``: for calls made in
    parallel, where the order of a script would be arbitrary."""

    route: Callable[[list[BaseMessage], str], Any]

    @classmethod
    def answering(
        cls,
        route: Callable[[list[BaseMessage], str], Any],
        name: str = "routed",
        usage: tuple[int, int] | None = None,
    ) -> RoutedChatModel:
        model = cls(name=name, usage=usage)
        model.route = route
        return model

    def _answer(self, messages: list[BaseMessage], method: str | None, body: dict[str, Any]) -> Any:
        if method is None:
            raise AssertionError(f"{self.name}: unexpected chat call")
        return self.route(messages, _schema_name(body))


# --- wire format ---------------------------------------------------------------------------


def _structured_method(body: dict[str, Any]) -> str | None:
    if (body.get("response_format") or {}).get("type") == "json_schema":
        return "json_schema"
    if isinstance(body.get("tool_choice"), dict):
        return "function_calling"
    return None


def _schema_name(body: dict[str, Any]) -> str:
    if response_format := body.get("response_format"):
        return str(response_format["json_schema"]["name"])
    return str(body["tool_choice"]["function"]["name"])


def _structured_reply(entry: dict[str, Any], method: str | None, body: dict[str, Any]) -> AIMessage:
    if method == "json_schema":
        return AIMessage(content=json.dumps(entry))
    return tool_call(_schema_name(body), entry, "call_structured")


def _failure(error: Exception) -> httpx2.Response:
    """A scripted exception as the endpoint's answer: a timeout, or an HTTP error whose status
    is the exception's ``status_code`` (400, a rejected request, when it has none)."""
    if type(error).__name__ == "APITimeoutError":
        raise httpx2.ReadTimeout(str(error))
    status = getattr(error, "status_code", None) or 400
    headers = getattr(getattr(error, "response", None), "headers", None) or {}
    return httpx2.Response(
        status, headers=dict(headers), json={"error": {"message": str(error), "type": "error"}}
    )


def _tool_calls(reply: AIMessage) -> list[dict[str, Any]]:
    return [
        {
            "id": call["id"],
            "type": "function",
            "function": {"name": call["name"], "arguments": json.dumps(call["args"])},
        }
        for call in reply.tool_calls
    ]


def _completion(reply: AIMessage, completion_id: str, usage: dict[str, int] | None) -> Any:
    calls = _tool_calls(reply)
    message: dict[str, Any] = {"role": "assistant", "content": reply.text or None}
    if calls:
        message["tool_calls"] = calls
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "scripted",
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if calls else "stop",
            }
        ],
        "usage": usage,
    }


def _chunks(reply: AIMessage, completion_id: str, usage: dict[str, int] | None) -> Iterator[Any]:
    """The reply as an OpenAI-compatible stream: words, then each tool call's name and id,
    then its arguments, then the usage."""

    def event(delta: dict[str, Any], finish: str | None = None) -> dict[str, Any]:
        return {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "scripted",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }

    yield event({"role": "assistant", "content": ""})
    words = reply.text.split(" ") if reply.text else []
    for i, word in enumerate(words):
        yield event({"content": word if i == len(words) - 1 else word + " "})
    for i, call in enumerate(_tool_calls(reply)):
        yield event(
            {
                "tool_calls": [
                    {
                        "index": i,
                        "id": call["id"],
                        "type": "function",
                        "function": {"name": call["function"]["name"], "arguments": ""},
                    }
                ]
            }
        )
        yield event(
            {"tool_calls": [{"index": i, "function": {"arguments": call["function"]["arguments"]}}]}
        )
    yield event({}, "tool_calls" if reply.tool_calls else "stop")
    if usage is not None:
        yield {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "scripted",
            "choices": [],
            "usage": usage,
        }


def tool_call(name: str, args: dict[str, Any], call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def prd_out(
    groups: dict[str, list[str]], gap_features: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """A PRD v1.0 draft as the drafter model returns it: feature name -> FR IDs."""
    refs = {name: f"f{i + 1}" for i, name in enumerate(groups)}
    return {
        "problem_statement": "Long URLs are hard to share.",
        "goals": ["Short links that always redirect"],
        "users": ["Anonymous web users"],
        "features": [
            {
                "ref": refs[name],
                "name": name,
                "description": f"{name} description",
                "requirement_ids": ids,
            }
            for name, ids in groups.items()
        ],
        "scope": ["Creating and resolving short links"],
        "gap_features": [
            {"gap_id": gap, "feature_refs": [refs[n] for n in names]}
            for gap, names in (gap_features or {}).items()
        ],
    }
