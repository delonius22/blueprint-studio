"""Document import through the real graph with scripted models (SPEC-document-import §2, §7)."""

import json
from typing import Any

from fakes import ProviderError, ScriptedChatModel, tool_call
from langchain_core.messages import AIMessage, SystemMessage
from sample_files import BRIEF_MD, PNG
from seam import GraphSeam, at_step
from test_step_gate import CONFIRM_STEP, CRITIQUE

from blueprint.domain.models import Design, Requirement
from blueprint.graph.gates import REVIEW_IMPORT

FR: dict[str, Any] = {"quote": "Users shorten a long URL.", "locator": "Link shortener > Requirements", "updates": None,
      "weaknesses": [], "statement": "Users shorten a long URL"}  # fmt: skip
NFR: dict[str, Any] = {"quote": "Redirects must be fast.", "locator": "Link shortener > Requirements", "updates": None,
       "weaknesses": [{"code": "missing_target", "detail": "No latency target or unit"}],
       "category": "latency", "statement": "Redirects are fast", "metric": None, "target": None,
       "unit": None}  # fmt: skip
INVENTED = FR | {"quote": "Users pay monthly.", "statement": "Users pay monthly"}
COMPONENT: dict[str, Any] = {"quote": "Browser", "locator": "diagram 1", "updates": None, "weaknesses": [],
             "name": "Browser", "kind": "client", "responsibility": "Shows the app"}  # fmt: skip
PROPOSAL = {
    "summary": "A brief for a link shortener.",
    "functional_requirements": [FR, INVENTED],
    "non_functional_requirements": [NFR],
    "components": [COMPONENT],
    "open_questions": [
        {"step": 1, "quote": "Link analytics dashboards.", "locator": "Link shortener > Out of scope",
         "question": "Are click counts out of scope too?"},
    ],
    "prd_context": [{"topic": "goals", "quote": "Redirects must be fast.", "locator": "Link shortener > Requirements"}],
}  # fmt: skip


def card(state: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """The newest review_import call: its ID and the candidates it shows."""
    message = state["messages"][-1]
    assert isinstance(message, AIMessage)
    (call,) = message.tool_calls
    assert call["name"] == REVIEW_IMPORT and call["id"]
    return call["id"], call["args"]["candidates"]


def decide(*decisions: tuple[str, str, dict[str, Any]]) -> str:
    """A review_import answer: (candidate ID, accept|edit|reject, edited fields) per candidate."""
    rows = [{"candidate_id": c, "decision": d, "fields": f} for c, d, f in decisions]
    return json.dumps({"decisions": rows})


async def test_an_attached_brief_offers_this_steps_items_and_holds_the_rest() -> None:
    interview = ScriptedChatModel.with_script(
        PROPOSAL, AIMessage("What latency do redirects need, and are click counts out of scope?")
    )
    seam = GraphSeam(interview)

    state = await seam.attach("brief.md", BRIEF_MD.encode())

    call_id, shown = card(state)
    assert [(c["id"], c["list"]) for c in shown] == [
        ("IMP-1", "functional_requirements"),
        ("IMP-2", "non_functional_requirements"),
    ]  # the invented requirement was dropped; the component waits for Step 3
    assert shown[0]["quote"] == "Users shorten a long URL." and shown[0]["file"] == "brief.md"
    assert [(c["id"], c["status"]) for c in state["import_queue"]] == [
        ("IMP-1", "offered"), ("IMP-2", "offered"), ("IMP-3", "staged"),
    ]  # fmt: skip
    assert state["attachments"][0]["status"] == "imported"
    assert state["attachments"][0]["summary"] == "A brief for a link shortener."
    assert state["design"] == Design().model_dump(mode="json")  # nothing recorded yet
    assert "untrusted-file" in interview.calls[0].messages[1].text
    assert interview.calls[0].structured_method == "json_schema"

    state = await seam.answer(call_id, decide(("IMP-1", "accept", {}), ("IMP-2", "accept", {})))

    design = Design.model_validate(state["design"])
    assert [r.statement for r in design.functional_requirements] == ["Users shorten a long URL"]
    assert design.non_functional_requirements[0].id == "NFR-1"
    assert state["provenance"]["FR-1"] == {
        "attachment_id": "ATT-1", "locator": "Link shortener > Requirements",
        "quote": "Users shorten a long URL.",
    }  # fmt: skip
    assert [c["id"] for c in state["import_queue"]] == ["IMP-3"]
    assert state["prd_context"][0]["topic"] == "goals"
    summary = state["messages"][-2]
    assert summary.text.startswith("Recorded FR-1, NFR-1 from your files.")
    assert "waits for Step 3" in summary.text
    system = interview.calls[1].messages[0]
    assert isinstance(system, SystemMessage)
    assert "## Imported material" in system.text
    assert "- NFR-1 [missing_target] No latency target or unit" in system.text
    assert "Are click counts out of scope too?" in system.text
    assert [n["status"] for n in state["import_notes"]] == ["asked", "asked"]


async def test_staged_items_are_offered_when_their_step_opens() -> None:
    staged = {
        "id": "IMP-3", "attachment_id": "ATT-1", "step": 3, "tool": "upsert_component",
        "args": {"name": "Browser", "kind": "client", "responsibility": "Shows the app"},
        "source": {"attachment_id": "ATT-1", "locator": "diagram 1", "quote": "Browser"},
        "status": "staged",
    }  # fmt: skip
    initial = at_step(2) | {
        "import_queue": [staged],
        "attachments": [
            {"id": "ATT-1", "name": "brief.md", "role": "prd", "kind": "text", "status": "imported"}
        ],
    }
    seam = GraphSeam(
        ScriptedChatModel.with_script(
            tool_call("confirm_step", {"step": 2, "summary": "done"}, "gate-1"), CRITIQUE
        ),
        frontend_tools=[CONFIRM_STEP],
        initial=initial,
    )
    seam.files.add("session-1", "brief.md", BRIEF_MD.encode())
    await seam.send("Step 2 is complete")
    state = await seam.answer("gate-1", json.dumps({"approved": True}))

    assert state["current_step"] == 3
    _, shown = card(state)
    assert [c["id"] for c in shown] == ["IMP-3"]
    assert state["messages"][-2].text.startswith("**Step 2 critique**")


async def test_rejecting_everything_records_nothing() -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(PROPOSAL, AIMessage("Tell me about the users.")))
    call_id, _ = card(await seam.attach("brief.md", BRIEF_MD.encode()))

    state = await seam.answer(call_id, decide(("IMP-1", "reject", {}), ("IMP-2", "reject", {})))

    assert state["design"] == Design().model_dump(mode="json")
    assert state["provenance"] == {}
    assert state["messages"][-2].text.startswith("2 suggestions rejected.")


async def test_answering_in_the_chat_instead_puts_the_items_back_to_wait() -> None:
    interview = ScriptedChatModel.with_script(PROPOSAL, AIMessage("Sure, go on."))
    seam = GraphSeam(interview)
    await seam.attach("brief.md", BRIEF_MD.encode())

    state = await seam.send("Never mind the file for now.")

    assert {c["status"] for c in state["import_queue"]} == {"staged"}


async def test_an_import_updates_an_existing_item() -> None:
    design = Design(functional_requirements=[Requirement(id="FR-1", statement="Shorten URLs")])
    update = FR | {"updates": "FR-1"}
    interview = ScriptedChatModel.with_script(
        {"summary": "s", "functional_requirements": [update]}, AIMessage("ok")
    )
    seam = GraphSeam(interview, initial=at_step(1, design, {"FR": 1}))
    call_id, shown = card(await seam.attach("brief.md", BRIEF_MD.encode()))
    assert shown[0]["current"] == {"id": "FR-1", "statement": "Shorten URLs"}

    state = await seam.answer(
        call_id, decide(("IMP-1", "edit", {"statement": "Users shorten long URLs"}))
    )

    assert Design.model_validate(state["design"]).functional_requirements == [
        Requirement(id="FR-1", statement="Users shorten long URLs")
    ]
    assert state["id_counters"]["FR"] == 1


async def test_a_provider_failure_keeps_the_file_waiting_to_be_read() -> None:
    interview = ScriptedChatModel.with_script(*[ProviderError(500)] * 4)
    seam = GraphSeam(interview)

    state = await seam.attach("brief.md", BRIEF_MD.encode())

    assert state["last_error"]["code"] == "provider_error"
    assert state["attachments"][0]["status"] == "parsed"
    assert state["import_queue"] == []


async def test_a_spent_budget_stops_the_import() -> None:
    seam = GraphSeam(
        ScriptedChatModel.with_script(),
        initial={"tokens_used": {"interview": 10, "review": 0}},
        token_budget=10,
    )

    state = await seam.attach("brief.md", BRIEF_MD.encode())

    assert state["last_error"]["code"] == "budget_exhausted"
    assert state["attachments"][0]["status"] == "parsed"


async def test_an_image_is_sent_to_the_model_as_an_image() -> None:
    interview = ScriptedChatModel.with_script(
        {"summary": "A diagram", "components": [COMPONENT | {"quote": ""}]}, AIMessage("ok")
    )
    seam = GraphSeam(interview, initial=at_step(3))

    state = await seam.attach("arch.png", PNG)

    content = interview.calls[0].messages[1].content
    assert isinstance(content, list) and isinstance(content[1], dict)
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    _, shown = card(state)
    assert shown[0]["list"] == "components" and shown[0]["locator"] == "diagram 1"


async def test_removing_a_file_drops_what_still_waits_on_it() -> None:
    seam = GraphSeam(ScriptedChatModel.with_script(PROPOSAL, AIMessage("ok"), AIMessage("ok")))
    call_id, _ = card(await seam.attach("brief.md", BRIEF_MD.encode()))
    await seam.answer(call_id, decide(("IMP-1", "accept", {})))

    seam.files.remove("session-1", "ATT-1")
    state = await seam.send("I removed the file")

    assert state["attachments"][0]["status"] == "removed"
    assert state["import_queue"] == []
    assert Design.model_validate(state["design"]).functional_requirements[0].id == "FR-1"
