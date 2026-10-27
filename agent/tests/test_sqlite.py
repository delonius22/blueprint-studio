"""Local mode: the same session API over a SQLite file, with no database server or Docker."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from conftest import valid_env
from fakes import ScriptedChatModel
from fastapi import FastAPI
from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from service import client, event_types, post_run, run_input, streamed_text, user

from blueprint.app import assemble_from, prepare
from blueprint.config.settings import ConfigError, load_settings
from blueprint.llm.clients import RoleModels
from blueprint.storage.sqlite import open_sqlite, sqlite_path


@asynccontextmanager
async def local_service(
    path: Path, interview: ScriptedChatModel | None = None
) -> AsyncIterator[tuple[FastAPI, AsyncSqliteSaver]]:
    """One agent process in local mode: the real app over ``path``, with scripted models."""
    models = RoleModels(interview or ScriptedChatModel(), ScriptedChatModel())
    env = valid_env() | {"DATABASE_URL": f"sqlite:///{path}"}
    runtime = await prepare(env, build=lambda _: models)
    async with open_sqlite(str(path)) as (checkpointer, store):
        yield assemble_from(runtime, checkpointer, store), checkpointer


def test_the_database_url_picks_the_mode() -> None:
    assert sqlite_path("sqlite:///blueprint.db") == "blueprint.db"
    assert sqlite_path("sqlite:////var/data/blueprint.db") == "/var/data/blueprint.db"
    assert sqlite_path("sqlite:///C:/data/blueprint.db") == "C:/data/blueprint.db"
    assert sqlite_path("postgresql://blueprint:secret@db:5432/blueprint") is None


@pytest.mark.parametrize("url", ["sqlite:///blueprint.db", "postgres://u:p@h/d"])
def test_sqlite_and_postgres_urls_are_accepted(url: str) -> None:
    settings = load_settings(valid_env() | {"DATABASE_URL": url})
    assert settings.database_url.get_secret_value() == url


def test_any_other_database_url_is_refused_without_echoing_it() -> None:
    with pytest.raises(ConfigError) as refused:
        load_settings(valid_env() | {"DATABASE_URL": "mysql://user:hunter2@host/db"})
    assert "DATABASE_URL must start with postgresql:// (server) or sqlite:/// (local)" in str(
        refused.value
    )
    assert "hunter2" not in str(refused.value)


async def test_list_is_newest_first_and_keyset_paginated(tmp_path: Path) -> None:
    async with local_service(tmp_path / "blueprint.db") as (app, _), client(app) as http:
        ids = [
            (await http.post("/api/sessions", json={"name": f"s{i}"})).json()["id"]
            for i in range(7)
        ]
        seen: list[str] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"limit": 3} | ({"cursor": cursor} if cursor else {})
            page = (await http.get("/api/sessions", params=params)).json()
            assert len(page["items"]) <= 3
            seen += [item["id"] for item in page["items"]]
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert seen == list(reversed(ids))

        await http.patch(f"/api/sessions/{ids[0]}", json={"name": "renamed"})
        top = (await http.get("/api/sessions", params={"limit": 1})).json()["items"][0]
        assert (top["id"], top["name"], top["stage"]) == (ids[0], "renamed", "interview")
        assert top["created_at"].endswith("Z") and top["updated_at"] > top["created_at"]


async def test_get_rename_and_delete_removes_the_checkpoint(tmp_path: Path) -> None:
    script = ScriptedChatModel.with_script(AIMessage("Who are the users?"))
    async with local_service(tmp_path / "blueprint.db", script) as (app, saver):
        async with client(app) as http:
            session_id = (await http.post("/api/sessions", json={"name": "old"})).json()["id"]
        await post_run(app, run_input(session_id, [user("Design a URL shortener")]))
        config: Any = {"configurable": {"thread_id": session_id}}
        assert await saver.aget_tuple(config) is not None
        async with client(app) as http:
            renamed = await http.patch(f"/api/sessions/{session_id}", json={"name": " new "})
            assert renamed.status_code == 200 and renamed.json()["name"] == "new"
            assert (await http.get("/api/sessions/missing")).status_code == 404
            assert (await http.delete(f"/api/sessions/{session_id}")).status_code == 204
            assert (await http.get(f"/api/sessions/{session_id}")).status_code == 404
        assert await saver.aget_tuple(config) is None


async def test_a_session_survives_a_restart_and_runs_update_the_list(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "blueprint.db"  # the folder is created on first start
    script = ScriptedChatModel.with_script(AIMessage("Who are the users?"))
    async with local_service(path, script) as (app, _):
        async with client(app) as http:
            first = (await http.post("/api/sessions", json={"name": "first"})).json()
            second = (await http.post("/api/sessions", json={"name": "second"})).json()
        events = await post_run(app, run_input(first["id"], [user("Design a URL shortener")]))
        assert streamed_text(events) == "Who are the users?"
        async with client(app) as http:
            items = (await http.get("/api/sessions")).json()["items"]
            before = (await http.get(f"/api/sessions/{first['id']}")).json()
        assert [i["id"] for i in items] == [first["id"], second["id"]]
        assert items[0]["updated_at"] > first["updated_at"]
        refused = await post_run(app, run_input("no-such-session", [user("hello")]))
        assert event_types(refused) == ["RUN_ERROR"]

    # a new process over the same file, with models that must not be called
    async with local_service(path, ScriptedChatModel.with_script()) as (app, _):
        async with client(app) as http:
            assert (await http.get(f"/api/sessions/{first['id']}")).json() == before
        events = await post_run(app, run_input(first["id"], []))
        snapshot = next(e for e in events if e["type"] == "MESSAGES_SNAPSHOT")
        assert [m["content"] for m in snapshot["messages"]] == [
            "Design a URL shortener",
            "Who are the users?",
        ]
        assert "TEXT_MESSAGE_CONTENT" not in event_types(events)
