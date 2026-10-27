"""Settling the gap register with the user (SPECS S6.5).

The decide_gaps card shows every open gap; acceptances are applied directly, answers go to
the interviewer to record as ordinary design items.
"""

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig

from blueprint.domain.models import Gap
from blueprint.graph.context import Update, ask
from blueprint.graph.gates import DECIDE_GAPS, gap_decisions, latest_answer_to
from blueprint.utils.text import plural


def open_gaps(gaps: Sequence[Gap]) -> list[Gap]:
    return [g for g in gaps if g.status == "open"]


def decide_gaps_args(gaps: Sequence[Gap]) -> dict[str, Any]:
    """What the decide_gaps card shows: every open gap."""
    keys = ("id", "lens", "severity", "item_ids", "risk", "decision_needed")
    return {"gaps": [{k: getattr(g, k) for k in keys} for g in open_gaps(gaps)]}


def accept_gaps(gaps: Sequence[Gap], answer: dict[str, Any]) -> list[Gap]:
    """The register with every open gap the user accepted marked ``accepted``, with its note."""
    accepted = {
        d.gap_id: d.text.strip() or None
        for d in gap_decisions(answer.get("decisions"))
        if d.decision == "accept"
    }
    return [
        g.model_copy(update={"status": "accepted", "note": accepted[g.id]})
        if g.status == "open" and g.id in accepted
        else g
        for g in gaps
    ]


def gap_answer_note(gaps: Sequence[Gap], messages: Sequence[BaseMessage]) -> str | None:
    """The open gaps the user answered in the newest decide_gaps card, for the interviewer."""
    answers = {
        d.gap_id: d.text
        for d in gap_decisions(latest_answer_to(messages, DECIDE_GAPS))
        if d.decision == "answer"
    }
    lines = [
        f"- {g.id} ({g.lens}, {g.severity}; items {', '.join(g.item_ids)}): risk: {g.risk} "
        f"Decision needed: {g.decision_needed} The user's answer: {answers[g.id]}"
        for g in open_gaps(gaps)
        if answers.get(g.id, "").strip()
    ]
    if not lines:
        return None
    return (
        "The user answered these gaps from the design review. Record each answer as ordinary "
        "design items with your tools, using only what the user said, then call resolve_gap with "
        "the gap ID and the IDs of the items you recorded.\n" + "\n".join(lines)
    )


async def gap_followup(config: RunnableConfig, gaps: Sequence[Gap]) -> Update:
    """After gap decisions: the PRD draft when none is open, else a new decide_gaps card."""
    still_open = open_gaps(gaps)
    if not still_open:
        settled = AIMessage("Every gap is answered or accepted. Next, the PRD draft.")
        return {"stage": "prd_draft", "messages": [settled]}
    count = len(still_open)
    text = (
        f"{plural(count, 'gap')} {'is' if count == 1 else 'are'} still open; "
        f"answer or accept {'it' if count == 1 else 'each'}."
    )
    card = await ask(config, DECIDE_GAPS, decide_gaps_args(gaps), text)
    return {"stage": "gap_resolution", "messages": [card]}
