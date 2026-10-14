"""T-06: Step 3a — components, flows and blueprint framing (S2.7, S5.2, S5.3, FR-10)."""

import json
from collections.abc import Sequence

from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from seam import GraphSeam, at_step

from blueprint.domain import Component, Flow, FlowStep


def calls(*entries: tuple[str, dict[str, object]]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(entries)],
    )


def results(messages: Sequence[object]) -> list[dict[str, object]]:
    return [json.loads(m.text) for m in messages if isinstance(m, ToolMessage)]


COMPONENTS: list[tuple[str, dict[str, object]]] = [
    ("upsert_component", {"name": "Mobile app", "kind": "client", "responsibility": "UI"}),
    (
        "upsert_component",
        {"name": "API", "kind": "service", "responsibility": "Shorten and resolve"},
    ),
    ("upsert_component", {"name": "URL store", "kind": "database", "responsibility": "Mappings"}),
]


async def test_components_and_flows_are_recorded_with_ids() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(
                *COMPONENTS,
                ("upsert_flow", {"name": "Resolve", "kind": "read", "steps": [
                    {"from_component": "CMP-1", "to_component": "CMP-2", "label": "GET /{code}"},
                    {"from_component": "CMP-2", "to_component": "CMP-3", "label": "lookup"}]}),
            ),
            AIMessage("What happens when the URL store is down?"),
        ),
        initial=at_step(3),
    )  # fmt: skip
    await seam.send("Client calls the API, which reads the store")

    design = await seam.design()
    assert design.components[1] == Component(
        id="CMP-2", name="API", kind="service", responsibility="Shorten and resolve"
    )
    assert design.flows == [
        Flow(
            id="FLW-1",
            name="Resolve",
            kind="read",
            steps=[
                FlowStep(from_component="CMP-1", to_component="CMP-2", label="GET /{code}"),
                FlowStep(from_component="CMP-2", to_component="CMP-3", label="lookup"),
            ],
        )
    ]


async def test_flows_must_use_recorded_components_and_used_components_cannot_be_deleted() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(
                *COMPONENTS,
                ("upsert_flow", {"name": "Write", "kind": "write", "steps": [
                    {"from_component": "CMP-2", "to_component": "CMP-9", "label": "insert"}]}),
                ("upsert_flow", {"name": "Write", "kind": "write", "steps": [
                    {"from_component": "CMP-2", "to_component": "CMP-3", "label": "insert"}]}),
                ("delete_item", {"item_id": "CMP-3"}),
            ),
            AIMessage("ok"),
        ),
        initial=at_step(3),
    )  # fmt: skip
    await seam.send("record the write path")

    outcomes = results(seam.interview.calls[1].messages)
    assert outcomes[3] == {"error": "FLW-1 refers to CMP-9, which is not a component"}
    assert outcomes[4] == {"recorded": "FLW-1"}  # the rejected flow consumed no ID
    assert outcomes[5] == {
        "error": "cannot delete CMP-3: FLW-1 refers to CMP-3, which is not a component"
    }
    assert [c.id for c in (await seam.design()).components] == ["CMP-1", "CMP-2", "CMP-3"]


async def test_the_prompt_carries_the_blueprints_framed_as_patterns_to_consider() -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(AIMessage("ok")), initial=at_step(3))
    await seam.send("This looks like a chat app")

    system = seam.interview.calls[0].messages[0]
    assert isinstance(system, SystemMessage)
    for blueprint in (
        "Blueprint A: Music Streaming Platform",
        "Blueprint B: Hotel Reservation System",
        "Blueprint C: Real-Time Messaging Platform",
    ):
        assert blueprint in system.text
    assert "as something to consider, never as the answer" in system.text
    assert "Step: 3 of 5" in system.text
    tools = set(seam.interview.calls[0].tools)
    assert {"upsert_component", "upsert_flow"} <= tools
