"""The attachment routes and the run-start sync, over the real app (SPEC-document-import §4)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from conftest import valid_env
from fakes import ScriptedChatModel
from fastapi import FastAPI
from sample_files import BRIEF_MD, PNG
from service import client, post_run, run_input, user
from test_sessions import assert_error

from blueprint.app import assemble_from, prepare
from blueprint.imports.files import MAX_ATTACHMENTS, MAX_BYTES
from blueprint.llm.clients import RoleModels
from blueprint.storage.sqlite import open_sqlite

PROPOSAL = {
    "summary": "A brief.",
    "functional_requirements": [
        {"quote": "Users shorten a long URL.", "locator": "Link shortener > Requirements",
         "updates": None, "weaknesses": [], "statement": "Users shorten a long URL"}
    ],
}  # fmt: skip


@asynccontextmanager
async def service(
    path: Path, interview: ScriptedChatModel | None = None, vision: bool = False
) -> AsyncIterator[FastAPI]:
    models = RoleModels(interview or ScriptedChatModel(), ScriptedChatModel())
    env = valid_env() | {"DATABASE_URL": f"sqlite:///{path}"}
    runtime = await prepare(env, build=lambda _: models, vision=vision)
    async with open_sqlite(str(path)) as (checkpointer, store):
        yield assemble_from(runtime, checkpointer, store)


async def new_session(http: httpx.AsyncClient) -> str:
    return str((await http.post("/api/sessions", json={"name": "Shortener"})).json()["id"])


def upload(
    http: httpx.AsyncClient, session_id: str, name: str, data: bytes, role: str = "prd"
) -> Any:
    return http.post(
        f"/api/sessions/{session_id}/attachments",
        params={"name": name, "role": role},
        content=data,
        headers={"content-type": "application/octet-stream"},
    )


async def test_upload_list_content_and_remove(tmp_path: Path) -> None:
    async with service(tmp_path / "b.db") as app, client(app) as http:
        sid = await new_session(http)
        created = await upload(http, sid, "brief.md", BRIEF_MD.encode())
        assert created.status_code == 201
        assert created.json() | {"size": 0} == {
            "id": "ATT-1", "name": "brief.md", "role": "prd", "kind": "text",
            "media_type": "text/markdown",
            "size": 0, "warnings": [], "duplicate": False,
        }  # fmt: skip
        again = await upload(http, sid, "copy.md", BRIEF_MD.encode())
        assert (again.status_code, again.json()["id"], again.json()["duplicate"]) == (
            200,
            "ATT-1",
            True,
        )

        listing = (await http.get(f"/api/sessions/{sid}/attachments")).json()
        assert [a["id"] for a in listing["attachments"]] == ["ATT-1"]
        assert ".md" in listing["accepts"] and ".png" not in listing["accepts"]
        content = await http.get(f"/api/sessions/{sid}/attachments/ATT-1/content")
        assert content.content == BRIEF_MD.encode()
        assert content.headers["content-type"].startswith("text/markdown")

        assert (await http.delete(f"/api/sessions/{sid}/attachments/ATT-1")).status_code == 204
        assert (await http.delete(f"/api/sessions/{sid}/attachments/ATT-1")).status_code == 204
        assert (await http.get(f"/api/sessions/{sid}/attachments")).json()["attachments"] == []
        assert_error(await http.get(f"/api/sessions/{sid}/attachments/ATT-1/content"), 404)


async def test_refusals(tmp_path: Path) -> None:
    async with service(tmp_path / "b.db") as app, client(app) as http:
        sid = await new_session(http)
        assert_error(await upload(http, "nope", "a.md", b"# a"), 404, "not_found")
        assert_error(await upload(http, sid, "a.exe", b"MZ"), 415, "unsupported_type")
        assert_error(await upload(http, sid, "a.png", PNG), 422, "vision_unavailable")
        assert_error(
            await upload(http, sid, "a.txt", b"a" * (MAX_BYTES + 1)), 413, "file_too_large"
        )
        assert_error(await upload(http, sid, "a.pdf", b"nope"), 422, "invalid_file")
        for n in range(MAX_ATTACHMENTS):
            assert (await upload(http, sid, f"{n}.md", f"# {n}".encode())).status_code == 201
        assert_error(await upload(http, sid, "one-more.md", b"# more"), 409, "attachment_limit")


async def test_every_file_needs_a_role(tmp_path: Path) -> None:
    async with service(tmp_path / "b.db") as app, client(app) as http:
        sid = await new_session(http)
        no_role = await http.post(
            f"/api/sessions/{sid}/attachments",
            params={"name": "a.md"},
            content=b"# a",
            headers={"content-type": "application/octet-stream"},
        )
        assert_error(no_role, 422)
        assert_error(await upload(http, sid, "a.md", b"# a", role="notes"), 422)
        assert (await upload(http, sid, "a.md", b"# a", role="supporting")).status_code == 201
        listing = (await http.get(f"/api/sessions/{sid}/attachments")).json()
        assert [a["role"] for a in listing["attachments"]] == ["supporting"]


async def test_images_are_taken_when_the_model_reads_them(tmp_path: Path) -> None:
    async with service(tmp_path / "b.db", vision=True) as app, client(app) as http:
        sid = await new_session(http)
        assert (await upload(http, sid, "arch.png", PNG)).json()["kind"] == "image"
        assert ".png" in (await http.get(f"/api/sessions/{sid}/attachments")).json()["accepts"]


async def test_a_run_after_an_upload_imports_the_file_and_opens_the_card(tmp_path: Path) -> None:
    interview = ScriptedChatModel.with_script(PROPOSAL)
    async with service(tmp_path / "b.db", interview) as app:
        async with client(app) as http:
            sid = await new_session(http)
            await upload(http, sid, "brief.md", BRIEF_MD.encode())

        events = await post_run(app, run_input(sid, [user("Attached brief.md (ATT-1).")]))

        calls = [e for e in events if e["type"] == "TOOL_CALL_START"]
        assert [c["toolCallName"] for c in calls] == ["review_import"]
        async with client(app) as http:
            state = (await http.get(f"/api/sessions/{sid}")).json()["state"]
        assert state["attachments"][0]["status"] == "imported"
        assert [c["status"] for c in state["import_queue"]] == ["offered"]


async def test_files_cannot_change_after_the_interview(tmp_path: Path) -> None:
    async with service(tmp_path / "b.db") as app:
        async with client(app) as http:
            sid = await new_session(http)
        graph = app.state.graph
        await graph.aupdate_state({"configurable": {"thread_id": sid}}, {"stage": "prd_signoff"})
        async with client(app) as http:
            assert_error(await upload(http, sid, "late.md", b"# late"), 409, "wrong_stage")
            assert_error(
                await http.delete(f"/api/sessions/{sid}/attachments/ATT-1"), 409, "wrong_stage"
            )


async def test_deleting_the_session_deletes_its_files(tmp_path: Path) -> None:
    async with service(tmp_path / "b.db") as app, client(app) as http:
        sid = await new_session(http)
        await upload(http, sid, "brief.md", BRIEF_MD.encode())
        assert (await http.delete(f"/api/sessions/{sid}")).status_code == 204
        assert_error(await http.get(f"/api/sessions/{sid}/attachments"), 404)
