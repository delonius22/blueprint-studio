"""T-04: step confirmation gate and per-step critique (S5.1, S5.7, S5.8, S2.8)."""

import json
from typing import Any

from fakes import ScriptedChatModel, tool_call
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END
from seam import GraphSeam

from blueprint.graph import route_design_tools, route_interviewer, route_start

CONFIRM_STEP = {
    "name": "confirm_step",
    "description": "Ask the user to confirm the current step.",
    "parameters": {
        "type": "object",
        "properties": {"step": {"type": "integer"}, "summary": {"type": "string"}},
        "required": ["step", "summary"],
    },
}
CRITIQUE = {
    "strengths": ["Clear functional scope (FR-1)"],
    "bottlenecks": ["No availability target yet"],
    "questions": ["What happens when a short code collides?"],
}


def confirm(step: int, call_id: str = "gate-1") -> AIMessage:
    return tool_call("confirm_step", {"step": step, "summary": f"Step {step} is done"}, call_id)


def gate_seam(*script: Any) -> GraphSeam:
    return GraphSeam(ScriptedChatModel.with_script(*script), frontend_tools=[CONFIRM_STEP])


async def test_the_run_ends_while_the_gate_call_is_unanswered() -> None:
    seam = gate_seam(confirm(1))

    await seam.send("I think requirements are complete")

    state = await seam.state()
    assert (state["current_step"], state["confirmed_steps"], state["critiques"]) == (1, [], [])
    last = state["messages"][-1]
    assert isinstance(last, AIMessage) and last.tool_calls[0]["name"] == "confirm_step"
    assert not any(isinstance(m, ToolMessage) for m in state["messages"])
    assert len(seam.interview.calls) == 1
    assert "confirm_step" in seam.interview.calls[0].tools


async def test_approval_confirms_the_step_and_stores_one_critique() -> None:
    seam = gate_seam(confirm(1), CRITIQUE)
    await seam.send("Requirements are complete")

    await seam.answer("gate-1", json.dumps({"approved": True}))

    state = await seam.state()
    assert state["confirmed_steps"] == [1]
    assert state["current_step"] == 2
    assert state["critiques"] == [{"step": 1, **CRITIQUE}]
    assert seam.interview.calls[-1].structured_method == "json_schema"
    assert seam.review.calls == []
    message = state["messages"][-1]
    assert isinstance(message, AIMessage) and not message.tool_calls
    for heading in (
        "Strengths & Alignment",
        "Bottlenecks & Unaddressed Trade-Offs",
        "Probing / Next-Step Questions",
    ):
        assert heading in message.text
    assert "What happens when a short code collides?" in message.text


async def test_rejection_passes_what_is_missing_to_the_interviewer_and_stays_on_the_step() -> None:
    seam = gate_seam(confirm(1), AIMessage("Understood — what availability do you need?"))
    await seam.send("Requirements are complete")

    rejection = json.dumps({"approved": False, "missing": "We never set an availability target"})
    await seam.answer("gate-1", rejection)

    state = await seam.state()
    assert (state["current_step"], state["confirmed_steps"], state["critiques"]) == (1, [], [])
    sent = seam.interview.calls[-1].messages
    assert isinstance(sent[-1], ToolMessage) and sent[-1].text == rejection
    assert state["messages"][-1].text == "Understood — what availability do you need?"


async def test_steps_advance_one_at_a_time_through_step_5() -> None:
    script: list[Any] = []
    for step in range(1, 6):
        script += [confirm(step, f"gate-{step}"), CRITIQUE]
    seam = gate_seam(*script)
    for step in range(1, 6):
        await seam.send(f"step {step} done")
        await seam.answer(f"gate-{step}", '{"approved": true}')
        state = await seam.state()
        assert state["confirmed_steps"] == list(range(1, step + 1))
        assert state["current_step"] == min(step + 1, 5)
    assert [c["step"] for c in state["critiques"]] == [1, 2, 3, 4, 5]


async def test_backend_calls_in_the_same_turn_run_but_the_gate_still_waits() -> None:
    both = AIMessage(
        content="",
        tool_calls=[
            {"name": "upsert_requirement", "args": {"statement": "Shorten URLs"}, "id": "c1"},
            {"name": "confirm_step", "args": {"step": 1, "summary": "done"}, "id": "gate-1"},
        ],
    )
    seam = gate_seam(both)

    await seam.send("Users shorten URLs; that's step 1")

    assert [r.statement for r in (await seam.design()).functional_requirements] == ["Shorten URLs"]
    assert len(seam.interview.calls) == 1  # did not return to the interviewer
    assert (await seam.state())["current_step"] == 1


def test_routing_is_a_pure_function_of_state() -> None:
    gate = confirm(1)

    def state(*messages: Any) -> Any:
        return {"messages": list(messages), "copilotkit": {"actions": [CONFIRM_STEP]}}

    approved = ToolMessage('{"approved": true}', tool_call_id="gate-1")
    rejected = ToolMessage('{"approved": false, "missing": "x"}', tool_call_id="gate-1")
    assert route_start(state(HumanMessage("hi"))) == "interviewer"
    assert route_start(state(HumanMessage("hi"), gate, approved)) == "critic"
    assert route_start(state(HumanMessage("hi"), gate, rejected)) == "interviewer"
    assert route_start(state(HumanMessage("hi"), AIMessage("reply"))) == END
    assert route_start(state()) == END
    assert route_interviewer(state(HumanMessage("hi"), gate)) == END
    assert route_interviewer(state(HumanMessage("hi"), AIMessage("text"))) == END
    assert (
        route_interviewer(state(HumanMessage("hi"), tool_call("upsert_requirement", {})))
        == "design_tools"
    )
    pending = AIMessage(
        content="",
        tool_calls=[
            {"name": "upsert_requirement", "args": {}, "id": "c1"},
            {"name": "confirm_step", "args": {}, "id": "gate-1"},
        ],
    )
    assert route_design_tools(state(pending, ToolMessage("{}", tool_call_id="c1"))) == END
    assert (
        route_design_tools(
            state(tool_call("upsert_requirement", {}, "c1"), ToolMessage("{}", tool_call_id="c1"))
        )
        == "interviewer"
    )
