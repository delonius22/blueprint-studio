"""T-07: Step 3b — CAP stance, cache policies and the failure-mode gate (S2.7, S5.3, S5.6)."""

import json
from typing import Any

from fakes import ScriptedChatModel, calls, results
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from seam import GraphSeam, at_step
from service import post_run, run_input, user

from blueprint.app import create_app
from blueprint.config.assets import load_assets
from blueprint.domain.models import CachePolicy, CapStance, Design, FailureMode
from blueprint.domain.state import new_session_state
from blueprint.graph.build import build_graph
from blueprint.llm.clients import RoleModels

CONFIRM_STEP = {
    "name": "confirm_step",
    "description": "Ask the user to confirm the current step.",
    "parameters": {
        "type": "object",
        "properties": {"step": {"type": "integer"}, "summary": {"type": "string"}},
        "required": ["step", "summary"],
    },
}
FAILURE_MODE = {
    "scenario": "Primary DB fails",
    "behaviour": "Reads served from replicas",
    "recovery": "Promote replica",
}


async def test_cap_stance_cache_policies_and_failure_modes_are_recorded() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(
                ("set_cap_stance", {"choice": "AP", "rationale": "Redirects must stay up"}),
                ("upsert_cache_policy", {"data": "hot codes", "strategy": "cache-aside",
                                         "eviction": "LRU", "ttl_seconds": 3600}),
                ("upsert_failure_mode", FAILURE_MODE),
                ("set_cap_stance", {"choice": "mixed", "rationale": "AP reads, CP code creation"}),
            ),
            AIMessage("What about cache stampedes?"),
        ),
        initial=at_step(3),
    )  # fmt: skip
    await seam.send("AP, cache hot codes, and replicas take over if the primary fails")

    design = await seam.design()
    assert design.cap_stance == CapStance(choice="mixed", rationale="AP reads, CP code creation")
    assert design.cache_policies == [
        CachePolicy(
            id="CACHE-1", data="hot codes", strategy="cache-aside", eviction="LRU", ttl_seconds=3600
        )
    ]
    assert design.failure_modes == [FailureMode(id="FM-1", **FAILURE_MODE)]


async def test_confirming_step_3_without_a_failure_mode_returns_the_blocker() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(("confirm_step", {"step": 3, "summary": "Architecture done"}), prefix="gate"),
            AIMessage("Before we confirm: what happens if the primary database fails?"),
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=at_step(3),
    )
    await seam.send("Step 3 is done")

    blocker = results(seam.interview.calls[1].messages)
    assert blocker == [
        {
            "error": "Step 3 cannot be confirmed yet.",
            "blockers": ["Step 3 needs at least one failure mode (upsert_failure_mode)."],
        }
    ]
    state = await seam.state()
    assert (state["current_step"], state["confirmed_steps"]) == (3, [1, 2])
    assert state["messages"][-1].text.startswith("Before we confirm")


async def test_a_failure_mode_recorded_in_the_same_turn_clears_the_gate() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(
                ("upsert_failure_mode", FAILURE_MODE),
                ("confirm_step", {"step": 3, "summary": "Architecture done"}),
            ),
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=at_step(3),
    )
    await seam.send("If the primary fails we fail over; step 3 is done")

    state = await seam.state()
    assert results(state["messages"]) == [{"recorded": "FM-1"}]  # the gate call awaits the user
    assert len(seam.interview.calls) == 1


async def agent_app(script: list[Any], design: Design | None = None) -> Any:
    graph = build_graph(
        RoleModels(ScriptedChatModel.with_script(*script), ScriptedChatModel()),
        InMemorySaver(),
        load_assets(),
    )
    initial = new_session_state("t", 1000, True) | at_step(3, design, {"FM": 1} if design else None)
    await graph.aupdate_state({"configurable": {"thread_id": "t"}}, initial, as_node="__start__")
    return create_app(graph)


async def test_a_blocked_gate_opens_no_card_and_a_clear_gate_opens_one() -> None:
    gate = calls(("confirm_step", {"step": 3, "summary": "done"}), prefix="gate")
    blocked = await agent_app([gate, AIMessage("What happens if the database fails?")])
    events = await post_run(blocked, run_input("t", [user("Step 3 is done")], [CONFIRM_STEP]))
    assert not [e for e in events if e["type"] == "TOOL_CALL_START"]

    design = Design(failure_modes=[FailureMode(id="FM-1", **FAILURE_MODE)])
    clear = await agent_app([gate], design)
    events = await post_run(clear, run_input("t", [user("Step 3 is done")], [CONFIRM_STEP]))
    starts = [e for e in events if e["type"] == "TOOL_CALL_START"]
    assert [(e["toolCallName"], e["toolCallId"]) for e in starts] == [("confirm_step", "gate0")]
    args = "".join(e["delta"] for e in events if e["type"] == "TOOL_CALL_ARGS")
    assert json.loads(args) == {"step": 3, "summary": "done"}
