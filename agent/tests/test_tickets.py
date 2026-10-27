"""T-15: tickets with to-tickets, completing the session (S2.14, S9.1-S9.4, G3)."""

from typing import Any

import pytest
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from seam import GraphSeam
from test_prd import signed_off_state
from test_spec import story

from blueprint.domain.models import UserStory
from blueprint.planning.tickets import DagError, TicketDraft, planner_view, validate_dag


def ticket(
    label: str, stories: list[str], blocked_by: list[str] | None = None, title: str | None = None
) -> dict[str, Any]:
    return {
        "id": label,
        "title": title or f"Ticket {label}",
        "what_to_build": "A thin slice",
        "blocked_by": blocked_by or [],
        "acceptance_criteria": ["It works"],
        "story_ids": stories,
        "kind": "slice",
    }


GOOD = {
    "tickets": [ticket("b", ["US-2"], ["a"]), ticket("a", ["US-1"]), ticket("c", ["US-3"], ["a"])]
}


def planning(*script: Any) -> GraphSeam:
    base = signed_off_state()
    v10 = base.prd_versions[0].doc
    stories = [
        UserStory(id=f"US-{i + 1}", **story(f, r))
        for i, (f, r) in enumerate([("F-1", ["FR-1"]), ("F-1", ["FR-2"]), ("F-2", ["FR-3"])])
    ]
    v11 = v10.model_copy(update={
        "solution": "A web service", "user_stories": stories, "testing_decisions": ["SEAM-1: HTTP API."],
        "further_notes": ["Analytics may come later", "GAP-1: Open creation Decision needed: Who? Note: v1"],
    })  # fmt: skip
    initial = base.model_dump(mode="json") | {
        "stage": "ticket_breakdown",
        "prd_draft": v11.model_dump(mode="json"),
        "prd_versions": [base.prd_versions[0].model_dump(mode="json"),
                         {"version": "1.1", "approved_at": "2026-10-14T13:00:00Z", "doc": v11.model_dump(mode="json")}],
    }  # fmt: skip
    keys = ("stage", "design", "gaps", "prd_draft", "prd_versions")
    return GraphSeam(
        ScriptedChatModel.with_script(*script),
        initial={k: initial[k] for k in keys} | {"current_step": 5},
    )


async def test_the_planner_runs_to_tickets_verbatim_and_never_sees_an_open_gap() -> None:
    seam = planning(GOOD)
    await seam.resync()

    system, human = seam.interview.calls[0].messages
    assert isinstance(system, SystemMessage) and seam.assets.to_tickets in system.text
    assert "Vendored verbatim from mattpocock-skills 1.2.3" in system.text
    assert isinstance(human, HumanMessage)
    for gap_text in ("GAP-1", "Open creation", "Decision needed: Who?"):
        assert gap_text not in human.text
    assert "Analytics may come later" in human.text and "US-3" in human.text


async def test_valid_tickets_are_renumbered_in_build_order_and_complete_the_session() -> None:
    seam = planning(GOOD)
    await seam.resync()

    state = await seam.state()
    assert [(t["id"], t["title"], t["blocked_by"]) for t in state["tickets"]] == [
        ("T-01", "Ticket a", []),
        ("T-02", "Ticket b", ["T-01"]),
        ("T-03", "Ticket c", ["T-01"]),
    ]
    assert state["stage"] == "complete"
    assert state["tickets_approved_at"] is not None and state["tickets_approved_at"].endswith("Z")
    assert not any(isinstance(m, AIMessage) and m.tool_calls for m in state["messages"])
    summary, done = state["messages"][-2:]
    assert "T-01" in summary.text and "T-03" in summary.text
    assert (
        "PRD v1.0.docx, PRD v1.1.docx, Requirements.docx, UserStories.docx and context.md"
        in done.text
    )


async def test_stories_must_be_covered_with_one_corrective_retry() -> None:
    missing = {"tickets": [ticket("a", ["US-1"]), ticket("b", ["US-9"])]}
    seam = planning(missing, GOOD)
    await seam.resync()
    retry = seam.interview.calls[1].messages[-1]
    assert isinstance(retry, HumanMessage)
    assert "ticket b names US-9, which is not a user story" in retry.text
    assert (
        "US-2 is delivered by no ticket" in retry.text
        and "US-3 is delivered by no ticket" in retry.text
    )
    assert (await seam.state())["stage"] == "complete"


async def test_a_cycle_is_named_and_sent_back_to_the_planner() -> None:
    cyclic = {
        "tickets": [
            ticket("a", ["US-1"], ["c"]),
            ticket("b", ["US-2"], ["a"]),
            ticket("c", ["US-3"], ["b"]),
        ]
    }
    seam = planning(cyclic, GOOD)
    await seam.resync()

    second = seam.interview.calls[1].messages[1]
    assert isinstance(second, HumanMessage)
    assert "the blocking edges contain a cycle: a → c → b → a" in second.text
    assert (await seam.state())["stage"] == "complete"  # completes only once the cycle is fixed


async def test_a_planner_that_keeps_producing_cycles_stops_with_an_error() -> None:
    cyclic = {"tickets": [ticket("a", ["US-1", "US-2", "US-3"], ["a"])]}
    seam = planning(cyclic, cyclic, cyclic)
    await seam.resync()
    state = await seam.state()
    assert (
        state["last_error"]["code"] == "invalid_output"
        and "cycle" in state["last_error"]["message"]
    )
    assert state["tickets"] == [] and state["stage"] == "ticket_breakdown"


def test_the_dag_validator_rules() -> None:
    def drafts(*items: dict[str, Any]) -> list[TicketDraft]:
        return [TicketDraft.model_validate(i) for i in items]

    with pytest.raises(DagError, match="duplicate ticket IDs: a"):
        validate_dag(drafts(ticket("a", ["US-1"]), ticket("a", ["US-2"])))
    with pytest.raises(DagError, match="ticket a is blocked by unknown tickets: z"):
        validate_dag(drafts(ticket("a", ["US-1"], ["z"])))
    ordered = validate_dag(
        drafts(ticket("x", ["US-1"], ["z"]), ticket("y", ["US-2"]), ticket("z", ["US-3"]))
    )
    assert [(t.id, t.title, t.blocked_by) for t in ordered] == [
        ("T-01", "Ticket y", []),
        ("T-02", "Ticket z", []),
        ("T-03", "Ticket x", ["T-02"]),
    ]


def test_the_planner_view_removes_open_gaps_and_gap_notes() -> None:
    doc = (
        signed_off_state()
        .prd_versions[0]
        .doc.model_copy(update={"further_notes": ["Keep", "GAP-1: Open creation"]})
    )
    view = planner_view(doc)
    assert view.open_gaps == [] and view.further_notes == ["Keep"]
    assert doc.open_gaps  # the PRD itself is unchanged
