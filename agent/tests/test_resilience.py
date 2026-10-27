"""T-19: resilience, token budget and structured logs (S13.1-S13.5, S1.5, NFR-6)."""

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from conftest import INTERVIEW_KEY, REVIEW_KEY, valid_env
from fakes import FakeTimeout, ProviderError, ScriptedChatModel
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from seam import GraphSeam

from blueprint.app import DownloadTimer, apply_tracing
from blueprint.config.settings import load_settings
from blueprint.llm.clients import RoleModels
from blueprint.llm.gateway import Meter, ModelGateway, estimate_tokens
from blueprint.utils import log


@pytest.fixture
def logs() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = log.configure(secrets=(INTERVIEW_KEY, REVIEW_KEY), stream=stream)
    yield stream
    logging.getLogger(log.LOGGER_NAME).removeHandler(handler)


def lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


# --- S13.1 retries and S13.2 state on failure ------------------------------------------------


async def test_429_5xx_and_timeouts_are_retried_with_backoff_and_retry_after() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            ProviderError(503), ProviderError(429, retry_after="7"), FakeTimeout("read timed out"),
            AIMessage("Who are the users?"),
        ),
        jitter=0.5,
    )  # fmt: skip
    await seam.send("Design a URL shortener")

    # full jitter from 1 s doubling (jitter fixed at 0.5), and at least Retry-After
    assert seam.sleeps == [0.5, 7.0, 2.0]
    state = await seam.state()
    assert state["messages"][-1].text == "Who are the users?"
    assert state["last_error"] is None


async def test_after_exhausted_retries_only_last_error_changes() -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(*[ProviderError(500)] * 4))
    await seam._ensure_session("session-1")
    before = await seam.state()

    await seam.send("Design a URL shortener")

    after = await seam.state()
    assert len(seam.interview.calls) == 4  # one call and 3 retries
    assert len(seam.sleeps) == 3
    assert after["last_error"] == {
        "code": "provider_error",
        "message": after["last_error"]["message"],
        "retryable": True,
    }
    changed = {
        k for k in after if k not in ("messages", "copilotkit") and after[k] != before.get(k)
    }
    assert changed == {"last_error"}
    assert [type(m) for m in after["messages"]] == [HumanMessage]  # no reply was written


async def test_a_non_retryable_error_is_not_retried() -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(ProviderError(401)))
    await seam.send("hi")
    error = (await seam.state())["last_error"]
    assert (error["code"], error["retryable"], seam.sleeps) == ("model_error", False, [])


async def test_retry_re_runs_the_last_user_turn_and_clears_the_error() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(*[ProviderError(502)] * 4, AIMessage("Back again."))
    )
    await seam.send("Design a URL shortener")
    assert (await seam.state())["last_error"]["retryable"] is True

    await seam.retry()

    state = await seam.state()
    assert state["last_error"] is None
    assert [m.text for m in state["messages"]] == ["Design a URL shortener", "Back again."]
    assert seam.interview.calls[-1].messages[-1].text == "Design a URL shortener"


async def test_a_run_with_last_error_set_and_nothing_new_makes_no_model_call() -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(*[ProviderError(500)] * 4))
    await seam.send("hi")
    calls = len(seam.interview.calls)
    resync: Any = {"messages": []}
    await seam.graph.ainvoke(resync, seam.config("session-1"))  # a page-load re-sync
    assert len(seam.interview.calls) == calls


# --- S13.3 token budget --------------------------------------------------------------------


async def test_tokens_are_counted_per_role_and_the_budget_stops_model_calls() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(AIMessage("one"), AIMessage("two"), usage=(600, 400)),
        token_budget=1500,
    )
    await seam.send("first")
    assert (await seam.state())["tokens_used"] == {"interview": 1000, "review": 0}
    await seam.send("second")
    assert (await seam.state())["tokens_used"] == {"interview": 2000, "review": 0}

    await seam.send("third")  # 2000 >= 1500: no model call is made

    state = await seam.state()
    assert seam.interview.remaining == 0 and len(seam.interview.calls) == 2
    assert state["last_error"]["code"] == "budget_exhausted"
    assert state["last_error"]["retryable"] is False


async def test_missing_usage_is_estimated_from_characters(logs: io.StringIO) -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(AIMessage("x" * 40)))
    await seam.send("hello")

    used = (await seam.state())["tokens_used"]["interview"]
    call = next(line for line in lines(logs) if line["event"] == "model_call")
    assert call["usage_estimated"] is True
    assert used == call["output_tokens"] > estimate_tokens(0, 40)  # prompt characters count too
    assert estimate_tokens(10, 3) == 4


# --- S13.4 structured output -----------------------------------------------------------------


class Answer(BaseModel):
    ok: bool


async def test_structured_output_falls_back_to_tool_calling_once_and_remembers_it() -> None:
    model = ScriptedChatModel.with_script(ProviderError(400), {"ok": True}, {"ok": True})
    gateway = ModelGateway(RoleModels(model, ScriptedChatModel()))
    meter = Meter("s", "critic", {"interview": 0, "review": 0}, 10_000)

    assert await gateway.structured(meter, "interview", Answer, [HumanMessage("?")]) == Answer(
        ok=True
    )
    assert await gateway.structured(meter, "interview", Answer, [HumanMessage("?")]) == Answer(
        ok=True
    )

    assert [c.structured_method for c in model.calls] == [
        "json_schema",
        "function_calling",
        "function_calling",
    ]


# --- S13.5 logs ------------------------------------------------------------------------------


async def test_model_calls_are_logged_as_json_with_role_latency_tokens_and_ttft(
    logs: io.StringIO,
) -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(AIMessage("Who are the users?"), usage=(120, 30))
    )
    await seam.send("Design a URL shortener")

    call = next(line for line in lines(logs) if line["event"] == "model_call")
    assert {"ts", "level", "session_id", "node", "event"} <= set(call)
    assert (call["session_id"], call["node"], call["role"]) == (
        "session-1",
        "interviewer",
        "interview",
    )
    assert (call["input_tokens"], call["output_tokens"]) == (120, 30)
    assert isinstance(call["latency_ms"], int) and isinstance(call["ttft_ms"], int)
    assert "Design a URL shortener" not in logs.getvalue()  # prompts are never logged


async def test_download_requests_log_export_ms(logs: io.StringIO) -> None:
    async def download(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"file"})

    app = DownloadTimer(download)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://a"
    ) as http:
        await http.get("/api/sessions/s-1/downloads/context.md")
        await http.get("/api/sessions/s-1")
    entries = [line for line in lines(logs) if line["event"] == "download"]
    assert len(entries) == 1
    assert (entries[0]["session_id"], entries[0]["kind"], entries[0]["status"]) == (
        "s-1",
        "context.md",
        200,
    )
    assert isinstance(entries[0]["export_ms"], int)


def test_langsmith_tracing_toggles_by_variable() -> None:
    environ: dict[str, str] = {}
    apply_tracing(load_settings(valid_env() | {"LANGSMITH_TRACING": "yes"}), environ)
    assert environ["LANGSMITH_TRACING"] == "true"
    apply_tracing(load_settings(valid_env()), environ)
    assert environ["LANGSMITH_TRACING"] == "false"


# --- S1.5, NFR-6: keys never reach the logs ---------------------------------------------------


async def test_key_values_never_appear_in_logs_even_in_provider_errors(logs: io.StringIO) -> None:
    leaky = ProviderError(401)
    leaky.args = (f"Incorrect API key provided: {INTERVIEW_KEY}. Also {REVIEW_KEY}.",)
    seam = GraphSeam(ScriptedChatModel.with_script(leaky, AIMessage("ok"), usage=(1, 1)))
    await seam.send("hi")
    error = (await seam.state())["last_error"]
    assert error["code"] == "model_error" and "HTTP 401" in error["message"]
    assert INTERVIEW_KEY not in json.dumps(error)  # last_error reaches the browser
    await seam.retry()
    log.log_event("startup", message=f"settings: {load_settings(valid_env())!r}")

    output = logs.getvalue()
    assert "[redacted]" in output
    assert INTERVIEW_KEY not in output and REVIEW_KEY not in output
