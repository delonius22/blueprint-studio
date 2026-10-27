"""The interview nodes: the interviewer, its design tools and the per-step critic (SPECS S5)."""

import json

from copilotkit.langgraph import copilotkit_customize_config
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from blueprint.domain.models import (
    AttachmentRef,
    Critique,
    Design,
    Gap,
    ImportCandidate,
    ImportNote,
    Model,
    Scorecard,
)
from blueprint.domain.state import DesignState
from blueprint.graph.context import Context, Update, ask, invalid_output, open_gate
from blueprint.graph.gates import (
    DECIDE_GAPS,
    REVIEW_IMPORT,
    backend_calls,
    close_unanswered,
    confirm_calls,
    frontend_actions,
    last_answer,
    last_message,
)
from blueprint.imports.proposal import (
    imported_material,
    mark_asked,
    offer,
    review_import_args,
    withdraw,
)
from blueprint.interview.prompts import critic_prompt, interviewer_prompt
from blueprint.interview.scoring import ScorecardError, make_scorecard
from blueprint.interview.tools import (
    Draft,
    ToolFailure,
    bound_tool_names,
    run_tool,
    step_blockers,
    tool_schemas,
)
from blueprint.llm.gateway import InvalidStructuredOutput, Meter, ModelCallFailed
from blueprint.review.resolution import accept_gaps, gap_answer_note, gap_followup, open_gaps
from blueprint.utils.models import dump, load
from blueprint.utils.text import transcript


class CritiqueDraft(Model):
    """What the critic model returns (S2.8 Critique without the step)."""

    strengths: list[str]
    bottlenecks: list[str]
    questions: list[str]


def format_critique(critique: Critique) -> str:
    """The critique as a chat message in the three-part format of FR-9."""

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) or "- (none)"

    return (
        f"**Step {critique.step} critique**\n\n"
        f"🟢 **Strengths & Alignment**\n{bullets(critique.strengths)}\n\n"
        f"⚠️ **Bottlenecks & Unaddressed Trade-Offs**\n{bullets(critique.bottlenecks)}\n\n"
        f"❓ **Probing / Next-Step Questions**\n{bullets(critique.questions)}"
    )


def format_scorecard(scorecard: Scorecard) -> str:
    """The final scorecard as a chat message (FR-9): score, quoted evidence, then advice."""
    parts = ["**Final scorecard**"]
    for score in scorecard.dimensions:
        quotes = "\n".join(f'> "{quote}"' for quote in score.evidence)
        parts.append(
            f"**{score.dimension.capitalize()}: {score.score}/4**\n\n{quotes}\n\nAdvice: {score.advice}"
        )
    return "\n\n".join(parts)


def draft_of(state: DesignState) -> Draft:
    """The design, ID counters and gaps a batch of tool calls changes."""
    return Draft(
        Design.model_validate(state["design"]), dict(state["id_counters"]), load(Gap, state, "gaps")
    )


async def interviewer(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """S5.2-S5.4: one interviewer turn on the interview model, with the tools of this step."""
    step, stage = state["current_step"], state["stage"]
    design = Design.model_validate(state["design"])
    gaps = load(Gap, state, "gaps")
    messages = list(state["messages"])
    update: Update = {}
    gap_note = None
    if stage == "gap_resolution":
        answer = last_answer(messages)
        decisions = answer[1] if answer and answer[0] == DECIDE_GAPS else None
        if decisions is not None:  # S6.5: acceptances apply here; answers go to the model
            gaps = accept_gaps(gaps, decisions)
            update["gaps"] = dump(gaps)
        gap_note = gap_answer_note(gaps, messages)
        if decisions is not None and gap_note is None:  # nothing to record: settle or ask again
            return update | await gap_followup(config, gaps)
    queue = load(ImportCandidate, state, "import_queue")
    if any(c.status == "offered" for c in queue):
        update["import_queue"] = dump(withdraw(queue))  # the user answered in the chat instead
    notes = load(ImportNote, state, "import_notes")
    imported = imported_material(load(AttachmentRef, state, "attachments"), notes, step)
    system = interviewer_prompt(ctx.assets, stage, step, design, gap_note, imported)
    # Design tools exist only while the design is being made (interview, gap answers).
    making = stage in ("interview", "gap_resolution")
    tools = (tool_schemas(bound_tool_names(step, stage)) if making else []) + frontend_actions(
        state
    )
    # Tool calls are not streamed to the browser: backend calls are internal, and a
    # confirm_step card may only open after design_tools has checked its blockers (S5.6).
    quiet = copilotkit_customize_config(config, emit_tool_calls=False)
    quiet["metadata"] = {**quiet.get("metadata", {}), "emit-tool-calls": False}
    meter = Meter.for_node(state, "interviewer")
    prompt = [SystemMessage(system), *close_unanswered(messages)]
    try:
        reply = await ctx.calls.chat(meter, "interview", prompt, quiet, tools, measure_ttft=True)
    except ModelCallFailed as failure:
        return {"last_error": failure.info()}  # S13.2: nothing else changes
    update |= {"messages": [reply], "tokens_used": meter.used, "last_error": None}
    if reply.tool_calls:
        return update
    if imported:
        update["import_notes"] = dump(mark_asked(notes, step))  # raised in this reply
    if stage == "gap_resolution":  # done for now: settle the stage or ask about what is open
        followup = await gap_followup(config, gaps)
        update |= {"stage": followup["stage"], "messages": [reply, *followup["messages"]]}
    return update


async def design_tools(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """S5.3, S5.6: run the interviewer's backend calls; open confirm_step unless it is blocked."""
    last = last_message(state)
    assert isinstance(last, AIMessage)
    draft = draft_of(state)
    allowed = bound_tool_names(state["current_step"], state["stage"])
    results: list[ToolMessage] = []
    for call in backend_calls(state, last):
        counters = dict(draft.counters)
        try:
            content = run_tool(call["name"], call["args"], draft, allowed)
        except ToolFailure as failure:
            draft.counters = counters
            content = json.dumps({"error": str(failure)})
        results.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
    for call in confirm_calls(last):
        blockers = step_blockers(state["current_step"], draft.design)
        if blockers:
            error = {
                "error": f"Step {state['current_step']} cannot be confirmed yet.",
                "blockers": blockers,
            }
            results.append(
                ToolMessage(json.dumps(error), tool_call_id=call["id"], name=call["name"])
            )
        else:
            await open_gate(config, last, call)
    update: Update = {
        "messages": results,
        "design": draft.design.model_dump(mode="json"),
        "id_counters": draft.counters,
        "gaps": dump(draft.gaps),
    }
    if state["stage"] == "gap_resolution" and not open_gaps(draft.gaps):
        update["stage"] = "prd_draft"  # S6.5: every gap answered or accepted
    return update


async def critic(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """S5.7, S5.8: confirm the step, critique it, and move on; files' items for the next step
    are offered as it opens (SPEC-document-import §2.5)."""
    step = state["current_step"]
    design = Design.model_validate(state["design"])
    meter = Meter.for_node(state, "critic")
    prompt = [
        SystemMessage(critic_prompt(ctx.assets, step, design)),
        HumanMessage("Conversation so far:\n\n" + transcript(state["messages"])),
    ]
    try:
        draft = await ctx.calls.structured(meter, "interview", CritiqueDraft, prompt, config)
    except ModelCallFailed as failure:
        return {"last_error": failure.info()}
    except InvalidStructuredOutput as invalid:
        return {"last_error": invalid_output(str(invalid)), "tokens_used": meter.used}
    critique = Critique(step=step, **draft.model_dump())
    update: Update = {
        "tokens_used": meter.used,
        "last_error": None,
        "confirmed_steps": sorted({*state["confirmed_steps"], step}),
        "current_step": min(step + 1, 5),
        "critiques": [*state["critiques"], critique.model_dump(mode="json")],
    }
    messages = [AIMessage(format_critique(critique))]
    if step == 5:
        try:
            scorecard = await make_scorecard(
                ctx.calls, meter, ctx.assets, design, state["messages"], config
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}  # S13.2: the critique is not stored either
        except ScorecardError as invalid:
            error = invalid_output(f"The scorecard could not be produced: {invalid}")
            return {"last_error": error, "tokens_used": meter.used}
        update |= {"scorecard": scorecard.model_dump(mode="json"), "stage": "design_review"}
        return update | {"messages": [*messages, AIMessage(format_scorecard(scorecard))]}
    queue = offer(load(ImportCandidate, state, "import_queue"), step + 1)
    if any(c.status == "offered" for c in queue):
        args = review_import_args(queue, load(AttachmentRef, state, "attachments"), design)
        text = f"Your files had more for Step {step + 1}; review it below."
        messages.append(await ask(config, REVIEW_IMPORT, args, text))
        update["import_queue"] = dump(queue)
    return update | {"messages": messages}
