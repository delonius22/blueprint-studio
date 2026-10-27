"""T-03: Step 1 — clarify requirements, recorded live as structured items (S2.4-S2.7, S2.15, S5.1-S5.4)."""

import json
from collections.abc import Sequence

import pytest
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from pydantic import ValidationError
from seam import GraphSeam

from blueprint.domain.models import (
    Component,
    Design,
    Entity,
    EntityField,
    Estimate,
    Flow,
    FlowStep,
    NfrTarget,
    Note,
    Relationship,
    Requirement,
    Spof,
)
from blueprint.interview.tools import violations

ARCHITECTURE_TOOLS = {"upsert_component", "upsert_flow", "upsert_storage_choice", "upsert_endpoint"}


def calls(*entries: tuple[str, dict[str, object]]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(entries)],
    )


def results(messages: Sequence[object]) -> list[dict[str, object]]:
    return [json.loads(m.text) for m in messages if isinstance(m, ToolMessage)]


async def test_step1_answers_are_recorded_as_items_with_ids() -> None:
    interview = ScriptedChatModel.with_script(
        calls(
            ("upsert_requirement", {"statement": "Users shorten a long URL"}),
            ("upsert_requirement", {"statement": "Visitors are redirected from a short URL"}),
            ("upsert_nfr", {"category": "latency", "statement": "Redirects are fast",
                            "metric": "p95 redirect latency", "target": 50, "unit": "ms"}),
            ("upsert_out_of_scope", {"text": "Link analytics dashboards"}),
            ("upsert_estimate", {"quantity": "Writes per second", "formula": "100M / 86400",
                                 "result": 1157.4, "unit": "writes/s"}),
        ),
        AIMessage("Recorded. What read/write ratio do you expect?"),
    )  # fmt: skip
    seam = GraphSeam(interview)

    await seam.send(
        "Users shorten URLs and visitors get redirected; p95 under 50 ms; no analytics."
    )

    design = await seam.design()
    assert [(r.id, r.statement) for r in design.functional_requirements] == [
        ("FR-1", "Users shorten a long URL"),
        ("FR-2", "Visitors are redirected from a short URL"),
    ]
    assert design.non_functional_requirements == [
        NfrTarget(id="NFR-1", category="latency", statement="Redirects are fast",
                  metric="p95 redirect latency", target=50, unit="ms")
    ]  # fmt: skip
    assert design.out_of_scope == [Note(id="OOS-1", text="Link analytics dashboards")]
    # S2.7: estimates keep their formula as well as their result
    assert design.capacity_estimates == [
        Estimate(id="EST-1", quantity="Writes per second", formula="100M / 86400",
                 result=1157.4, unit="writes/s")
    ]  # fmt: skip
    state = await seam.state()
    assert state["id_counters"] == {"FR": 2, "NFR": 1, "OOS": 1, "EST": 1}
    assert state["agent_design"] == state["design"]
    # the design_tools node ran the calls and returned to the interviewer
    assert len(interview.calls) == 2
    assert [r["recorded"] for r in results(interview.calls[1].messages)] == [
        "FR-1", "FR-2", "NFR-1", "OOS-1", "EST-1",
    ]  # fmt: skip
    assert (await seam.messages())[-1].text == "Recorded. What read/write ratio do you expect?"


async def test_ids_are_never_reused_after_deletion() -> None:
    interview = ScriptedChatModel.with_script(
        calls(
            ("upsert_requirement", {"statement": "a"}), ("upsert_requirement", {"statement": "b"})
        ),
        AIMessage("ok"),
        calls(("delete_item", {"item_id": "FR-2"}), ("upsert_requirement", {"statement": "c"})),
        AIMessage("ok"),
        calls(("upsert_requirement", {"id": "FR-1", "statement": "a, revised"})),
        AIMessage("ok"),
    )
    seam = GraphSeam(interview)
    await seam.send("two requirements")
    await seam.send("drop the second, add another")
    await seam.send("revise the first")

    design = await seam.design()
    assert [(r.id, r.statement) for r in design.functional_requirements] == [
        ("FR-1", "a, revised"),
        ("FR-3", "c"),
    ]


async def test_asking_for_a_redis_cache_in_step_1_records_nothing_architectural() -> None:
    interview = ScriptedChatModel.with_script(
        # even if the model tries, the tool is not bound and design_tools refuses it
        calls(
            (
                "upsert_component",
                {"name": "Redis cache", "kind": "cache", "responsibility": "cache"},
            )
        ),
        AIMessage("Before any architecture, who are the users and what is the read/write ratio?"),
    )
    seam = GraphSeam(interview)

    await seam.send("Add a Redis cache in front of the database.")

    bound = set(interview.calls[0].tools)
    assert not bound & ARCHITECTURE_TOOLS
    assert {"upsert_requirement", "upsert_nfr", "upsert_out_of_scope", "upsert_estimate"} <= bound
    assert results(interview.calls[1].messages) == [
        {"error": "upsert_component is not available now"}
    ]
    design = await seam.design()
    assert design == Design()
    assert (await seam.state())["id_counters"] == {}


async def test_invalid_tool_calls_change_nothing() -> None:
    interview = ScriptedChatModel.with_script(
        calls(
            ("upsert_requirement", {}),
            ("upsert_nfr", {"category": "speed", "statement": "fast"}),
            ("upsert_requirement", {"id": "FR-9", "statement": "x"}),
            ("delete_item", {"item_id": "FR-1"}),
            ("upsert_requirement", {"statement": "ok", "extra": 1}),
        ),
        AIMessage("Let me ask that again."),
    )
    seam = GraphSeam(interview)
    await seam.send("something")

    outcomes = results(interview.calls[1].messages)
    assert all("error" in outcome for outcome in outcomes)
    assert await seam.design() == Design()
    assert (await seam.state())["id_counters"] == {}


async def test_system_prompt_is_assembled_from_the_vendored_assets_in_order() -> None:
    interview = ScriptedChatModel.with_script(
        calls(("upsert_requirement", {"statement": "Users shorten a long URL"})),
        AIMessage("Next?"),
        AIMessage("Anything else?"),
    )
    seam = GraphSeam(interview)
    await seam.send("Users shorten URLs")
    await seam.send("That's all")

    system = interview.calls[2].messages[0]
    assert isinstance(system, SystemMessage)
    text = system.text
    parts = [
        seam.assets.interviewer_instructions.rstrip("\n"),
        seam.assets.course_context.rstrip("\n"),
        "Stage: interview",
        "Step: 1 of 5",
        "FR-1: Users shorten a long URL",
    ]
    positions = [text.find(part) for part in parts]
    assert all(p >= 0 for p in positions), positions
    assert positions == sorted(positions)
    assert text.startswith(parts[0])


# --- S2.7 shapes and S2.15 validation --------------------------------------------------------


def test_items_forbid_unknown_fields_and_require_their_fields() -> None:
    with pytest.raises(ValidationError):
        Requirement.model_validate({"id": "FR-1", "statement": "x", "priority": "high"})
    with pytest.raises(ValidationError):
        Estimate.model_validate({"id": "EST-1", "quantity": "q", "result": 1, "unit": "u"})
    with pytest.raises(ValidationError):
        NfrTarget.model_validate({"id": "NFR-1", "category": "speed", "statement": "x"})


def test_validation_names_every_violation() -> None:
    design = Design(
        functional_requirements=[
            Requirement(id="FR-1", statement="a"),
            Requirement(id="FR-1", statement="b"),
            Requirement(id="NFR-2", statement="c"),
            Requirement(id="FR-7", statement="d"),
        ],
        entities=[
            Entity(
                id="ENT-1",
                name="Url",
                fields=[EntityField(name="owner", type="id", key="fk", references="ENT-9")],
            )
        ],
        relationships=[
            Relationship(id="REL-1", from_entity="ENT-1", to_entity="ENT-2", cardinality="1:N")
        ],
        components=[Component(id="CMP-1", name="api", kind="service", responsibility="r")],
        flows=[
            Flow(
                id="FLW-1",
                name="read",
                kind="read",
                steps=[FlowStep(from_component="CMP-1", to_component="CMP-5", label="get")],
            )
        ],
        spofs=[Spof(id="SPOF-1", component_id="CMP-3", risk="down")],
    )
    counters = {"FR": 2, "ENT": 1, "REL": 1, "CMP": 1, "FLW": 1, "SPOF": 1}
    problems = violations(design, counters)
    assert problems == [
        "FR-1 is used more than once",
        "NFR-2 is not a valid FR- ID for functional_requirements",
        "FR-7 was never issued",
        "ENT-1.owner references ENT-9, which is not an entity",
        "REL-1 refers to ENT-2, which is not an entity",
        "FLW-1 refers to CMP-5, which is not a component",
        "SPOF-1 refers to CMP-3, which is not a component",
    ]
    assert violations(Design(), {}) == []


async def test_an_empty_design_tells_the_interviewer_to_record_the_brief_first() -> None:
    interview = ScriptedChatModel.with_script(
        calls(("upsert_requirement", {"statement": "Users shorten a long URL"})),
        AIMessage("How many links a day?"),
        AIMessage("And the read latency?"),
    )
    seam = GraphSeam(interview)
    await seam.send("A URL shortener where users shorten long URLs")
    await seam.send("About a million a day")

    opening = "## Opening"
    first, after_recording, next_turn = (c.messages[0].text for c in interview.calls)
    assert opening in first and "record every functional requirement" in first
    assert opening not in after_recording  # FR-1 is recorded: the brief has been taken in
    assert opening not in next_turn
