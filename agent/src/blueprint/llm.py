"""Every model call the graph makes goes through the ModelGateway (SPECS S13.1-S13.5).

- Budget (S13.3): before a call, if both roles together have used ``token_budget``
  tokens, the call is not made and fails with ``budget_exhausted``.
- Retries (S13.1): HTTP 429, 5xx and timeouts are retried up to 3 times with
  exponential backoff from 1 s, full jitter, and at least ``Retry-After``.
- Usage (S13.3): each response's tokens are added to its role; when a response
  carries no usage, it is estimated as (prompt + completion characters) / 4.
- Structured output (S13.4): JSON-schema mode first; if the provider rejects it,
  tool calling once; the working mode is remembered per model for the process.

Provider errors are recognised by their shape (``status_code``, ``response``,
timeout class names) so that no module but the factory touches a provider SDK.
"""

import asyncio
import json
import math
import random
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from functools import partial
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, message_chunk_to_message
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from blueprint.domain import ErrorInfo
from blueprint.log import log_event
from blueprint.models import RoleModels
from blueprint.settings import Role

MAX_RETRIES = 3
BASE_DELAY_S = 1.0
STRUCTURED_METHODS = ("json_schema", "function_calling")


class ModelCallFailed(Exception):
    """A model call could not be completed; becomes the session's ``last_error`` (S13.2)."""

    def __init__(self, code: str, message: str, retryable: bool, status: int | None = None) -> None:
        super().__init__(message)
        self.code, self.message, self.retryable, self.status = code, message, retryable, status

    def info(self) -> dict[str, Any]:
        return ErrorInfo(
            code=self.code, message=self.message, retryable=self.retryable
        ).model_dump()


class InvalidStructuredOutput(Exception):
    """The model answered, but not in the requested schema."""


@dataclass
class Meter:
    """Token use for one node run: starts from the state and is written back on success."""

    session_id: str
    node: str
    used: dict[str, int]
    budget: int

    @classmethod
    def for_node(cls, state: Any, node: str) -> Meter:
        used = {"interview": 0, "review": 0} | dict(state.get("tokens_used") or {})
        return cls(
            str(state.get("session_id", "")), node, used, int(state.get("token_budget") or 0)
        )

    def exhausted(self) -> bool:
        return sum(self.used.values()) >= self.budget


def _status(exc: BaseException) -> int | None:
    status = getattr(exc, "status_code", None)
    return status if isinstance(status, int) else None


def classify(exc: BaseException) -> str | None:
    """S13.1: the retryable failures; None for anything else."""
    status = _status(exc)
    if status == 429:
        return "rate_limited"
    if status is not None and status >= 500:
        return "provider_error"
    if isinstance(exc, TimeoutError) or "Timeout" in type(exc).__name__:
        return "timeout"
    return None


def retry_after(exc: BaseException) -> float | None:
    """Seconds from a Retry-After header (delta-seconds or HTTP date), if the error has one."""
    headers = getattr(getattr(exc, "response", None), "headers", None) or {}
    value = headers.get("retry-after") if hasattr(headers, "get") else None
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
        except TypeError, ValueError:
            return None


def estimate_tokens(prompt_chars: int, completion_chars: int) -> int:
    return math.ceil((prompt_chars + completion_chars) / 4)


def _chars(messages: Sequence[BaseMessage]) -> int:
    return sum(len(m.text) for m in messages)


def _completion_chars(message: AIMessage) -> int:
    return len(message.text) + sum(
        len(json.dumps(c["args"])) + len(c["name"]) for c in message.tool_calls
    )


@dataclass
class ModelGateway:
    models: RoleModels
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    jitter: Callable[[], float] = random.random
    _modes: dict[int, str] = field(default_factory=dict)

    async def _attempts(
        self, meter: Meter, role: Role, call: Callable[[], Awaitable[Any]]
    ) -> tuple[Any, float, int]:
        """Run ``call`` with the budget check and S13.1 retries; return (result, latency, attempt)."""
        if meter.exhausted():
            log_event("budget_exhausted", session_id=meter.session_id, node=meter.node, role=role)
            raise ModelCallFailed(
                "budget_exhausted",
                "This session has used its whole token budget, so no further model calls are made.",
                retryable=False,
            )
        for attempt in range(MAX_RETRIES + 1):
            start = time.monotonic()
            try:
                return await call(), start, attempt
            except Exception as exc:
                kind = classify(exc)
                if kind is None:
                    log_event(
                        "model_error",
                        session_id=meter.session_id,
                        node=meter.node,
                        role=role,
                        code="model_error",
                        status=_status(exc),
                        message=f"{type(exc).__name__}: {exc}",
                    )
                    # The provider's own text stays in the (redacted) log: it can quote a key.
                    status = _status(exc)
                    detail = f"HTTP {status}" if status else type(exc).__name__
                    raise ModelCallFailed(
                        "model_error",
                        f"The {role} model could not answer ({detail}).",
                        retryable=False,
                        status=status,
                    ) from exc
                if attempt == MAX_RETRIES:
                    log_event(
                        "model_retries_exhausted",
                        session_id=meter.session_id,
                        node=meter.node,
                        role=role,
                        code=kind,
                        attempt=attempt,
                    )
                    raise ModelCallFailed(
                        kind,
                        f"The {role} model is not responding ({kind.replace('_', ' ')}) after "
                        f"{MAX_RETRIES} retries. Try again in a moment.",
                        retryable=True,
                        status=_status(exc),
                    ) from exc
                delay = max(self.jitter() * BASE_DELAY_S * 2**attempt, retry_after(exc) or 0.0)
                log_event(
                    "model_retry",
                    session_id=meter.session_id,
                    node=meter.node,
                    role=role,
                    code=kind,
                    attempt=attempt + 1,
                )
                await self.sleep(delay)
        raise AssertionError("unreachable")

    def _account(
        self,
        meter: Meter,
        role: Role,
        raw: AIMessage | None,
        prompt_chars: int,
        latency_ms: int,
        attempt: int,
        ttft_ms: int | None = None,
    ) -> None:
        usage = raw.usage_metadata if raw is not None else None
        estimated = not usage
        if usage:
            tokens_in, tokens_out = usage["input_tokens"], usage["output_tokens"]
        else:
            tokens_in, tokens_out = (
                0,
                estimate_tokens(prompt_chars, _completion_chars(raw) if raw else 0),
            )
        meter.used[role] = meter.used.get(role, 0) + tokens_in + tokens_out
        log_event(
            "model_call",
            session_id=meter.session_id,
            node=meter.node,
            role=role,
            latency_ms=latency_ms,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            usage_estimated=estimated or None,
            attempt=attempt,
            ttft_ms=ttft_ms,
        )

    async def chat(
        self,
        meter: Meter,
        role: Role,
        messages: Sequence[BaseMessage],
        config: RunnableConfig | None = None,
        tools: Sequence[Any] = (),
        measure_ttft: bool = False,
    ) -> AIMessage:
        model = self.models.for_role(role)
        runnable: Any = model.bind_tools(list(tools)) if tools else model
        first: list[float] = []

        async def streamed() -> AIMessage:
            """Stream the reply (so time to first token is measured) and assemble it."""
            first.clear()
            total: AIMessageChunk | None = None
            async for chunk in runnable.astream(list(messages), config):
                if not first:
                    first.append(time.monotonic())
                total = chunk if total is None else total + chunk
            assert total is not None
            message = message_chunk_to_message(total)
            assert isinstance(message, AIMessage)
            return message

        call = streamed if measure_ttft else partial(runnable.ainvoke, list(messages), config)
        reply, start, attempt = await self._attempts(meter, role, call)
        assert isinstance(reply, AIMessage)
        now = time.monotonic()
        ttft = round((first[0] - start) * 1000) if measure_ttft and first else None
        self._account(
            meter,
            role,
            reply,
            _chars(messages) + len(json.dumps(list(tools), default=str)),
            round((now - start) * 1000),
            attempt,
            ttft,
        )
        return reply

    async def structured[T: BaseModel](
        self,
        meter: Meter,
        role: Role,
        schema: type[T],
        messages: Sequence[BaseMessage],
        config: RunnableConfig | None = None,
    ) -> T:
        model = self.models.for_role(role)
        cached = self._modes.get(id(model))
        methods = (cached,) if cached else STRUCTURED_METHODS
        for index, method in enumerate(methods):
            runnable: Any = model.with_structured_output(schema, method=method, include_raw=True)
            try:
                out, start, attempt = await self._attempts(
                    meter, role, partial(runnable.ainvoke, list(messages), config)
                )
            except ModelCallFailed as failure:
                rejected = failure.code == "model_error" and failure.status in (400, 404, 422, None)
                if rejected and index + 1 < len(methods):
                    continue  # S13.4: the provider rejected JSON-schema mode; try tool calling once
                raise
            self._modes[id(model)] = method
            raw = out.get("raw") if isinstance(out, dict) else None
            self._account(
                meter,
                role,
                raw if isinstance(raw, AIMessage) else None,
                _chars(messages),
                round((time.monotonic() - start) * 1000),
                attempt,
            )
            if (
                not isinstance(out, dict)
                or out.get("parsing_error") is not None
                or out.get("parsed") is None
            ):
                problem = out.get("parsing_error") if isinstance(out, dict) else out
                raise InvalidStructuredOutput(
                    f"the {role} model's answer did not match the schema: {problem}"
                )
            return schema.model_validate(out["parsed"])
        raise AssertionError("unreachable")
