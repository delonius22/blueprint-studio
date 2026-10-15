"""The LangGraph graph served at /agent (SPECS S4.1, S5).

Nodes do the work; routing functions are pure functions of state (S5.1).
"""

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from copilotkit.langgraph import copilotkit_customize_config
from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from blueprint.assets import Assets
from blueprint.design import (
    Draft,
    ToolFailure,
    bound_tool_names,
    run_tool,
    step_blockers,
    tool_schemas,
)
from blueprint.domain import (
    Critique,
    Design,
    Gap,
    Model,
    PrdDoc,
    PrdVersion,
    Scorecard,
    Seam,
    Ticket,
)
from blueprint.edits import edit_note
from blueprint.gates import (
    APPROVE_SEAMS,
    CONFIRM_STEP,
    DECIDE_GAPS,
    GATES,
    OPEN_GATE_EVENT,
    REVIEW_TICKETS,
    SIGN_OFF_PRD,
    close_unanswered,
    gap_decisions,
    gate_message,
    last_answer,
    latest_answer_to,
    pending_gate,
    step_approved,
)
from blueprint.llm import InvalidStructuredOutput, Meter, ModelCallFailed, ModelGateway
from blueprint.models import RoleModels
from blueprint.prd import (
    PrdDraftOut,
    build_prd,
    current_prd,
    draft_problems,
    drafter_messages,
    signoff_summary,
)
from blueprint.prompts import critic_prompt, interviewer_prompt, transcript
from blueprint.review import (
    LENSES,
    Findings,
    GapFinding,
    MergedGaps,
    cited,
    findings_payload,
    gap_register,
    merger_messages,
    review_summary,
    reviewer_messages,
)
from blueprint.scoring import ScorecardError, make_scorecard
from blueprint.spec import (
    SeamsOut,
    SpecOut,
    approved_seams,
    build_v1_1_draft,
    issue_seams,
    seam_decision,
    seam_messages,
    seam_problems,
    spec_problems,
    synthesizer_messages,
)
from blueprint.state import DesignState
from blueprint.tickets import (
    DagError,
    TicketDraft,
    TicketsOut,
    planner_messages,
    ticket_problems,
    tickets_summary,
    validate_dag,
)

Graph = CompiledStateGraph[DesignState, None, DesignState, DesignState]

REVIEWERS = [f"review_{lens}" for lens in LENSES]


def _merge_lenses(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class PlanningChannel(DesignState):
    """Graph-internal channel from the ticket planner to the DAG validator (S9.3): the draft
    tickets, the last DAG error and how many attempts were made. Not session state."""

    planning: dict[str, Any]


DAG_ATTEMPTS = 3


class ReviewChannel(DesignState):
    """Graph-internal channel for the parallel reviewers (S6.1): findings, tokens or an error
    per lens, gathered by the gap_merger. It is not part of the session state (S2.2)."""

    review: Annotated[dict[str, Any], _merge_lenses]


def frontend_actions(state: DesignState) -> list[dict[str, Any]]:
    """The frontend tools CopilotKit sent with this run (PRD OQ-2, QUESTIONS Q-6)."""
    copilotkit: Any = state.get("copilotkit") or {}
    return list(copilotkit.get("actions") or [])


def frontend_names(state: DesignState) -> set[str]:
    return {str(action.get("name")) for action in frontend_actions(state)}


def _last(state: DesignState) -> BaseMessage | None:
    messages = state.get("messages") or []
    return messages[-1] if messages else None


def _backend_calls(state: DesignState, message: AIMessage) -> list[dict[str, Any]]:
    frontend = frontend_names(state) | GATES
    return [dict(call) for call in message.tool_calls if call["name"] not in frontend]


def _open_gaps(gaps: list[Gap]) -> list[Gap]:
    return [g for g in gaps if g.status == "open"]


def decide_gaps_args(gaps: list[Gap]) -> dict[str, Any]:
    """What the decide_gaps card shows: every open gap (S6.5)."""
    keys = ("id", "lens", "severity", "item_ids", "risk", "decision_needed")
    return {"gaps": [{k: getattr(g, k) for k in keys} for g in _open_gaps(gaps)]}


def gap_answer_note(gaps: list[Gap], messages: list[Any]) -> str | None:
    """The open gaps the user answered in the newest decide_gaps card, for the interviewer."""
    answers = {
        d.gap_id: d.text
        for d in gap_decisions(latest_answer_to(messages, DECIDE_GAPS))
        if d.decision == "answer"
    }
    lines = [
        f"- {g.id} ({g.lens}, {g.severity}; items {', '.join(g.item_ids)}): risk: {g.risk} "
        f"Decision needed: {g.decision_needed} The user's answer: {answers[g.id]}"
        for g in _open_gaps(gaps)
        if answers.get(g.id, "").strip()
    ]
    if not lines:
        return None
    return (
        "The user answered these gaps from the design review. Record each answer as ordinary "
        "design items with your tools, using only what the user said, then call resolve_gap with "
        "the gap ID and the IDs of the items you recorded.\n" + "\n".join(lines)
    )


def _gate_calls(message: AIMessage) -> list[dict[str, Any]]:
    """confirm_step calls, which design_tools checks for blockers before any card opens (S5.6)."""
    return [dict(call) for call in message.tool_calls if call["name"] == CONFIRM_STEP]


# --- routing (pure) --------------------------------------------------------------------------


def route_start(state: DesignState) -> str | list[str]:
    """Route a new run by what the user just sent (S5.1).

    A chat message goes to the interviewer; an approved ``confirm_step`` goes to the
    critic (S5.7, S5.8); any other gate answer, including a rejection, goes to the
    interviewer. A run with nothing new ends at once (used to re-sync a thread).
    """
    if state.get("last_error"):
        return END
    if state.get("stage") == "design_review":
        return REVIEWERS  # the review runs (or re-runs after a failure)
    messages = list(state.get("messages") or [])
    answer = last_answer(messages)
    if answer is not None:
        name, content = answer
        if name == CONFIRM_STEP and step_approved(content):
            return "critic"
        if name == SIGN_OFF_PRD:
            return "prd_drafter"  # S7.3, S7.4
        if name == APPROVE_SEAMS:
            return "seam_proposer"  # S8.3, S8.4
        if name == REVIEW_TICKETS:
            return "completer" if content.get("decision") == "approve" else "ticket_planner"  # S9.4
        return "interviewer"
    stage = state.get("stage")
    if stage == "prd_draft":
        return "prd_drafter"
    if stage == "spec_synthesis":
        return "spec_synthesizer"
    if pending_gate(messages):
        return END  # a card is waiting: a run that adds nothing never opens it again
    if stage == "seam_gate" and not state.get("seams"):
        return "seam_proposer"
    if stage == "ticket_breakdown":
        return "ticket_planner"
    if isinstance(_last(state), HumanMessage):
        return "interviewer"
    return END


def route_critic(state: DesignState) -> str | list[str]:
    """After Step 5 the design review starts: three reviewers in parallel (S6.1)."""
    if state.get("last_error") or state.get("stage") != "design_review":
        return END
    return REVIEWERS


def route_interviewer(state: DesignState) -> str:
    """Backend calls and confirm_step go to design_tools; a text reply or an error ends the run,
    unless every gap is settled, when the PRD draft starts (S6.5)."""
    if state.get("last_error"):
        return END
    last = _last(state)
    if isinstance(last, AIMessage) and (_backend_calls(state, last) or _gate_calls(last)):
        return "design_tools"
    if state.get("stage") == "prd_draft":
        return "prd_drafter"
    return END


def route_prd_drafter(state: DesignState) -> str:
    """Sign-off starts the to-spec synthesis (S7.4, S8.1)."""
    if not state.get("last_error") and state.get("stage") == "spec_synthesis":
        return "spec_synthesizer"
    return END


def route_seam_proposer(state: DesignState) -> str:
    """Approved seams with no proposed changes go straight to the tickets (S8.4)."""
    if not state.get("last_error") and state.get("stage") == "ticket_breakdown":
        return "ticket_planner"
    return END


def route_ticket_planner(state: DesignState) -> str:
    return END if state.get("last_error") else "dag_validator"


def route_dag_validator(state: PlanningChannel) -> str:
    """S9.3: invalid edges go back to the planner with the error (a bounded number of times)."""
    planning = state.get("planning") or {}
    if not state.get("last_error") and planning.get("error"):
        return "ticket_planner"
    return END


def route_spec_synthesizer(state: DesignState) -> str:
    return END if state.get("last_error") else "seam_proposer"


def route_gap_merger(state: DesignState) -> str:
    """Zero gaps goes straight to the PRD draft (S6.4)."""
    if not state.get("last_error") and state.get("stage") == "prd_draft":
        return "prd_drafter"
    return END


def route_design_tools(state: DesignState) -> str:
    """Back to the interviewer, unless a frontend gate call from the same turn awaits the user."""
    messages = state.get("messages") or []
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    turn = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    if turn and any(call["id"] not in answered for call in turn.tool_calls):
        return END
    return "interviewer"


def utc_now() -> str:
    """ISO 8601 UTC, to the second: the approval time a PRD version is frozen with (S2.12)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def gap_followup(gaps: list[Gap]) -> dict[str, Any]:
    """After gap decisions: prd_draft when none is open, else a new decide_gaps card."""
    if not _open_gaps(gaps):
        settled = AIMessage("Every gap is answered or accepted. Next, the PRD draft.")
        return {"stage": "prd_draft", "messages": [settled]}
    open_count = len(_open_gaps(gaps))
    text = f"{open_count} gap{'s are' if open_count != 1 else ' is'} still open; answer or accept {'each' if open_count != 1 else 'it'}."
    message, call = gate_message(DECIDE_GAPS, decide_gaps_args(gaps), text)
    return {"stage": "gap_resolution", "messages": [message], "_gate": (message, call)}


async def opened(config: RunnableConfig, update: dict[str, Any] | None = None) -> dict[str, Any]:
    """Open the gate a gap_followup prepared (if any); returns nothing to write."""
    if update and "_gate" in update:
        message, call = update.pop("_gate")
        await open_gate(config, message, call)
    return {}


async def open_gate(config: RunnableConfig, message: AIMessage, call: dict[str, Any]) -> None:
    """Stream a gate tool call to the browser so its card opens (S5.6, S11.4)."""
    await adispatch_custom_event(
        OPEN_GATE_EVENT,
        {"id": call["id"], "name": call["name"], "args": call["args"], "message_id": message.id},
        config=config,
    )


# --- critique ------------------------------------------------------------------------------


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


# --- nodes -----------------------------------------------------------------------------------


def build_graph(
    models: RoleModels,
    checkpointer: BaseCheckpointSaver[Any],
    assets: Assets,
    gateway: ModelGateway | None = None,
) -> Graph:
    calls = gateway or ModelGateway(models)

    async def interviewer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        step = state["current_step"]
        stage = state["stage"]
        design = Design.model_validate(state["design"])
        gaps = [Gap.model_validate(g) for g in state.get("gaps") or []]
        update: dict[str, Any] = {}
        answer = last_answer(list(state["messages"]))
        if stage == "gap_resolution" and answer and answer[0] == DECIDE_GAPS:
            # S6.5: acceptances are applied here; answers go to the model to record.
            for decision in gap_decisions(answer[1].get("decisions")):
                index = next((i for i, g in enumerate(gaps) if g.id == decision.gap_id), None)
                if (
                    index is not None
                    and gaps[index].status == "open"
                    and decision.decision == "accept"
                ):
                    gaps[index] = gaps[index].model_copy(
                        update={"status": "accepted", "note": decision.text.strip() or None}
                    )
            update["gaps"] = [g.model_dump(mode="json") for g in gaps]
            note = gap_answer_note(gaps, list(state["messages"]))
            if note is None:  # nothing to record: settle the stage or ask about what is left
                followup = gap_followup(gaps)
                await opened(config, followup)
                return update | followup
        seen = Design.model_validate(state["agent_design"]) if state.get("agent_design") else None
        gap_note = (
            gap_answer_note(gaps, list(state["messages"])) if stage == "gap_resolution" else None
        )
        system = interviewer_prompt(assets, stage, step, design, edit_note(seen, design), gap_note)
        # Design tools exist only while the design is being made (interview, gap answers).
        backend = (
            tool_schemas(bound_tool_names(step, stage))
            if stage in ("interview", "gap_resolution")
            else []
        )
        tools = backend + frontend_actions(state)
        # Tool calls are not streamed to the browser: backend calls are internal, and a
        # confirm_step card may only open after design_tools has checked its blockers (S5.6).
        quiet = copilotkit_customize_config(config, emit_tool_calls=False)
        quiet["metadata"] = {**quiet.get("metadata", {}), "emit-tool-calls": False}
        meter = Meter.for_node(state, "interviewer")
        try:
            reply = await calls.chat(
                meter,
                "interview",
                [SystemMessage(system), *close_unanswered(state["messages"])],
                quiet,
                tools,
                measure_ttft=True,
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}  # S13.2: nothing else changes
        # S5.9: the interviewer has now seen this design, including the user's edits.
        update |= {
            "messages": [reply],
            "tokens_used": meter.used,
            "last_error": None,
            "agent_design": design.model_dump(mode="json"),
        }
        if stage == "gap_resolution" and not reply.tool_calls:
            # The interviewer is done for now: settle the stage or ask about the open gaps again.
            followup = gap_followup(gaps)
            update["stage"] = followup.get("stage", stage)
            update["messages"] = [reply, *followup.get("messages", [])]
            await opened(config, followup)
        return update

    async def design_tools(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        last = _last(state)
        assert isinstance(last, AIMessage)
        draft = Draft(
            Design.model_validate(state["design"]),
            dict(state["id_counters"]),
            [Gap.model_validate(g) for g in state.get("gaps") or []],
        )
        allowed = bound_tool_names(state["current_step"], state["stage"])
        results: list[ToolMessage] = []
        for call in _backend_calls(state, last):
            counters = dict(draft.counters)
            try:
                content = run_tool(call["name"], call["args"], draft, allowed)
            except ToolFailure as failure:
                draft.counters = counters
                content = json.dumps({"error": str(failure)})
            results.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
        for call in _gate_calls(last):
            blockers = step_blockers(state["current_step"], draft.design)
            if blockers:
                content = json.dumps(
                    {
                        "error": f"Step {state['current_step']} cannot be confirmed yet.",
                        "blockers": blockers,
                    }
                )
                results.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
            else:
                await open_gate(config, last, call)
        written = draft.design.model_dump(mode="json")
        update: dict[str, Any] = {
            "messages": results,
            "design": written,
            "agent_design": written,
            "id_counters": draft.counters,
            "gaps": [g.model_dump(mode="json") for g in draft.gaps],
        }
        if state["stage"] == "gap_resolution" and not _open_gaps(draft.gaps):
            update["stage"] = "prd_draft"  # S6.5: every gap answered or accepted
        return update

    async def critic(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        """S5.7 approval and S5.8 critique: confirm the step, critique it, move on."""
        step = state["current_step"]
        design = Design.model_validate(state["design"])
        meter = Meter.for_node(state, "critic")
        try:
            draft = await calls.structured(
                meter,
                "interview",
                CritiqueDraft,
                [
                    SystemMessage(critic_prompt(assets, step, design)),
                    HumanMessage("Conversation so far:\n\n" + transcript(state["messages"])),
                ],
                config,
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}
        except InvalidStructuredOutput as invalid:
            error = ModelCallFailed("invalid_output", str(invalid), retryable=True)
            return {"last_error": error.info(), "tokens_used": meter.used}
        critique = Critique(step=step, **draft.model_dump())
        update: dict[str, Any] = {
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
                    calls, meter, assets, design, state["messages"], config
                )
            except ModelCallFailed as failure:
                return {"last_error": failure.info()}  # S13.2: the critique is not stored either
            except ScorecardError as invalid:
                error = ModelCallFailed(
                    "invalid_output",
                    f"The scorecard could not be produced: {invalid}",
                    retryable=True,
                )
                return {"last_error": error.info(), "tokens_used": meter.used}
            update |= {
                "scorecard": scorecard.model_dump(mode="json"),
                "stage": "design_review",
                "tokens_used": meter.used,
            }
            messages.append(AIMessage(format_scorecard(scorecard)))
        return update | {"messages": messages}

    def reviewer(lens: Any) -> Any:
        async def review(state: ReviewChannel, config: RunnableConfig) -> dict[str, Any]:
            meter = Meter.for_node(state, f"review_{lens}")
            spent = meter.used.get("review", 0)
            design = Design.model_validate(state["design"])
            try:
                result = await calls.structured(
                    meter, "review", Findings, reviewer_messages(assets, lens, design), config
                )
                entry: dict[str, Any] = {"findings": findings_payload(result.findings, lens)}
            except ModelCallFailed as failure:
                entry = {"error": failure.info()}
            except InvalidStructuredOutput as invalid:
                entry = {
                    "error": ModelCallFailed("invalid_output", str(invalid), retryable=True).info()
                }
            entry["tokens"] = meter.used.get("review", 0) - spent
            return {"review": {lens: entry}}

        return review

    async def gap_merger(state: ReviewChannel, config: RunnableConfig) -> dict[str, Any]:
        """S6.4: merge the three lists on the review model, then hold the result to the rules."""
        review = state.get("review") or {}
        meter = Meter.for_node(state, "gap_merger")
        meter.used["review"] = meter.used.get("review", 0) + sum(
            int((review.get(lens) or {}).get("tokens", 0)) for lens in LENSES
        )
        errors = [review[lens]["error"] for lens in LENSES if (review.get(lens) or {}).get("error")]
        missing = [lens for lens in LENSES if lens not in review]
        if errors or missing:
            error = (
                errors[0]
                if errors
                else ModelCallFailed(
                    "review_incomplete",
                    "The design review did not finish; retry it.",
                    retryable=True,
                ).info()
            )
            return {"last_error": error, "tokens_used": meter.used}
        design = Design.model_validate(state["design"])
        findings = [
            GapFinding.model_validate(f) for lens in LENSES for f in review[lens]["findings"]
        ]
        inputs = cited(findings, design)
        counters = dict(state["id_counters"])
        gaps = []
        if inputs:
            try:
                merged = await calls.structured(
                    meter, "review", MergedGaps, merger_messages(assets, design, inputs), config
                )
            except ModelCallFailed as failure:
                return {"last_error": failure.info(), "tokens_used": meter.used}
            except InvalidStructuredOutput as invalid:
                error = ModelCallFailed("invalid_output", str(invalid), retryable=True)
                return {"last_error": error.info(), "tokens_used": meter.used}
            gaps = gap_register(merged.gaps, inputs, design, counters)
        update = {
            "gaps": [gap.model_dump(mode="json") for gap in gaps],
            "id_counters": counters,
            "stage": "gap_resolution" if gaps else "prd_draft",
            "tokens_used": meter.used,
            "last_error": None,
            "messages": [AIMessage(review_summary(gaps))],
        }
        if gaps:
            message, call = gate_message(DECIDE_GAPS, decide_gaps_args(gaps), review_summary(gaps))
            update["messages"] = [message]
            await open_gate(config, message, call)
        return update

    async def prd_drafter(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        """S7.1-S7.4: draft PRD v1.0, open sign_off_prd, and act on the user's answer."""
        previous = PrdDoc.model_validate(state["prd_draft"]) if state.get("prd_draft") else None
        answer = last_answer(list(state["messages"]))
        reason = None
        if answer is not None and answer[0] == SIGN_OFF_PRD and state["stage"] == "prd_signoff":
            if step_approved(answer[1]) and previous is not None:
                version = PrdVersion(version="1.0", approved_at=utc_now(), doc=previous)
                return {
                    "prd_versions": [*state["prd_versions"], version.model_dump(mode="json")],
                    "stage": "spec_synthesis",
                    "last_error": None,
                    "messages": [
                        AIMessage("PRD v1.0 is signed off and frozen. You can download it now.")
                    ],
                }
            reason = str(answer[1].get("reason") or "").strip() or "The user rejected the draft."
        design = Design.model_validate(state["design"])
        gaps = [Gap.model_validate(g) for g in state.get("gaps") or []]
        accepted = [g for g in gaps if g.status == "accepted"]
        counters = dict(state["id_counters"])
        meter = Meter.for_node(state, "prd_drafter")
        prompt = drafter_messages(design, accepted, previous, reason)
        problems: list[str] = []
        try:
            for _attempt in range(2):  # S7.2: one corrective retry
                try:
                    out = await calls.structured(meter, "interview", PrdDraftOut, prompt, config)
                    problems = draft_problems(out, design, accepted)
                except InvalidStructuredOutput as invalid:
                    problems = [str(invalid)]
                if not problems:
                    break
                prompt = [
                    *prompt,
                    HumanMessage(
                        "Your draft could not be used. Fix these and answer again:\n- "
                        + "\n- ".join(problems)
                    ),
                ]
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}
        if problems:
            error = ModelCallFailed(
                "invalid_output",
                "The PRD draft broke its rules: " + "; ".join(problems),
                retryable=True,
            )
            return {"last_error": error.info(), "tokens_used": meter.used}
        doc = build_prd(out, design, accepted, counters, previous)
        features_of = {g.id: g.feature_ids for g in doc.open_gaps}
        message, call = gate_message(
            SIGN_OFF_PRD, {"prd": doc.model_dump(mode="json")}, signoff_summary(doc)
        )
        await open_gate(config, message, call)
        return {
            "prd_draft": doc.model_dump(mode="json"),
            "gaps": [
                g.model_copy(
                    update={"feature_ids": features_of.get(g.id, g.feature_ids)}
                ).model_dump(mode="json")
                for g in gaps
            ],
            "id_counters": counters,
            "stage": "prd_signoff",
            "tokens_used": meter.used,
            "last_error": None,
            "messages": [message],
        }

    async def structured_with_retry(
        meter: Meter, schema: Any, prompt: list[Any], check: Any, config: RunnableConfig
    ) -> Any:
        """One structured call plus one corrective retry; returns (output, problems)."""
        problems: list[str] = []
        out = None
        for _attempt in range(2):
            try:
                out = await calls.structured(meter, "interview", schema, prompt, config)
                problems = check(out)
            except InvalidStructuredOutput as invalid:
                problems = [str(invalid)]
            if not problems:
                break
            prompt = [
                *prompt,
                HumanMessage(
                    "Your answer could not be used. Fix these and answer again:\n- "
                    + "\n- ".join(problems)
                ),
            ]
        return out, problems

    async def spec_synthesizer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        """S8.1, S8.2: extend the signed-off PRD into the v1.1 draft with to-spec."""
        signed = PrdDoc.model_validate(state["prd_versions"][-1]["doc"])
        design = Design.model_validate(state["design"])
        counters = dict(state["id_counters"])
        meter = Meter.for_node(state, "spec_synthesizer")
        prompt = synthesizer_messages(assets, signed, design, list(state["messages"]))
        try:
            out, problems = await structured_with_retry(
                meter, SpecOut, prompt, lambda o: spec_problems(o, signed), config
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}
        if problems:
            error = ModelCallFailed(
                "invalid_output",
                "The PRD v1.1 synthesis broke its rules: " + "; ".join(problems),
                retryable=True,
            )
            return {"last_error": error.info(), "tokens_used": meter.used}
        draft, changes = build_v1_1_draft(out, signed, counters)
        return {
            "prd_draft": draft.model_dump(mode="json"),
            "proposed_changes": [c.model_dump(mode="json") for c in changes],
            "seams": [],
            "id_counters": counters,
            "stage": "seam_gate",
            "tokens_used": meter.used,
            "last_error": None,
        }

    async def seam_proposer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        """S8.3, S8.4: propose the test seams, and act on the user's approval or feedback."""
        draft = PrdDoc.model_validate(state["prd_draft"])
        proposed = [Seam.model_validate(s) for s in state.get("seams") or []]
        counters = dict(state["id_counters"])
        answer = last_answer(list(state["messages"]))
        feedback = None
        if answer is not None and answer[0] == APPROVE_SEAMS and state["stage"] == "seam_gate":
            if step_approved(answer[1]):
                seams = approved_seams(answer[1].get("seams"), proposed, counters) or proposed
                final = draft.model_copy(
                    update={"testing_decisions": [seam_decision(s) for s in seams]}
                )
                version = PrdVersion(version="1.1", approved_at=utc_now(), doc=final)
                changes = state.get("proposed_changes") or []
                return {
                    "seams": [s.model_dump(mode="json") for s in seams],
                    "prd_draft": final.model_dump(mode="json"),
                    "prd_versions": [*state["prd_versions"], version.model_dump(mode="json")],
                    "id_counters": counters,
                    "stage": "change_review" if changes else "ticket_breakdown",
                    "last_error": None,
                    "messages": [
                        AIMessage(
                            "The seams are approved and PRD v1.1 is frozen. You can download it now."
                        )
                    ],
                }
            feedback = (
                str(answer[1].get("feedback") or "").strip()
                or "The user asked for different seams."
            )
        meter = Meter.for_node(state, "seam_proposer")
        prompt = seam_messages(assets, draft, feedback, proposed)
        try:
            out, problems = await structured_with_retry(
                meter, SeamsOut, prompt, lambda o: seam_problems(o.seams, draft), config
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}
        if problems:
            error = ModelCallFailed(
                "invalid_output",
                "The seam proposal broke its rules: " + "; ".join(problems),
                retryable=True,
            )
            return {"last_error": error.info(), "tokens_used": meter.used}
        seams = issue_seams(out.seams, counters)
        text = f"I propose {len(seams)} test seam{'s' if len(seams) != 1 else ''}. Approve them, edit them, or tell me what to change."
        message, call = gate_message(
            APPROVE_SEAMS, {"seams": [s.model_dump(mode="json") for s in seams]}, text
        )
        await open_gate(config, message, call)
        return {
            "seams": [s.model_dump(mode="json") for s in seams],
            "id_counters": counters,
            "stage": "seam_gate",
            "tokens_used": meter.used,
            "last_error": None,
            "messages": [message],
        }

    async def ticket_planner(state: PlanningChannel, config: RunnableConfig) -> dict[str, Any]:
        """S9.1, S9.2, S9.4: break the current PRD into tickets with to-tickets."""
        prd = current_prd(state["prd_versions"])
        assert prd is not None
        planning = dict(state.get("planning") or {})
        answer = last_answer(list(state["messages"]))
        instructions = None
        if answer is not None and answer[0] == REVIEW_TICKETS:
            instructions = (
                str(answer[1].get("instructions") or "").strip() or "Revise the breakdown."
            )
            planning = {}
        attempts = int(planning.get("attempts", 0)) + 1
        if attempts > DAG_ATTEMPTS:
            error = ModelCallFailed(
                "invalid_output",
                f"The ticket breakdown kept invalid blocking edges: {planning.get('error')}",
                retryable=True,
            )
            return {"last_error": error.info(), "planning": {}}
        current = [Ticket.model_validate(t) for t in state.get("tickets") or []]
        previous = [TicketDraft.model_validate(t) for t in planning.get("drafts") or []]
        prompt = planner_messages(
            assets, prd, current, instructions, planning.get("error"), previous
        )
        meter = Meter.for_node(state, "ticket_planner")
        try:
            out, problems = await structured_with_retry(
                meter, TicketsOut, prompt, lambda o: ticket_problems(o.tickets, prd), config
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}
        if problems:
            error = ModelCallFailed(
                "invalid_output",
                "The ticket breakdown broke its rules: " + "; ".join(problems),
                retryable=True,
            )
            return {"last_error": error.info(), "tokens_used": meter.used, "planning": {}}
        return {
            "planning": {
                "drafts": [t.model_dump() for t in out.tickets],
                "error": None,
                "attempts": attempts,
            },
            "stage": "ticket_breakdown",
            "tokens_used": meter.used,
            "last_error": None,
        }

    async def dag_validator(state: PlanningChannel, config: RunnableConfig) -> dict[str, Any]:
        """S9.3: check the blocking edges, renumber in build order, and ask for review."""
        planning = dict(state.get("planning") or {})
        drafts = [TicketDraft.model_validate(t) for t in planning.get("drafts") or []]
        try:
            tickets = validate_dag(drafts)
        except DagError as invalid:
            return {"planning": planning | {"error": str(invalid)}}
        message, call = gate_message(
            REVIEW_TICKETS,
            {"tickets": [t.model_dump(mode="json") for t in tickets]},
            tickets_summary(tickets),
        )
        await open_gate(config, message, call)
        return {
            "tickets": [t.model_dump(mode="json") for t in tickets],
            "id_counters": dict(state["id_counters"]) | {"T": len(tickets)},
            "stage": "ticket_gate",
            "planning": {},
            "messages": [message],
        }

    async def completer(state: DesignState) -> dict[str, Any]:
        """S9.4: approval completes the session; one message lists the downloads."""
        versions = ", ".join(f"PRD v{v['version']}.docx" for v in state["prd_versions"])
        return {
            "tickets_approved_at": utc_now(),
            "stage": "complete",
            "last_error": None,
            "messages": [
                AIMessage(
                    "The ticket breakdown is approved and the session is complete. Your downloads are "
                    f"ready: {versions}, Requirements.docx, UserStories.docx and context.md (the Jira "
                    "hand-off), or all of them as one zip from the completion view."
                )
            ],
        }

    builder = StateGraph(DesignState)
    builder.add_node("interviewer", interviewer)
    builder.add_node("design_tools", design_tools)
    builder.add_node("critic", critic)
    for lens, name in zip(LENSES, REVIEWERS, strict=True):
        builder.add_node(name, reviewer(lens), input_schema=ReviewChannel)
    builder.add_node("gap_merger", gap_merger, input_schema=ReviewChannel)
    builder.add_node("prd_drafter", prd_drafter)
    builder.add_node("spec_synthesizer", spec_synthesizer)
    builder.add_node("seam_proposer", seam_proposer)
    builder.add_node("ticket_planner", ticket_planner, input_schema=PlanningChannel)
    builder.add_node("dag_validator", dag_validator, input_schema=PlanningChannel)
    builder.add_node("completer", completer)
    builder.add_conditional_edges(
        START,
        route_start,
        [
            "interviewer",
            "critic",
            *REVIEWERS,
            "prd_drafter",
            "spec_synthesizer",
            "seam_proposer",
            "ticket_planner",
            "completer",
            END,
        ],
    )
    builder.add_conditional_edges("critic", route_critic, [*REVIEWERS, END])
    builder.add_edge(REVIEWERS, "gap_merger")
    builder.add_conditional_edges("gap_merger", route_gap_merger, ["prd_drafter", END])
    builder.add_conditional_edges("prd_drafter", route_prd_drafter, ["spec_synthesizer", END])
    builder.add_conditional_edges(
        "spec_synthesizer", route_spec_synthesizer, ["seam_proposer", END]
    )
    builder.add_conditional_edges("seam_proposer", route_seam_proposer, ["ticket_planner", END])
    builder.add_conditional_edges("ticket_planner", route_ticket_planner, ["dag_validator", END])
    builder.add_conditional_edges("dag_validator", route_dag_validator, ["ticket_planner", END])
    builder.add_edge("completer", END)
    builder.add_conditional_edges(
        "interviewer", route_interviewer, ["design_tools", "prd_drafter", END]
    )
    builder.add_conditional_edges("design_tools", route_design_tools, ["interviewer", END])
    return builder.compile(checkpointer=checkpointer)
