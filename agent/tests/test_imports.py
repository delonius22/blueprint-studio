"""From a proposal to recorded items: grounding, staging, decisions and notes (SPEC §2.4, §2.5)."""

from typing import Any

from blueprint.domain.models import (
    AttachmentRef,
    Component,
    Design,
    ImportCandidate,
    ImportNote,
    SourceRef,
)
from blueprint.imports.files import Section
from blueprint.imports.proposal import (
    ImportProposal,
    apply_decisions,
    import_decisions,
    imported_material,
    mark_asked,
    offer,
    read_proposal,
    review_import_args,
    sync_attachments,
    withdraw,
)
from blueprint.interview.tools import Draft, bound_tool_names
from blueprint.storage.sessions import AttachmentRow, StoredAttachment

ROW = AttachmentRow("ATT-1", "prd.md", "text", "text/markdown", 10, "0" * 64, [])
FILE = StoredAttachment(
    ROW,
    b"",
    [
        Section("Requirements", "Users shorten a long URL. Redirects must be fast."),
        Section("Architecture", "The browser calls the API, which reads Postgres."),
    ],
)


def proposal(**lists: list[dict[str, Any]]) -> Any:
    return ImportProposal.model_validate({"summary": "A shortener PRD"} | lists)


def item(quote: str, locator: str = "Requirements", **fields: Any) -> dict[str, Any]:
    return {"quote": quote, "locator": locator, "updates": None, "weaknesses": []} | fields


def test_only_items_the_file_states_become_candidates() -> None:
    counters: dict[str, int] = {}
    design = Design.model_validate({"functional_requirements": [{"id": "FR-1", "statement": "x"}]})
    candidates, _, _ = read_proposal(
        proposal(
            functional_requirements=[
                item("users  SHORTEN a long url", statement="Users shorten a long URL"),
                item("Users export links", statement="Users export links"),  # not in the file
                item("Redirects must be fast", statement="Redirect", updates="FR-9"),  # unknown ID
            ],
            components=[
                item(
                    "The browser calls the API",
                    "Architecture",
                    name="API",
                    kind="service",
                    responsibility="Serves",
                )
            ],
        ),
        FILE,
        design,
        counters,
    )
    assert [(c.id, c.tool, c.step) for c in candidates] == [
        ("IMP-1", "upsert_requirement", 1),
        ("IMP-2", "upsert_component", 3),
    ]
    assert candidates[0].source == SourceRef(
        attachment_id="ATT-1", locator="Requirements", quote="users  SHORTEN a long url"
    )
    assert counters == {"IMP": 2}


def test_open_questions_and_prd_context_must_also_be_quoted() -> None:
    _, questions, excerpts = read_proposal(
        proposal(
            open_questions=[
                {
                    "step": 1,
                    "quote": "Redirects must be fast",
                    "locator": "Requirements",
                    "question": "How fast?",
                },
                {"step": 1, "quote": "made up", "locator": "x", "question": "Ignored?"},
            ],
            prd_context=[
                {"topic": "problem", "quote": "Users shorten a long URL", "locator": "Requirements"}
            ],
        ),
        FILE,
        Design(),
        {},
    )
    assert [(q.code, q.detail) for q in questions] == [("question", "How fast?")]
    assert [e.topic for e in excerpts] == ["problem"]


def candidate(
    cid: str, step: int, tool: str, args: dict[str, Any], **extra: Any
) -> ImportCandidate:
    source = SourceRef(attachment_id="ATT-1", locator="Requirements", quote="q")
    return ImportCandidate(
        id=cid,
        attachment_id="ATT-1",
        step=step,
        tool=tool,
        args=args,
        source=source,
        status="staged",
        **extra,
    )


def test_candidates_wait_for_their_step() -> None:
    queue = [
        candidate("IMP-1", 1, "upsert_requirement", {"statement": "a"}),
        candidate("IMP-2", 3, "upsert_component", {}),
    ]
    assert [c.status for c in offer(queue, 1)] == ["offered", "staged"]
    assert [c.status for c in offer(queue, 3)] == ["offered", "offered"]
    assert [c.status for c in withdraw(offer(queue, 3))] == ["staged", "staged"]


def test_decisions_record_accepted_and_edited_items_and_link_new_names() -> None:
    queue = offer(
        [
            candidate(
                "IMP-1",
                1,
                "upsert_nfr",
                {"category": "latency", "statement": "Fast"},
                weaknesses=[
                    {"code": "missing_unit", "detail": "no unit"},
                    {"code": "vague", "detail": "how fast"},
                ],
            ),
            candidate("IMP-2", 1, "upsert_requirement", {"statement": "Export"}),
            candidate(
                "IMP-3",
                3,
                "upsert_component",
                {"name": "API", "kind": "service", "responsibility": "Serves"},
            ),
            candidate(
                "IMP-4",
                3,
                "upsert_component",
                {"name": "Links DB", "kind": "database", "responsibility": "Stores"},
            ),
            candidate(
                "IMP-5",
                3,
                "upsert_flow",
                {
                    "name": "Redirect",
                    "kind": "read",
                    "steps": [
                        {"from_component": "api", "to_component": "Links DB", "label": "lookup"}
                    ],
                },
            ),
            candidate(
                "IMP-6",
                3,
                "upsert_flow",
                {
                    "name": "Broken",
                    "kind": "read",
                    "steps": [{"from_component": "Nowhere", "to_component": "API", "label": ""}],
                },
            ),
        ],
        current_step=3,
    )
    decisions = import_decisions(
        {
            "decisions": [
                {
                    "candidate_id": "IMP-1",
                    "decision": "edit",
                    "fields": {"unit": "ms", "target": 50, "id": "FR-9"},
                },
                {"candidate_id": "IMP-2", "decision": "reject"},
                *({"candidate_id": f"IMP-{n}", "decision": "accept"} for n in (3, 4, 5, 6)),
                {"candidate_id": "IMP-7", "bad": True},
            ]
        }
    )
    draft = Draft(Design(), {})
    applied = apply_decisions(queue, decisions, draft, bound_tool_names(3))
    assert applied.recorded == {
        "IMP-1": "NFR-1",
        "IMP-3": "CMP-1",
        "IMP-4": "CMP-2",
        "IMP-5": "FLW-1",
    }
    assert applied.rejected == ["IMP-2"]
    assert list(applied.failed) == ["IMP-6"]
    nfr = draft.design.non_functional_requirements[0]
    assert (nfr.unit, nfr.target) == ("ms", 50)  # edited; the edit could not set an ID
    assert draft.design.flows[0].steps[0].from_component == "CMP-1"
    assert [n.code for n in applied.notes] == ["vague"]  # missing_unit was fixed in the card
    assert set(applied.provenance) == {"NFR-1", "CMP-1", "CMP-2", "FLW-1"}
    assert draft.counters == {"NFR": 1, "CMP": 2, "FLW": 1}


def test_step_1_never_records_architecture_even_when_offered() -> None:
    queue = offer(
        [
            candidate(
                "IMP-1",
                3,
                "upsert_component",
                {"name": "API", "kind": "service", "responsibility": "x"},
            )
        ],
        3,
    )
    draft = Draft(Design(), {})
    applied = apply_decisions(
        queue,
        import_decisions({"decisions": [{"candidate_id": "IMP-1", "decision": "accept"}]}),
        draft,
        bound_tool_names(1),
    )
    assert list(applied.failed) == ["IMP-1"] and draft.design.components == []


def test_the_card_shows_offered_candidates_with_their_editable_fields_and_the_item_they_change() -> (
    None
):
    design = Design(
        components=[Component(id="CMP-1", name="API", kind="service", responsibility="Old")]
    )
    queue = [
        candidate(
            "IMP-1",
            3,
            "upsert_component",
            {"name": "API", "kind": "service", "responsibility": "New"},
            updates="CMP-1",
        ),
        candidate("IMP-2", 4, "upsert_spof", {"component_id": "CMP-1", "risk": "x"}),
    ]
    refs = [AttachmentRef(id="ATT-1", name="prd.md", kind="text")]
    (shown,) = review_import_args(offer(queue, 3), refs, design)["candidates"]
    assert shown["file"] == "prd.md" and shown["current"]["responsibility"] == "Old"
    assert list(shown["editable"]) == ["name", "kind", "responsibility"]
    assert shown["editable"]["name"] == "text" and "database" in shown["editable"]["kind"]


def test_notes_are_raised_once_their_step_is_reached() -> None:
    notes = [
        ImportNote(
            attachment_id="ATT-1",
            step=1,
            item_id="NFR-1",
            code="missing_unit",
            detail="no unit",
            quote="fast",
        ),
        ImportNote(attachment_id="ATT-1", step=3, code="question", detail="Which cache?", quote=""),
    ]
    refs = [
        AttachmentRef(id="ATT-1", name="prd.md", kind="text", status="imported", summary="A PRD.")
    ]
    text = imported_material(refs, notes, current_step=1)
    assert text is not None
    assert "- ATT-1: prd.md (imported). A PRD." in text
    assert '- NFR-1 [missing_unit] no unit (the file says: "fast")' in text
    assert "Which cache?" not in text
    asked = mark_asked(notes, 1)
    assert [n.status for n in asked] == ["asked", "open"]
    assert "Ask about these" not in (imported_material(refs, asked, 1) or "")
    assert imported_material([], notes, 1) is None


def test_sync_adds_new_uploads_and_drops_what_waits_on_a_removed_file() -> None:
    row2 = AttachmentRow("ATT-2", "arch.png", "image", "image/png", 5, "1" * 64, ["w"])
    values = {
        "attachments": [{"id": "ATT-1", "name": "prd.md", "kind": "text", "status": "imported"}],
        "import_queue": [candidate("IMP-1", 3, "upsert_component", {}).model_dump(mode="json")],
    }
    update = sync_attachments(values, [row2])
    assert [(r["id"], r["status"]) for r in update["attachments"]] == [
        ("ATT-1", "removed"),
        ("ATT-2", "parsed"),
    ]
    assert update["attachments"][1]["warnings"] == ["w"] and update["import_queue"] == []
    assert sync_attachments(update, [row2]) == {}
