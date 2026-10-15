"""T-10: design review on the review model (S2.9, S6.1-S6.4, S6.6, S13.3, G3, G4)."""

import json
from typing import Any

from fakes import RoutedChatModel, ScriptedChatModel, prd_out
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from seam import GraphSeam

from blueprint.domain import Component, Design, Endpoint, NfrTarget, Requirement
from blueprint.review import GapFinding, combine, gap_register, held_to_inputs

DESIGN = Design(
    functional_requirements=[Requirement(id="FR-1", statement="Users shorten URLs")],
    non_functional_requirements=[
        NfrTarget(id="NFR-1", category="latency", statement="Fast redirects")
    ],
    endpoints=[
        Endpoint(id="EP-1", method="POST", path="/urls", request="{url}", response="{code}")
    ],
    components=[Component(id="CMP-1", name="API", kind="service", responsibility="shorten")],
)
COUNTERS = {"FR": 1, "NFR": 1, "EP": 1, "CMP": 1}


def finding(
    lens: str,
    ids: list[str],
    risk: str,
    severity: str = "medium",
    decision: str = "Who may call it?",
) -> dict[str, Any]:
    return {
        "lens": lens,
        "item_ids": ids,
        "risk": risk,
        "decision_needed": decision,
        "severity": severity,
    }


def lens_of(messages: list[BaseMessage]) -> str | None:
    system = messages[0].text if messages and isinstance(messages[0], SystemMessage) else ""
    for lens in ("security", "efficiency", "maintainability"):
        if f"one lens only: {lens}" in system:
            return lens
    return None


def judge(
    per_lens: dict[str, list[dict[str, Any]]],
    merged: list[dict[str, Any]] | None = None,
    usage: tuple[int, int] | None = None,
) -> RoutedChatModel:
    def route(messages: list[BaseMessage], schema: Any) -> Any:
        lens = lens_of(messages)
        if lens is not None:
            return {"findings": per_lens.get(lens, [])}
        assert messages[0].text.startswith("You merge findings")
        inputs = json.loads(messages[1].text.split("```json\n")[-1].rstrip("`\n"))["findings"]
        return {"gaps": merged if merged is not None else inputs}

    return RoutedChatModel.answering(route, name="review", usage=usage)


def at_review(
    review: RoutedChatModel, interview: ScriptedChatModel | None = None, **initial: Any
) -> GraphSeam:
    return GraphSeam(
        interview or ScriptedChatModel.with_script(),
        review,
        initial={"stage": "design_review", "current_step": 5, "confirmed_steps": [1, 2, 3, 4, 5],
                 "design": DESIGN.model_dump(mode="json"), "agent_design": DESIGN.model_dump(mode="json"),
                 "id_counters": dict(COUNTERS)} | initial,
    )  # fmt: skip


async def test_three_reviewers_run_on_the_review_model_without_the_transcript() -> None:
    review = judge(
        {"security": [finding("security", ["EP-1"], "POST /urls has no authentication")]}
    )
    seam = at_review(review)
    await seam.send("This sentence is only in the transcript")

    reviewer_calls = [c for c in review.calls if lens_of(c.messages)]
    assert sorted(lens_of(c.messages) or "" for c in reviewer_calls) == [
        "efficiency",
        "maintainability",
        "security",
    ]
    assert seam.interview.calls == []  # the review never uses the interview model
    for call in reviewer_calls:
        lens = lens_of(call.messages)
        assert call.messages[0].text == seam.assets.design_judge_reviewer.replace(
            "{lens}", lens or ""
        )
        record = call.messages[1].text
        assert '"id": "FR-1"' in record and '"id": "NFR-1"' in record and '"id": "EP-1"' in record
        assert "only in the transcript" not in record
    assert review.calls[-1].messages[0].text == seam.assets.design_judge_merge


async def test_the_merger_keeps_cited_findings_combines_duplicates_and_issues_gap_ids() -> None:
    review = judge({
        "security": [finding("security", ["EP-1"], "No rate limit on POST /urls", "medium"),
                     finding("security", ["EP-9"], "Unknown endpoint is open", "high")],
        "efficiency": [finding("efficiency", ["EP-1"], "No rate limit on POST /urls.", "high"),
                       finding("efficiency", ["NFR-1"], "No cache for hot codes", "low")],
        "maintainability": [finding("maintainability", [], "Nothing cited", "high")],
    })  # fmt: skip
    seam = at_review(review)
    await seam.send("review please")

    state = await seam.state()
    gaps = state["gaps"]
    assert [(g["id"], g["lens"], g["item_ids"], g["severity"], g["status"]) for g in gaps] == [
        (
            "GAP-1",
            "efficiency",
            ["EP-1"],
            "high",
            "open",
        ),  # duplicate combined, higher severity kept
        ("GAP-2", "efficiency", ["NFR-1"], "low", "open"),
    ]
    assert state["id_counters"]["GAP"] == 2
    assert state["stage"] == "gap_resolution"
    merger_input = review.calls[-1].messages[1].text
    assert (
        "EP-9" not in merger_input and "Nothing cited" not in merger_input
    )  # dropped before merging


async def test_a_finding_that_proposes_a_new_component_adds_no_design_item_or_requirement() -> None:
    proposal = finding(
        "efficiency",
        ["CMP-1"],
        "Add a Redis cache component in front of the API to absorb reads",
        "medium",
        decision="Should a Redis cache be added?",
    )
    invented = finding("efficiency", ["CMP-99"], "New CDN component", "high")
    review = judge(
        {"efficiency": [proposal, invented]},
        merged=[
            proposal,
            invented,
            finding("security", ["FR-1"], "invented by the merger", "high"),
        ],
    )
    seam = at_review(review)
    await seam.send("review please")

    state = await seam.state()
    assert Design.model_validate(state["design"]) == DESIGN  # no component, no requirement
    assert state["id_counters"] == COUNTERS | {"GAP": 1}
    assert [(g["item_ids"], g["risk"]) for g in state["gaps"]] == [(["CMP-1"], proposal["risk"])]


async def test_zero_gaps_goes_straight_to_the_prd_draft() -> None:
    review = judge({})
    seam = at_review(review, ScriptedChatModel.with_script(prd_out({"Short links": ["FR-1"]})))
    await seam.send("review please")
    state = await seam.state()
    assert (state["stage"], state["gaps"], state["last_error"]) == ("prd_signoff", [], None)
    assert len(review.calls) == 3  # nothing to merge, so no merger call
    assert any("found no gaps" in m.text for m in state["messages"])


async def test_review_tokens_are_counted_under_the_review_role() -> None:
    review = judge({"security": [finding("security", ["EP-1"], "No auth")]}, usage=(100, 50))
    seam = at_review(review, tokens_used={"interview": 7, "review": 0})
    await seam.send("review please")
    assert (await seam.state())["tokens_used"] == {"interview": 7, "review": 4 * 150}


async def test_a_failed_reviewer_sets_last_error_and_retry_reruns_the_review() -> None:
    attempts = {"n": 0}

    def flaky(messages: list[BaseMessage], schema: Any) -> Any:
        if lens_of(messages) == "maintainability" and attempts["n"] == 0:
            attempts["n"] += 1
            error = Exception("schema rejected")
            error.status_code = 401  # type: ignore[attr-defined]
            return error
        return {"findings": []} if lens_of(messages) else {"gaps": []}

    draft = ScriptedChatModel.with_script(prd_out({"Short links": ["FR-1"]}))
    seam = at_review(RoutedChatModel.answering(flaky), draft)
    await seam.send("review please")
    state = await seam.state()
    assert (state["stage"], state["gaps"], state["last_error"]["code"]) == (
        "design_review",
        [],
        "model_error",
    )

    await seam.retry()
    state = await seam.state()
    assert (state["stage"], state["last_error"]) == ("prd_signoff", None)  # no gaps: on to the PRD


async def test_the_review_starts_when_step_5_is_approved() -> None:
    confirm = AIMessage(
        content="",
        tool_calls=[{"name": "confirm_step", "args": {"step": 5, "summary": "done"}, "id": "g5"}],
    )
    scorecard = {"dimensions": [{"dimension": d, "score": 3, "evidence": ["step 5 is done"], "advice": "a"}
                                for d in ("communication", "structure", "judgment", "depth", "time")]}  # fmt: skip
    interview = ScriptedChatModel.with_script(
        confirm, {"strengths": [], "bottlenecks": [], "questions": []}, scorecard
    )
    review = judge({"security": [finding("security", ["EP-1"], "No auth")]})
    seam = at_review(review, interview, stage="interview")
    seam.frontend_tools = [
        {
            "name": "confirm_step",
            "description": "",
            "parameters": {"type": "object", "properties": {}},
        }
    ]
    await seam.send("step 5 is done")
    await seam.answer("g5", '{"approved": true}')

    state = await seam.state()
    assert state["scorecard"] is not None
    assert state["stage"] == "gap_resolution" and [g["id"] for g in state["gaps"]] == ["GAP-1"]


def test_merge_rules() -> None:
    a = GapFinding.model_validate(finding("security", ["EP-1"], "Open endpoint", "low"))
    b = GapFinding.model_validate(finding("efficiency", ["EP-1"], "open endpoint!", "high"))
    assert combine([a, b]) == [b]
    assert held_to_inputs([a.model_copy(update={"item_ids": ["FR-1"]})], [a]) == []
    gaps = gap_register([a, b], [a, b], DESIGN, {"GAP": 3})
    assert [(g.id, g.severity) for g in gaps] == [("GAP-4", "high")]


async def test_the_parallel_review_runs_through_the_agent_endpoint() -> None:
    from langgraph.checkpoint.memory import InMemorySaver
    from service import event_types, post_run, run_input

    from blueprint.app import create_app
    from blueprint.assets import load_assets
    from blueprint.graph import build_graph
    from blueprint.models import RoleModels
    from blueprint.state import new_session_state

    review = judge({"security": [finding("security", ["EP-1"], "No auth")]})
    graph = build_graph(RoleModels(ScriptedChatModel(), review), InMemorySaver(), load_assets())
    initial = new_session_state("t", 10_000, True) | {
        "stage": "design_review", "design": DESIGN.model_dump(mode="json"), "id_counters": dict(COUNTERS),
    }  # fmt: skip
    await graph.aupdate_state({"configurable": {"thread_id": "t"}}, initial, as_node="__start__")

    events = await post_run(create_app(graph), run_input("t", []))

    assert event_types(events)[-1] == "RUN_FINISHED"
    values = (await graph.aget_state({"configurable": {"thread_id": "t"}})).values
    assert (values["stage"], [g["id"] for g in values["gaps"]]) == ("gap_resolution", ["GAP-1"])
    snapshot = [e for e in events if e["type"] == "STATE_SNAPSHOT"][-1]["snapshot"]
    assert snapshot["stage"] == "gap_resolution" and "review" not in snapshot
