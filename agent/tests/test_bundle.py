"""T-18: bundle.zip, deterministic downloads and export time (S10.3, S10.8, S10.9, S13.5, NFR-2)."""

import hashlib
import io
import json
import logging
import os
import statistics
import subprocess
import sys
import time
import zipfile
from typing import Any

from fixtures import STORIES, complete_state
from psycopg_pool import AsyncConnectionPool
from service import build_service, client

from blueprint.domain.models import ProposedChange, Ticket
from blueprint.domain.state import SessionState
from blueprint.exports.downloads import KINDS, render, unmet
from blueprint.planning.changes import apply_changes
from blueprint.utils import log

NAME = "URL shortener"


def with_v1_2() -> SessionState:
    state = complete_state()
    change = ProposedChange(
        id="CHG-1",
        section="goals",
        kind="add",
        proposed_text="Links expire",
        reason="r",
        decision="approved",
    )
    doc = apply_changes(state.prd_versions[-1].doc, [change], {})
    v12 = {"version": "1.2", "approved_at": "2026-10-14T14:00:00Z", "doc": doc.model_dump()}
    versions = [*(v.model_dump() for v in state.prd_versions), v12]
    return SessionState.model_validate(
        state.model_dump() | {"prd_versions": versions, "proposed_changes": [change.model_dump()]}
    )


def test_the_bundle_holds_every_available_kind_except_itself_under_its_file_name() -> None:
    for state, names in (
        (
            complete_state(),
            [
                "PRD v1.0.docx",
                "PRD v1.1.docx",
                "Requirements.docx",
                "UserStories.docx",
                "context.md",
                "Diagrams.md",
            ],
        ),
        (
            with_v1_2(),
            [
                "PRD v1.0.docx",
                "PRD v1.1.docx",
                "PRD v1.2.docx",
                "Requirements.docx",
                "UserStories.docx",
                "context.md",
                "Diagrams.md",
            ],
        ),
    ):
        archive = zipfile.ZipFile(io.BytesIO(render(state, "bundle.zip", NAME)))
        assert archive.namelist() == names
        for kind, spec in KINDS.items():
            if kind != "bundle.zip" and unmet(state, kind) is None:
                assert archive.read(spec.file_name(NAME)) == render(state, kind, NAME), kind
        assert {i.date_time for i in archive.infolist()} == {(2026, 10, 14, 15, 45, 0)}
    assert KINDS["bundle.zip"].file_name(NAME) == "URL shortener - Blueprint.zip"


def test_every_kind_renders_byte_identically_from_the_same_state() -> None:
    state = with_v1_2()
    for kind in KINDS:
        assert unmet(state, kind) is None, kind
        assert render(state, kind, NAME) == render(
            SessionState.model_validate(state.model_dump()), kind, NAME
        ), kind


def test_renders_are_identical_across_processes() -> None:
    """Different hash seeds and clocks: nothing may depend on set order or the time of export."""
    state = json.dumps(with_v1_2().model_dump(mode="json"))
    script = (
        "import hashlib, json, sys\n"
        "from blueprint.exports.downloads import KINDS, render\n"
        "from blueprint.domain.state import SessionState\n"
        "state = SessionState.model_validate(json.loads(sys.stdin.read()))\n"
        "print(json.dumps({k: hashlib.sha256(render(state, k, 'URL shortener')).hexdigest() for k in KINDS}))\n"
    )
    digests = []
    for seed in ("1", "2"):
        environment = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", script],
            input=state,
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        digests.append(json.loads(result.stdout))
        time.sleep(1.1)  # a different wall-clock second
    assert digests[0] == digests[1]
    assert (
        digests[0]["bundle.zip"]
        == hashlib.sha256(render(with_v1_2(), "bundle.zip", NAME)).hexdigest()
    )


def fifty_tickets() -> SessionState:
    tickets = [
        Ticket(
            id=f"T-{i:02d}",
            title=f"Slice {i}",
            what_to_build=f"Build slice {i} end to end. " * 5,
            blocked_by=[f"T-{i - 1:02d}"] if i > 1 else [],
            acceptance_criteria=[f"Criterion {i}.{j}" for j in range(1, 6)],
            story_ids=[STORIES[i % len(STORIES)].id],
            kind="slice",
        ).model_dump()
        for i in range(1, 51)
    ]
    return complete_state(tickets=tickets)


def test_a_50_ticket_bundle_takes_under_10_s_at_p95() -> None:
    state = fifty_tickets()
    timings = []
    for _ in range(20):
        start = time.perf_counter()
        render(state, "bundle.zip", NAME)
        timings.append(time.perf_counter() - start)
    p95 = statistics.quantiles(timings, n=20)[-1]
    assert p95 <= 10.0, f"p95 {p95:.2f} s"
    print(f"bundle.zip for 50 tickets: p95 {p95 * 1000:.0f} ms over 20 runs")


async def test_downloads_are_409_before_completion_and_log_export_ms(
    pool: AsyncConnectionPool[Any],
) -> None:
    stream = io.StringIO()
    handler = log.configure(secrets=(), stream=stream)
    try:
        app = await build_service(pool)
        async with client(app) as http:
            session = (await http.post("/api/sessions", json={"name": NAME})).json()
            url = f"/api/sessions/{session['id']}/downloads/bundle.zip"
            assert (await http.get(url)).status_code == 409
            await app.state.graph.aupdate_state(
                {"configurable": {"thread_id": session["id"]}},
                complete_state().model_dump(mode="json"),
            )
            response = await http.get(url)
    finally:
        logging.getLogger(log.LOGGER_NAME).removeHandler(handler)
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    assert 'filename="URL shortener - Blueprint.zip"' in response.headers["content-disposition"]
    entries = [
        json.loads(line) for line in stream.getvalue().splitlines() if '"event": "download"' in line
    ]
    assert [(e["kind"], e["status"]) for e in entries] == [("bundle.zip", 409), ("bundle.zip", 200)]
    assert all(isinstance(e["export_ms"], int) for e in entries)
