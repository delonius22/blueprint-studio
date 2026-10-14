"""T-02: sessions — create, list, resume, rename, delete (S2.1-S2.3, S3, S4.2, NFR-3)."""

import json
from typing import Any

import pytest
from conftest import open_pool
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from service import build_service, client, event_types, post_run, run_input, streamed_text, user

from blueprint.domain import STAGES, Design
from blueprint.state import SESSION_FIELDS, DesignState

S2_2_FIELDS = {
    "session_id", "stage", "current_step", "confirmed_steps", "design", "agent_design",
    "critiques", "scorecard", "gaps", "review_model_distinct", "prd_draft", "prd_versions",
    "proposed_changes", "seams", "tickets", "tickets_approved_at", "id_counters", "tokens_used",
    "token_budget", "last_error",
}  # fmt: skip


def assert_error(response: Any, status: int, code: str | None = None) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
    assert body["error"]["message"]
    if code:
        assert body["error"]["code"] == code


# --- S2.1-S2.3 and S3.1 create ---------------------------------------------------------------


def test_design_state_extends_copilotkit_state_with_every_s2_2_field() -> None:
    from copilotkit import CopilotKitState

    assert CopilotKitState in DesignState.__orig_bases__
    assert {"messages", "copilotkit"} <= set(DesignState.__annotations__)
    assert set(SESSION_FIELDS) == S2_2_FIELDS
    assert STAGES == (
        "interview", "design_review", "gap_resolution", "prd_draft", "prd_signoff",
        "spec_synthesis", "seam_gate", "change_review", "ticket_breakdown", "ticket_gate",
        "complete",
    )  # fmt: skip


async def test_create_returns_201_and_initial_state(pool: AsyncConnectionPool[Any]) -> None:
    app = await build_service(pool, SESSION_TOKEN_BUDGET="12345")
    async with client(app) as http:
        created = await http.post("/api/sessions", json={"name": "  URL shortener  "})
        assert created.status_code == 201
        body = created.json()
        assert set(body) == {"id", "name", "stage", "current_step", "created_at", "updated_at"}
        assert (body["name"], body["stage"], body["current_step"]) == (
            "URL shortener",
            "interview",
            1,
        )

        state = (await http.get(f"/api/sessions/{body['id']}")).json()["state"]
    assert set(state) == S2_2_FIELDS
    assert state == {
        "session_id": body["id"], "stage": "interview", "current_step": 1,
        "confirmed_steps": [], "design": Design().model_dump(mode="json"), "agent_design": None,
        "critiques": [], "scorecard": None, "gaps": [], "review_model_distinct": True,
        "prd_draft": None, "prd_versions": [], "proposed_changes": [], "seams": [],
        "tickets": [], "tickets_approved_at": None, "id_counters": {},
        "tokens_used": {"interview": 0, "review": 0}, "token_budget": 12345, "last_error": None,
    }  # fmt: skip


async def test_new_session_copies_review_model_distinct(pool: AsyncConnectionPool[Any]) -> None:
    app = await build_service(
        pool,
        REVIEW_MODEL_BASE_URL="https://interview.example/v1",
        REVIEW_MODEL_NAME="interview-model",
    )
    async with client(app) as http:
        session = (await http.post("/api/sessions", json={"name": "same model"})).json()
        state = (await http.get(f"/api/sessions/{session['id']}")).json()["state"]
    assert state["review_model_distinct"] is False


@pytest.mark.parametrize(
    "body",
    [{"name": ""}, {"name": "   "}, {"name": "x" * 121}, {}, {"name": 5}, {"name": "a", "x": 1}],
)
async def test_create_rejects_invalid_names(pool: AsyncConnectionPool[Any], body: Any) -> None:
    app = await build_service(pool)
    async with client(app) as http:
        assert_error(await http.post("/api/sessions", json=body), 422)
        assert (await http.get("/api/sessions")).json()["items"] == []


async def test_name_of_120_characters_is_accepted(pool: AsyncConnectionPool[Any]) -> None:
    app = await build_service(pool)
    async with client(app) as http:
        assert (await http.post("/api/sessions", json={"name": "x" * 120})).status_code == 201


# --- S3.2 list ---------------------------------------------------------------------------------


async def test_list_is_newest_first_and_keyset_paginated(pool: AsyncConnectionPool[Any]) -> None:
    app = await build_service(pool)
    async with client(app) as http:
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

        # renaming bumps updated_at, so the renamed session moves to the top
        await http.patch(f"/api/sessions/{ids[0]}", json={"name": "renamed"})
        top = (await http.get("/api/sessions", params={"limit": 1})).json()["items"][0]
        assert (top["id"], top["name"], top["stage"]) == (ids[0], "renamed", "interview")


async def test_list_defaults_and_limits(pool: AsyncConnectionPool[Any]) -> None:
    app = await build_service(pool)
    async with client(app) as http:
        for i in range(21):
            await http.post("/api/sessions", json={"name": f"s{i}"})
        page = (await http.get("/api/sessions")).json()
        assert len(page["items"]) == 20 and page["next_cursor"]
        assert len((await http.get("/api/sessions", params={"limit": 100})).json()["items"]) == 21
        assert_error(await http.get("/api/sessions", params={"limit": 101}), 422)
        assert_error(await http.get("/api/sessions", params={"limit": 0}), 422)
        assert_error(await http.get("/api/sessions", params={"cursor": "not-a-cursor"}), 422)


# --- S3.3 to S3.5 ------------------------------------------------------------------------------


async def test_get_rename_and_delete(pool: AsyncConnectionPool[Any]) -> None:
    app = await build_service(pool)
    async with client(app) as http:
        session_id = (await http.post("/api/sessions", json={"name": "old"})).json()["id"]
        renamed = await http.patch(f"/api/sessions/{session_id}", json={"name": " new "})
        assert renamed.status_code == 200 and renamed.json()["name"] == "new"
        assert_error(await http.patch(f"/api/sessions/{session_id}", json={"name": ""}), 422)
        assert_error(
            await http.patch("/api/sessions/missing", json={"name": "x"}), 404, "not_found"
        )
        assert_error(await http.get("/api/sessions/missing"), 404, "not_found")

        assert (await http.delete(f"/api/sessions/{session_id}")).status_code == 204
        assert_error(await http.get(f"/api/sessions/{session_id}"), 404)
        assert (await http.delete(f"/api/sessions/{session_id}")).status_code == 204
        assert (await http.delete("/api/sessions/never-existed")).status_code == 204

    saver = AsyncPostgresSaver(pool)
    assert await saver.aget_tuple({"configurable": {"thread_id": session_id}}) is None


# --- S4.2, NFR-3: checkpointed in Postgres, thread ID = session ID, survives a restart -------


async def test_session_survives_an_agent_restart(database_url: str) -> None:
    async with open_pool(database_url) as first_pool:
        app = await build_service(
            first_pool, ScriptedChatModel.with_script(AIMessage("Who are the users?"))
        )
        async with client(app) as http:
            session_id = (await http.post("/api/sessions", json={"name": "durable"})).json()["id"]
        events = await post_run(app, run_input(session_id, [user("Design a URL shortener", "u1")]))
        assert streamed_text(events) == "Who are the users?"
        async with client(app) as http:
            before = (await http.get(f"/api/sessions/{session_id}")).json()

    # a new process: new pool, new app, models that must not be called
    async with open_pool(database_url) as second_pool:
        app = await build_service(second_pool, ScriptedChatModel.with_script())
        async with client(app) as http:
            after = (await http.get(f"/api/sessions/{session_id}")).json()
        assert after == before

        saver = AsyncPostgresSaver(second_pool)
        checkpoint = await saver.aget_tuple({"configurable": {"thread_id": session_id}})
        assert checkpoint is not None
        messages = checkpoint.checkpoint["channel_values"]["messages"]
        assert [m.text for m in messages] == ["Design a URL shortener", "Who are the users?"]

        # resuming with no new message restores the conversation without a model call
        events = await post_run(app, run_input(session_id, []))
        snapshot = next(e for e in events if e["type"] == "MESSAGES_SNAPSHOT")
        assert [m["content"] for m in snapshot["messages"]] == [
            "Design a URL shortener",
            "Who are the users?",
        ]
        assert "TEXT_MESSAGE_CONTENT" not in event_types(events)


async def test_a_run_updates_the_list_and_unknown_sessions_are_refused(
    pool: AsyncConnectionPool[Any],
) -> None:
    app = await build_service(pool, ScriptedChatModel.with_script(AIMessage("hi")))
    async with client(app) as http:
        first = (await http.post("/api/sessions", json={"name": "first"})).json()
        second = (await http.post("/api/sessions", json={"name": "second"})).json()
        await post_run(app, run_input(first["id"], [user("hello")]))
        items = (await http.get("/api/sessions")).json()["items"]
    assert [i["id"] for i in items] == [first["id"], second["id"]]
    assert items[0]["updated_at"] > first["updated_at"]

    refused = await post_run(app, run_input("no-such-session", [user("hello")]))
    assert event_types(refused) == ["RUN_ERROR"]


# --- S3.7 OpenAPI ----------------------------------------------------------------------------


async def test_openapi_describes_every_route_with_typed_models(
    pool: AsyncConnectionPool[Any],
) -> None:
    app = await build_service(pool)
    async with client(app) as http:
        document = (await http.get("/openapi.json")).json()
    assert document["openapi"].startswith("3.1")
    operations = {
        (method.upper(), path): op
        for path, item in document["paths"].items()
        if path.startswith("/api/")
        for method, op in item.items()
    }
    assert set(operations) == {
        ("POST", "/api/sessions"), ("GET", "/api/sessions"), ("GET", "/api/sessions/{session_id}"),
        ("PATCH", "/api/sessions/{session_id}"), ("DELETE", "/api/sessions/{session_id}"),
    }  # fmt: skip
    for key, op in operations.items():
        for status, response in op["responses"].items():
            if status.startswith("2"):
                if status != "204":
                    assert "$ref" in str(response["content"]["application/json"]["schema"]), key
            else:
                schema = response["content"]["application/json"]["schema"]
                assert schema == {"$ref": "#/components/schemas/ErrorBody"}, (key, status)
        if "requestBody" in op or op.get("parameters"):
            assert "422" in op["responses"], key


async def test_checked_in_rest_contract_matches_the_service(pool: AsyncConnectionPool[Any]) -> None:
    from conftest import REPO_ROOT

    from blueprint.openapi import rest_document

    exported = rest_document()
    checked_in = json.loads((REPO_ROOT / "web" / "openapi.json").read_text())
    assert checked_in == exported, "run: uv run python -m blueprint.openapi > ../web/openapi.json"

    app = await build_service(pool)
    async with client(app) as http:
        served = (await http.get("/openapi.json")).json()
    assert {k: v for k, v in served["paths"].items() if k.startswith("/api/")} == exported["paths"]
    for name, schema in exported["components"]["schemas"].items():
        assert served["components"]["schemas"][name] == schema


def test_session_state_model_matches_design_state() -> None:
    from blueprint.state import SessionState

    assert set(SessionState.model_fields) == set(SESSION_FIELDS)
