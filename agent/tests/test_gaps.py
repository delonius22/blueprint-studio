"""T-11: gap resolution — answer or accept (S5.3, S6.5, S11.4)."""

import json
from typing import Any

from fakes import ScriptedChatModel, prd_out
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from seam import GraphSeam

from blueprint.domain.models import Design, Endpoint, Gap, Requirement
from blueprint.graph.gates import close_unanswered

DESIGN = Design(
    functional_requirements=[Requirement(id="FR-1", statement="Users shorten URLs")],
    endpoints=[
        Endpoint(id="EP-1", method="POST", path="/urls", request="{url}", response="{code}")
    ],
)
GAPS = [
    Gap(
        id="GAP-1",
        lens="security",
        item_ids=["EP-1"],
        risk="Anyone can create codes",
        decision_needed="Who may create codes?",
        severity="high",
    ),
    Gap(
        id="GAP-2",
        lens="efficiency",
        item_ids=["FR-1"],
        risk="No cache",
        decision_needed="Cache hot codes?",
        severity="low",
    ),
]


def resolving(*script: Any, gaps: list[Gap] = GAPS) -> GraphSeam:
    seam = GraphSeam(
        ScriptedChatModel.with_script(*script),
        ScriptedChatModel.with_script(name="review"),  # the review never runs again
        initial={"stage": "gap_resolution", "current_step": 5, "confirmed_steps": [1, 2, 3, 4, 5],
                 "design": DESIGN.model_dump(mode="json"), "agent_design": DESIGN.model_dump(mode="json"),
                 "id_counters": {"FR": 1, "EP": 1, "GAP": len(gaps)},
                 "gaps": [g.model_dump(mode="json") for g in gaps]},
    )  # fmt: skip
    return seam


async def open_card(seam: GraphSeam) -> str:
    """Put the decide_gaps card in the thread the way the gap merger does, and return its ID."""
    from blueprint.graph.build import decide_gaps_args
    from blueprint.graph.gates import gate_message

    await seam._ensure_session("session-1")
    message, call = gate_message("decide_gaps", decide_gaps_args(GAPS), "2 gaps")
    await seam.graph.aupdate_state(
        seam.config("session-1"), {"messages": [message]}, as_node="gap_merger"
    )
    return str(call["id"])


def decisions(*items: tuple[str, str, str]) -> str:
    return json.dumps([{"gap_id": g, "decision": d, "text": t} for g, d, t in items])


async def gaps(seam: GraphSeam) -> dict[str, dict[str, Any]]:
    return {g["id"]: g for g in (await seam.state())["gaps"]}


async def test_accepted_gaps_get_status_and_note_and_the_stage_moves_on() -> None:
    draft = prd_out({"Short links": ["FR-1"]}, {"GAP-1": ["Short links"], "GAP-2": ["Short links"]})
    seam = resolving(draft)
    card = await open_card(seam)

    await seam.answer(
        card, decisions(("GAP-1", "accept", "Internal tool for v1"), ("GAP-2", "accept", ""))
    )

    register = await gaps(seam)
    assert (register["GAP-1"]["status"], register["GAP-1"]["note"]) == (
        "accepted",
        "Internal tool for v1",
    )
    assert (register["GAP-2"]["status"], register["GAP-2"]["note"]) == ("accepted", None)
    state = await seam.state()
    assert state["stage"] == "prd_signoff"  # all settled: the PRD draft followed at once
    assert [c.structured_method for c in seam.interview.calls] == [
        "json_schema"
    ]  # only the drafter
    assert seam.review.calls == []  # no re-review


async def test_an_answered_gap_is_recorded_as_design_items_and_resolved() -> None:
    seam = resolving(
        AIMessage(content="", tool_calls=[
            {"name": "upsert_requirement", "args": {"statement": "Only signed-in users create codes"}, "id": "c1"},
            {"name": "resolve_gap", "args": {"gap_id": "GAP-1", "item_ids": ["FR-2"]}, "id": "c2"},
        ]),
        AIMessage("Recorded FR-2 and closed GAP-1."),
        prd_out({"Short links": ["FR-1", "FR-2"]}, {"GAP-2": ["Short links"]}),
    )  # fmt: skip
    card = await open_card(seam)

    await seam.answer(
        card, decisions(("GAP-1", "answer", "Only signed-in users"), ("GAP-2", "accept", "Later"))
    )

    first = seam.interview.calls[0]
    system = first.messages[0]
    assert isinstance(system, SystemMessage)
    assert (
        "GAP-1" in system.text
        and "Only signed-in users" in system.text
        and "GAP-2 (" not in system.text
    )
    assert "resolve_gap" in first.tools
    register = await gaps(seam)
    assert (register["GAP-1"]["status"], register["GAP-1"]["resolved_by"]) == ("resolved", ["FR-2"])
    assert register["GAP-2"]["status"] == "accepted"
    state = await seam.state()
    assert [r["id"] for r in state["design"]["functional_requirements"]] == ["FR-1", "FR-2"]
    assert state["stage"] == "prd_signoff"
    assert seam.review.calls == []


async def test_gaps_left_open_come_back_in_a_new_card() -> None:
    seam = resolving(AIMessage("I need more detail before recording that."))
    card = await open_card(seam)

    await seam.answer(
        card, decisions(("GAP-1", "answer", "Sign-in, probably"), ("GAP-2", "accept", ""))
    )

    state = await seam.state()
    assert state["stage"] == "gap_resolution"
    last = state["messages"][-1]
    assert isinstance(last, AIMessage) and last.tool_calls[0]["name"] == "decide_gaps"
    assert [g["id"] for g in last.tool_calls[0]["args"]["gaps"]] == ["GAP-1"]
    assert last.tool_calls[0]["id"] != card


async def test_resolve_gap_needs_an_open_gap_and_recorded_items() -> None:
    seam = resolving(
        AIMessage(content="", tool_calls=[
            {"name": "resolve_gap", "args": {"gap_id": "GAP-1", "item_ids": ["FR-9"]}, "id": "c1"},
            {"name": "resolve_gap", "args": {"gap_id": "GAP-2", "item_ids": ["FR-1"]}, "id": "c2"},
            {"name": "resolve_gap", "args": {"gap_id": "GAP-7", "item_ids": ["FR-1"]}, "id": "c3"},
        ]),
        AIMessage("ok"),
    )  # fmt: skip
    card = await open_card(seam)
    await seam.answer(card, decisions(("GAP-1", "answer", "x"), ("GAP-2", "accept", "")))

    results = [
        json.loads(m.text)
        for m in seam.interview.calls[1].messages
        if isinstance(m, ToolMessage) and m.tool_call_id in ("c1", "c2", "c3")
    ]
    assert results == [
        {"error": "record the answer first: FR-9 not in the design record"},
        {"error": "GAP-2 is already accepted"},
        {"error": "GAP-7 is not a gap in the register"},
    ]


def test_unanswered_tool_calls_are_closed_before_a_model_sees_them() -> None:
    gate = AIMessage(content="", tool_calls=[{"name": "decide_gaps", "args": {}, "id": "g1"}])
    history = close_unanswered(
        [HumanMessage("hi"), gate, HumanMessage("Actually, a question first")]
    )
    assert [type(m).__name__ for m in history] == [
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
        "HumanMessage",
    ]
    assert history[2].tool_call_id == "g1"  # type: ignore[attr-defined]
