"""T-08: Steps 4-5 and the final scorecard (S2.7, S2.8, S5.3, S5.6, S5.8)."""

from collections.abc import Sequence
from typing import Any

import pytest
from fakes import ScriptedChatModel, calls, results
from langchain_core.messages import AIMessage, HumanMessage
from seam import GraphSeam, at_step

from blueprint.domain.models import (
    DIMENSIONS,
    Component,
    Design,
    FailureMode,
    Note,
    Signal,
    Spof,
    Tradeoff,
)
from blueprint.interview.scoring import ScorecardDraft, problems

CONFIRM_STEP = {
    "name": "confirm_step",
    "description": "Ask the user to confirm the current step.",
    "parameters": {
        "type": "object",
        "properties": {"step": {"type": "integer"}, "summary": {"type": "string"}},
        "required": ["step", "summary"],
    },
}
CRITIQUE = {"strengths": ["s"], "bottlenecks": ["b"], "questions": ["q"]}
BASE = Design(
    components=[Component(id="CMP-1", name="DB", kind="database", responsibility="store")],
    failure_modes=[FailureMode(id="FM-1", scenario="DB fails", behaviour="failover")],
)
COUNTERS = {"CMP": 1, "FM": 1}


def scorecard(
    evidence: str = "We fail over to a replica", order: Sequence[str] = DIMENSIONS
) -> dict[str, Any]:
    return {
        "dimensions": [
            {
                "dimension": d,
                "score": 2 + i % 3,
                "evidence": [evidence],
                "advice": f"Advice on {d}.",
            }
            for i, d in enumerate(order)
        ]
    }


async def test_spofs_signals_tradeoffs_and_extensions_are_recorded() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(
                (
                    "upsert_spof",
                    {
                        "component_id": "CMP-1",
                        "risk": "Single DB node",
                        "mitigation": "Multi-AZ replica",
                    },
                ),
                ("upsert_spof", {"component_id": "CMP-9", "risk": "unknown"}),
                (
                    "upsert_signal",
                    {
                        "kind": "alert",
                        "name": "p95 redirect latency",
                        "threshold": "> 50 ms for 5 min",
                    },
                ),
                (
                    "upsert_tradeoff",
                    {"decision": "AP reads", "gained": "availability", "sacrificed": "freshness"},
                ),
                ("upsert_extension", {"text": "Multi-region active-active at 10x"}),
            ),
            AIMessage("Good."),
        ),
        initial=at_step(4, BASE, COUNTERS),
    )
    await seam.send("record reliability")

    design = await seam.design()
    assert design.spofs == [
        Spof(
            id="SPOF-1", component_id="CMP-1", risk="Single DB node", mitigation="Multi-AZ replica"
        )
    ]
    assert "CMP-9, which is not a component" in str(
        results(seam.interview.calls[1].messages)[1]["error"]
    )
    assert design.observability == [
        Signal(id="OBS-1", kind="alert", name="p95 redirect latency", threshold="> 50 ms for 5 min")
    ]
    assert design.tradeoffs == [
        Tradeoff(id="TRD-1", decision="AP reads", gained="availability", sacrificed="freshness")
    ]
    assert design.extensions == [Note(id="EXT-1", text="Multi-region active-active at 10x")]


@pytest.mark.parametrize(
    ("spofs", "blocker"),
    [
        ([], "Step 4 needs at least one single point of failure (upsert_spof)."),
        (
            [
                Spof(id="SPOF-1", component_id="CMP-1", risk="r", mitigation="replica"),
                Spof(id="SPOF-2", component_id="CMP-1", risk="r"),
            ],
            "Step 4 needs a mitigation for every single point of failure: SPOF-2 has none.",
        ),
    ],
)
async def test_step_4_is_blocked_without_a_mitigated_spof(spofs: list[Spof], blocker: str) -> None:
    design = BASE.model_copy(update={"spofs": spofs})
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(("confirm_step", {"step": 4, "summary": "done"}), prefix="gate"),
            AIMessage("What fails?"),
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=at_step(4, design, COUNTERS | {"SPOF": 2}),
    )
    await seam.send("Step 4 is done")

    outcome = results(seam.interview.calls[1].messages)
    assert outcome == [{"error": "Step 4 cannot be confirmed yet.", "blockers": [blocker]}]
    assert (await seam.state())["current_step"] == 4


async def test_step_4_with_every_spof_mitigated_opens_the_card() -> None:
    design = BASE.model_copy(
        update={"spofs": [Spof(id="SPOF-1", component_id="CMP-1", risk="r", mitigation="replica")]}
    )
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(("confirm_step", {"step": 4, "summary": "done"}), prefix="gate")
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=at_step(4, design, COUNTERS | {"SPOF": 1}),
    )
    await seam.send("Step 4 is done")
    assert results((await seam.state())["messages"]) == []  # the gate waits for the user


async def test_step_5_approval_stores_the_scorecard_and_starts_the_design_review() -> None:
    reversed_order = list(reversed(DIMENSIONS))
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(("confirm_step", {"step": 5, "summary": "done"}), prefix="gate"),
            CRITIQUE,
            scorecard(order=[*DIMENSIONS[:4], "communication"]),  # "time" missing: corrected once
            scorecard(order=reversed_order),
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=at_step(5, BASE, COUNTERS),
    )
    await seam.send("We fail over to a replica. Trade-offs are recorded; step 5 is done.")
    await seam.answer("gate0", '{"approved": true}')

    state = await seam.state()
    assert state["stage"] == "design_review"
    assert state["confirmed_steps"] == [1, 2, 3, 4, 5]
    assert [c["step"] for c in state["critiques"]] == [5]
    card = state["scorecard"]
    assert [d["dimension"] for d in card["dimensions"]] == list(DIMENSIONS)
    assert all(1 <= d["score"] <= 4 and d["evidence"] and d["advice"] for d in card["dimensions"])
    retry = seam.interview.calls[-1].messages[-1]
    assert isinstance(retry, HumanMessage) and "could not be used" in retry.text
    assert "Final scorecard" in state["messages"][-1].text


async def test_a_scorecard_that_is_still_invalid_after_one_retry_is_not_stored() -> None:
    bad = scorecard(evidence="words nobody said")
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            calls(("confirm_step", {"step": 5, "summary": "done"}), prefix="gate"),
            CRITIQUE,
            bad,
            bad,
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=at_step(5, BASE, COUNTERS),
    )
    await seam.send("step 5 is done")
    await seam.answer("gate0", '{"approved": true}')

    state = await seam.state()
    assert (state["stage"], state["scorecard"], state["critiques"]) == ("interview", None, [])
    assert state["last_error"]["code"] == "invalid_output"
    assert "is not a verbatim quote" in state["last_error"]["message"]


@pytest.mark.parametrize(
    ("quotes_from", "accepted"),
    [
        ("user", ["I would shard by user"]),
        ("conversation", ["I would shard by user", "What about hot keys?"]),
    ],
)
def test_evidence_must_be_a_verbatim_quote_from_the_allowed_turns(
    quotes_from: Any, accepted: list[str]
) -> None:
    messages = [HumanMessage("I would  shard by USER id."), AIMessage("What about hot keys?")]
    for quote in ("I would shard by user", "What about hot keys?", "Use consistent hashing"):
        draft = ScorecardDraft.model_validate(scorecard(evidence=quote))
        assert (problems(draft, messages, quotes_from) == []) is (quote in accepted), (
            quotes_from,
            quote,
        )
