"""The browser cannot write session state (SPECS S2.15, S11.3): the canvas is read-only, and
a run starts from the checkpoint; the browser may only clear last_error for Retry (S11.6)."""

from typing import Any

from fakes import ScriptedChatModel
from langgraph.checkpoint.memory import InMemorySaver
from service import post_run, run_input

from blueprint.api.agent import browser_state
from blueprint.app import create_app
from blueprint.config.assets import load_assets
from blueprint.domain.models import Design, Requirement
from blueprint.domain.state import new_session_state
from blueprint.graph.build import build_graph
from blueprint.llm.clients import RoleModels

DESIGN = Design(functional_requirements=[Requirement(id="FR-1", statement="Shorten URLs")])


async def test_a_run_ignores_every_session_field_the_browser_sends() -> None:
    models = RoleModels(ScriptedChatModel(), ScriptedChatModel())
    graph = build_graph(models, InMemorySaver(), load_assets())
    initial = new_session_state("t", 1000, True) | {"design": DESIGN.model_dump(mode="json")}
    config: Any = {"configurable": {"thread_id": "t"}}
    await graph.aupdate_state(config, initial, as_node="__start__")
    sent = new_session_state("t", 10**9, True) | {
        "stage": "complete",
        "current_step": 5,
        "confirmed_steps": [1, 2, 3, 4, 5],
        "design": Design().model_dump(mode="json"),
        "id_counters": {"FR": 99},
    }

    await post_run(create_app(graph), run_input("t", [], state=sent))

    after = (await graph.aget_state(config)).values
    assert (after["stage"], after["current_step"], after["confirmed_steps"]) == ("interview", 1, [])
    assert (after["token_budget"], after["id_counters"]) == (1000, {})
    assert Design.model_validate(after["design"]) == DESIGN


def test_the_browser_may_clear_last_error_and_nothing_else() -> None:
    error = {"code": "provider_error", "message": "down", "retryable": True}
    checkpoint = new_session_state("t", 1000, True) | {"last_error": error}
    retried = browser_state(checkpoint, {"last_error": None, "stage": "complete", "messages": []})
    assert retried["last_error"] is None and retried["stage"] == "interview"
    assert retried["messages"] == []
    assert browser_state(checkpoint, {"stage": "complete"})["last_error"] == error
