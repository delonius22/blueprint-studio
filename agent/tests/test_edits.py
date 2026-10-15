"""T-09: direct canvas edits the interviewer notices (S2.5, S2.15, S5.9, S11.3)."""

import copy
from typing import Any

import pytest
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from seam import GraphSeam
from service import post_run, run_input

from blueprint.app import create_app
from blueprint.assets import load_assets
from blueprint.domain import Design, Note, Requirement
from blueprint.graph import build_graph
from blueprint.models import RoleModels
from blueprint.state import new_session_state

START_DESIGN = Design(
    functional_requirements=[Requirement(id="FR-1", statement="Shorten URLs")],
    out_of_scope=[Note(id="OOS-1", text="Analytics")],
)
START_COUNTERS = {"FR": 2, "OOS": 1}  # FR-2 was issued and later deleted


async def service(interview: ScriptedChatModel | None = None) -> tuple[Any, Any]:
    graph = build_graph(
        RoleModels(interview or ScriptedChatModel(), ScriptedChatModel()),
        InMemorySaver(),
        load_assets(),
    )
    initial = new_session_state("t", 1000, True) | {
        "design": START_DESIGN.model_dump(mode="json"),
        "agent_design": START_DESIGN.model_dump(mode="json"),
        "id_counters": START_COUNTERS,
    }
    await graph.aupdate_state({"configurable": {"thread_id": "t"}}, initial, as_node="__start__")
    return create_app(graph), graph


async def values(graph: Any) -> dict[str, Any]:
    return dict((await graph.aget_state({"configurable": {"thread_id": "t"}})).values)


def browser_state(**changes: Any) -> dict[str, Any]:
    """What the workspace sends: its copy of the state with the user's edits."""
    state = new_session_state("t", 1000, True) | {
        "design": START_DESIGN.model_dump(mode="json"),
        "id_counters": dict(START_COUNTERS),
    }
    return state | changes


def with_design(edit: Any) -> dict[str, Any]:
    design = START_DESIGN.model_dump(mode="json")
    edit(design)
    return design


async def test_a_valid_edit_is_saved_by_a_run_that_adds_no_message() -> None:
    app, graph = await service()
    design = with_design(
        lambda d: d["functional_requirements"].append({"id": "FR-3", "statement": "Redirect"})
    )

    await post_run(
        app, run_input("t", [], state=browser_state(design=design, id_counters={"FR": 3, "OOS": 1}))
    )

    saved = await values(graph)
    assert [r["id"] for r in saved["design"]["functional_requirements"]] == ["FR-1", "FR-3"]
    assert saved["id_counters"] == {"FR": 3, "OOS": 1}
    assert saved["last_error"] is None


@pytest.mark.parametrize(
    ("edit", "counters", "problem"),
    [
        (lambda d: d["functional_requirements"].append({"id": "OOS-9", "statement": "x"}), {"FR": 2, "OOS": 9},
         "OOS-9 is not a valid FR- ID for functional_requirements"),
        (lambda d: d["functional_requirements"].append({"id": "FR-5", "statement": "x"}), {"FR": 2, "OOS": 1},
         "FR-5 was never issued"),
        (lambda d: d["functional_requirements"].append({"id": "FR-2", "statement": "x"}), {"FR": 2, "OOS": 1},
         "FR-2 was issued before and cannot be reused"),
        (lambda d: d["functional_requirements"][0].update(priority="high"), {"FR": 2, "OOS": 1},
         "Extra inputs are not permitted"),
        (lambda d: d["relationships"].append({"id": "REL-1", "from_entity": "ENT-1", "to_entity": "ENT-2",
                                              "cardinality": "1:N"}), {"FR": 2, "OOS": 1, "REL": 1},
         "REL-1 refers to ENT-1, which is not an entity"),
        (lambda d: None, {"FR": 1, "OOS": 1}, "the FR counter cannot go back from 2"),
    ],
)  # fmt: skip
async def test_an_invalid_edit_keeps_the_old_state_and_sets_last_error(
    edit: Any, counters: dict[str, int], problem: str
) -> None:
    app, graph = await service()
    before = await values(graph)

    await post_run(
        app, run_input("t", [], state=browser_state(design=with_design(edit), id_counters=counters))
    )

    after = await values(graph)
    assert after["design"] == before["design"] and after["id_counters"] == before["id_counters"]
    assert after["last_error"]["code"] == "invalid_edit"
    assert problem in after["last_error"]["message"]
    assert after["last_error"]["retryable"] is False


async def test_the_browser_cannot_change_server_owned_fields() -> None:
    app, graph = await service()
    await post_run(
        app,
        run_input(
            "t",
            [],
            state=browser_state(
                stage="complete",
                current_step=5,
                confirmed_steps=[1, 2, 3, 4, 5],
                token_budget=10**9,
            ),
        ),
    )
    after = await values(graph)
    assert (
        after["stage"],
        after["current_step"],
        after["confirmed_steps"],
        after["token_budget"],
    ) == ("interview", 1, [], 1000)


async def test_a_valid_edit_clears_an_earlier_invalid_edit_error() -> None:
    app, graph = await service()
    bad = with_design(
        lambda d: d["functional_requirements"].append({"id": "FR-9", "statement": "x"})
    )
    await post_run(app, run_input("t", [], state=browser_state(design=bad)))
    assert (await values(graph))["last_error"]["code"] == "invalid_edit"

    good = with_design(lambda d: d["out_of_scope"].clear())
    await post_run(app, run_input("t", [], state=browser_state(design=good, last_error=None)))
    after = await values(graph)
    assert after["last_error"] is None and after["design"]["out_of_scope"] == []


async def test_the_next_interviewer_call_names_the_users_edits_and_agent_design_tracks_its_writes() -> (
    None
):
    interview = ScriptedChatModel.with_script(
        AIMessage("I see you added FR-3, changed FR-1 and deleted OOS-1."),
        AIMessage("Anything else?"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "upsert_requirement", "args": {"statement": "Expire links"}, "id": "c1"}
            ],
        ),
        AIMessage("Recorded FR-4."),
    )
    seam = GraphSeam(
        interview,
        initial={"design": START_DESIGN.model_dump(mode="json"), "agent_design": START_DESIGN.model_dump(mode="json"),
                 "id_counters": dict(START_COUNTERS)},
    )  # fmt: skip
    await seam._ensure_session("session-1")
    edited = copy.deepcopy(START_DESIGN.model_dump(mode="json"))
    edited["functional_requirements"][0]["statement"] = "Shorten long URLs"
    edited["functional_requirements"].append({"id": "FR-3", "statement": "Redirect"})
    edited["out_of_scope"] = []
    await seam.graph.aupdate_state(
        seam.config("session-1"), {"design": edited, "id_counters": {"FR": 3, "OOS": 1}}
    )

    await seam.send("Take a look at my edits")

    system = interview.calls[0].messages[0]
    assert isinstance(system, SystemMessage)
    assert "added FR-3; changed FR-1; deleted OOS-1" in system.text
    state = await seam.state()
    assert state["agent_design"] == state["design"] == edited

    await seam.send("No more edits")
    assert "edited the canvas" not in interview.calls[1].messages[0].text

    await seam.send("Links should expire")
    state = await seam.state()
    assert [r["id"] for r in state["design"]["functional_requirements"]] == ["FR-1", "FR-3", "FR-4"]
    assert state["agent_design"] == state["design"]  # the interviewer's own write is not an edit
    assert "edited the canvas" not in interview.calls[3].messages[0].text
