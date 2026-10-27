"""The planning nodes: PRD v1.0 and sign-off, to-spec, seams, changes and tickets (S7-S9)."""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from blueprint.domain.models import (
    Design,
    Gap,
    PrdDoc,
    PrdVersion,
    ProposedChange,
    SourceExcerpt,
    Ticket,
)
from blueprint.domain.state import DesignState
from blueprint.graph.context import Context, Update, ask, broke_rules, invalid_output, utc_now
from blueprint.graph.gates import SIGN_OFF_PRD, last_answer, step_approved
from blueprint.llm.gateway import Meter, ModelCallFailed
from blueprint.planning.changes import apply_changes
from blueprint.planning.prd import (
    PrdDraftOut,
    build_prd,
    current_prd,
    draft_problems,
    drafter_messages,
    signoff_summary,
)
from blueprint.planning.spec import (
    SeamsOut,
    SpecOut,
    build_v1_1_draft,
    issue_seams,
    seam_decision,
    seam_messages,
    seam_problems,
    spec_problems,
    synthesizer_messages,
)
from blueprint.planning.tickets import (
    DagError,
    TicketDraft,
    TicketsOut,
    planner_messages,
    ticket_problems,
    tickets_summary,
    validate_dag,
)
from blueprint.utils.models import dump, load
from blueprint.utils.text import plural

DAG_ATTEMPTS = 3


class PlanningChannel(DesignState):
    """Graph-internal channel from the ticket planner to the DAG validator (S9.3): the draft
    tickets, the last DAG error and how many attempts were made. Not session state."""

    planning: dict[str, Any]


def _frozen(version: PrdVersion, state: DesignState) -> list[dict[str, Any]]:
    return [*state["prd_versions"], version.model_dump(mode="json")]


async def prd_drafter(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """S7.1-S7.4: draft PRD v1.0, open sign_off_prd, and act on the user's answer."""
    previous = PrdDoc.model_validate(state["prd_draft"]) if state.get("prd_draft") else None
    answer = last_answer(list(state["messages"]))
    reason = None
    if answer is not None and answer[0] == SIGN_OFF_PRD and state["stage"] == "prd_signoff":
        if step_approved(answer[1]) and previous is not None:
            version = PrdVersion(version="1.0", approved_at=utc_now(), doc=previous)
            return {
                "prd_versions": _frozen(version, state),
                "stage": "spec_synthesis",
                "last_error": None,
                "messages": [
                    AIMessage("PRD v1.0 is signed off and frozen. You can download it now.")
                ],
            }
        reason = str(answer[1].get("reason") or "").strip() or "The user rejected the draft."
    design = Design.model_validate(state["design"])
    gaps = load(Gap, state, "gaps")
    accepted = [g for g in gaps if g.status == "accepted"]
    excerpts = load(SourceExcerpt, state, "prd_context")
    meter = Meter.for_node(state, "prd_drafter")
    prompt = drafter_messages(design, accepted, previous, reason, excerpts)
    try:
        out, problems = await ctx.structured_with_retry(
            meter, PrdDraftOut, prompt, lambda o: draft_problems(o, design, accepted), config
        )
    except ModelCallFailed as failure:
        return {"last_error": failure.info()}
    if problems or out is None:
        return broke_rules("The PRD draft", problems, meter)
    counters = dict(state["id_counters"])
    doc = build_prd(out, design, accepted, counters, previous)
    features_of = {g.id: g.feature_ids for g in doc.open_gaps}
    card = await ask(
        config, SIGN_OFF_PRD, {"prd": doc.model_dump(mode="json")}, signoff_summary(doc)
    )
    return {
        "prd_draft": doc.model_dump(mode="json"),
        "gaps": dump(
            g.model_copy(update={"feature_ids": features_of.get(g.id, g.feature_ids)}) for g in gaps
        ),
        "id_counters": counters,
        "stage": "prd_signoff",
        "tokens_used": meter.used,
        "last_error": None,
        "messages": [card],
    }


async def spec_synthesizer(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """S8.1, S8.2: extend the signed-off PRD into the v1.1 draft with to-spec."""
    signed = PrdDoc.model_validate(state["prd_versions"][-1]["doc"])
    design = Design.model_validate(state["design"])
    meter = Meter.for_node(state, "spec_synthesizer")
    prompt = synthesizer_messages(ctx.assets, signed, design, list(state["messages"]))
    try:
        out, problems = await ctx.structured_with_retry(
            meter, SpecOut, prompt, lambda o: spec_problems(o, signed), config
        )
    except ModelCallFailed as failure:
        return {"last_error": failure.info()}
    if problems or out is None:
        return broke_rules("The PRD v1.1 synthesis", problems, meter)
    counters = dict(state["id_counters"])
    draft, changes = build_v1_1_draft(out, signed, counters)
    return {
        "prd_draft": draft.model_dump(mode="json"),
        "proposed_changes": dump(changes),
        "seams": [],
        "id_counters": counters,
        "stage": "seam_gate",
        "tokens_used": meter.used,
        "last_error": None,
    }


async def seam_proposer(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """S8.3, S8.4: propose the test seams and freeze PRD v1.1 with them. Since the build
    this needs no approval: only the step confirmations and the PRD sign-off stop."""
    draft = PrdDoc.model_validate(state["prd_draft"])
    meter = Meter.for_node(state, "seam_proposer")
    prompt = seam_messages(ctx.assets, draft, None, [])
    try:
        out, problems = await ctx.structured_with_retry(
            meter, SeamsOut, prompt, lambda o: seam_problems(o.seams, draft), config
        )
    except ModelCallFailed as failure:
        return {"last_error": failure.info()}
    if problems or out is None:
        return broke_rules("The seam proposal", problems, meter)
    counters = dict(state["id_counters"])
    seams = issue_seams(out.seams, counters)
    final = draft.model_copy(update={"testing_decisions": [seam_decision(s) for s in seams]})
    version = PrdVersion(version="1.1", approved_at=utc_now(), doc=final)
    names = ", ".join(s.name for s in seams)
    return {
        "seams": dump(seams),
        "prd_draft": final.model_dump(mode="json"),
        "prd_versions": _frozen(version, state),
        "id_counters": counters,
        "stage": "change_review" if state.get("proposed_changes") else "ticket_breakdown",
        "tokens_used": meter.used,
        "last_error": None,
        "messages": [
            AIMessage(
                f"PRD v1.1 is frozen with {plural(len(seams), 'test seam')} ({names}). You can download it now."
            )
        ],
    }


async def change_applier(ctx: Context, state: DesignState) -> Update:
    """S8.5: apply the changes synthesis proposed to signed-off content as PRD v1.2. Since
    the build every pending change is accepted: the PRD sign-off was the user's decision."""
    decided = [
        c.model_copy(update={"decision": "approved"}) if c.decision == "pending" else c
        for c in load(ProposedChange, state, "proposed_changes")
    ]
    approved = [c for c in decided if c.decision == "approved"]
    update: Update = {
        "proposed_changes": dump(decided),
        "stage": "ticket_breakdown",
        "last_error": None,
    }
    if not approved:
        message = "Every proposed change was rejected; PRD v1.1 stays the current PRD."
        return update | {"messages": [AIMessage(message)]}
    counters = dict(state["id_counters"])
    base = PrdDoc.model_validate(state["prd_versions"][-1]["doc"])
    changed = apply_changes(base, approved, counters)
    version = PrdVersion(version="1.2", approved_at=utc_now(), doc=changed)
    text = (
        f"PRD v1.2 is frozen with the {plural(len(approved), 'change')} synthesis proposed. "
        "You can download it now."
    )
    return update | {
        "id_counters": counters,
        "prd_draft": changed.model_dump(mode="json"),
        "prd_versions": _frozen(version, state),
        "messages": [AIMessage(text)],
    }


async def ticket_planner(ctx: Context, state: PlanningChannel, config: RunnableConfig) -> Update:
    """S9.1, S9.2: break the current PRD into tickets with to-tickets."""
    prd = current_prd(state["prd_versions"])
    assert prd is not None
    planning = dict(state.get("planning") or {})
    attempts = int(planning.get("attempts", 0)) + 1
    if attempts > DAG_ATTEMPTS:
        message = f"The ticket breakdown kept invalid blocking edges: {planning.get('error')}"
        return {"last_error": invalid_output(message), "planning": {}}
    current = load(Ticket, state, "tickets")
    previous = [TicketDraft.model_validate(t) for t in planning.get("drafts") or []]
    prompt = planner_messages(ctx.assets, prd, current, None, planning.get("error"), previous)
    meter = Meter.for_node(state, "ticket_planner")
    try:
        out, problems = await ctx.structured_with_retry(
            meter, TicketsOut, prompt, lambda o: ticket_problems(o.tickets, prd), config
        )
    except ModelCallFailed as failure:
        return {"last_error": failure.info()}
    if problems or out is None:
        return broke_rules("The ticket breakdown", problems, meter) | {"planning": {}}
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


async def dag_validator(ctx: Context, state: PlanningChannel) -> Update:
    """S9.3: check the blocking edges and renumber in build order; a valid breakdown goes
    straight to the completer (no review since the build)."""
    planning = dict(state.get("planning") or {})
    drafts = [TicketDraft.model_validate(t) for t in planning.get("drafts") or []]
    try:
        tickets = validate_dag(drafts)
    except DagError as invalid:
        return {"planning": planning | {"error": str(invalid)}}
    return {
        "tickets": dump(tickets),
        "id_counters": dict(state["id_counters"]) | {"T": len(tickets)},
        "stage": "ticket_gate",
        "planning": {},
        "messages": [AIMessage(tickets_summary(tickets))],
    }


async def completer(ctx: Context, state: DesignState) -> Update:
    """S9.4: the ticket breakdown completes the session; one message lists the downloads."""
    versions = ", ".join(f"PRD v{v['version']}.docx" for v in state["prd_versions"])
    text = (
        "The ticket breakdown is done and the session is complete. Your downloads are "
        f"ready: {versions}, Requirements.docx, UserStories.docx and context.md (the Jira "
        "hand-off), or all of them as one zip from the completion view."
    )
    return {
        "tickets_approved_at": utc_now(),
        "stage": "complete",
        "last_error": None,
        "messages": [AIMessage(text)],
    }
