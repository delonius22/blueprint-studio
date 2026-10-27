"""The service seam for API tests: the real app over Postgres, with scripted fake models."""

import json
import uuid
from typing import Any

import httpx
from conftest import valid_env
from fakes import ScriptedChatModel
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

from blueprint.app import assemble, prepare
from blueprint.llm.clients import RoleModels


async def build_service(
    pool: AsyncConnectionPool[Any],
    interview: ScriptedChatModel | None = None,
    review: ScriptedChatModel | None = None,
    **env: str,
) -> FastAPI:
    models = RoleModels(interview or ScriptedChatModel(), review or ScriptedChatModel())
    runtime = await prepare(valid_env() | env, build=lambda _: models)
    return await assemble(runtime, pool)


def client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://agent")


def run_input(
    thread_id: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "runId": str(uuid.uuid4()),
        "state": state or {},
        "messages": messages,
        "tools": tools or [],
        "context": [],
        "forwardedProps": {},
    }


def user(text: str, message_id: str | None = None) -> dict[str, Any]:
    return {"id": message_id or str(uuid.uuid4()), "role": "user", "content": text}


async def post_run(app: FastAPI, body: dict[str, Any]) -> list[dict[str, Any]]:
    """POST an AG-UI run to /agent and return its events."""
    async with client(app) as http:
        response = await http.post("/agent", json=body, headers={"accept": "text/event-stream"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def event_types(events: list[dict[str, Any]]) -> list[str]:
    return [e["type"] for e in events]


def streamed_text(events: list[dict[str, Any]]) -> str:
    return "".join(e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
