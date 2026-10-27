"""Tickets with the to-tickets method (SPECS S9.1-S9.4, S2.14).

The planner sees the current PRD with every open gap removed, so an open gap can
never become a ticket (G3). The model labels its tickets as it likes; the DAG
validator checks the blocking edges and renumbers valid tickets T-01, T-02, ... in
topological order.
"""

import json
import re
from collections.abc import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import Field

from blueprint.config.assets import Assets
from blueprint.domain.models import Model, PrdDoc, Ticket

GAP_NOTE = re.compile(r"^GAP-\d+:")

FRAMING = (
    "You are running the to-tickets method below for Blueprint Studio. Work only from the PRD "
    "below: there is no codebase to explore and no tracker to publish to. Do not quiz the user; "
    "the app asks them to approve or revise the breakdown afterwards. Return every ticket with a "
    "short label of your choice as its id (unique), a title, what to build, the ids of the tickets "
    "that block it, its acceptance criteria, the US- IDs of the user stories it delivers, and its "
    "kind (slice, prefactor, expand, migrate or contract). Every user story must be delivered by "
    "at least one ticket. Create tickets only for what the PRD contains."
)


class TicketDraft(Model):
    id: str = Field(description="Your own short label for this ticket, unique in the list.")
    title: str
    what_to_build: str
    blocked_by: list[str] = Field(description="Labels of the tickets that must be done first.")
    acceptance_criteria: list[str]
    story_ids: list[str]
    kind: str = "slice"


class TicketsOut(Model):
    tickets: list[TicketDraft]


class DagError(ValueError):
    """The breakdown is not a valid set of blocking edges (S9.3)."""


def planner_view(prd: PrdDoc) -> PrdDoc:
    """S9.1: the current PRD with open_gaps removed and gap entries removed from further notes."""
    return prd.model_copy(
        update={
            "open_gaps": [],
            "further_notes": [n for n in prd.further_notes if not GAP_NOTE.match(n)],
        }
    )


def planner_messages(
    assets: Assets,
    prd: PrdDoc,
    current: Sequence[Ticket] = (),
    instructions: str | None = None,
    dag_error: str | None = None,
    previous: Sequence[TicketDraft] = (),
) -> list[BaseMessage]:
    parts = ["## Current PRD\n```json\n" + planner_view(prd).model_dump_json(indent=2) + "\n```"]
    if instructions:
        parts.append(
            "## The current breakdown\n```json\n"
            + json.dumps([t.model_dump() for t in current], indent=2)
            + "\n```\n## The user asks you to revise it\n"
            + instructions
        )
    if dag_error:
        parts.append(
            "## Your previous breakdown\n```json\n"
            + json.dumps([t.model_dump() for t in previous], indent=2)
            + "\n```\n## Its blocking edges were invalid\n"
            + dag_error
        )
    return [SystemMessage(FRAMING + "\n\n" + assets.to_tickets), HumanMessage("\n\n".join(parts))]


def ticket_problems(drafts: Sequence[TicketDraft], prd: PrdDoc) -> list[str]:
    """S9.2: every ticket names existing stories; every story is covered by a ticket."""
    problems: list[str] = []
    stories = [s.id for s in prd.user_stories]
    if not drafts:
        problems.append("the breakdown has no tickets")
    for draft in drafts:
        if not draft.story_ids:
            problems.append(f"ticket {draft.id} names no user story")
        for story in draft.story_ids:
            if story not in stories:
                problems.append(f"ticket {draft.id} names {story}, which is not a user story")
        if not draft.acceptance_criteria:
            problems.append(f"ticket {draft.id} has no acceptance criteria")
        if draft.kind not in ("slice", "prefactor", "expand", "migrate", "contract"):
            problems.append(f"ticket {draft.id} has kind {draft.kind}")
    covered = {s for d in drafts for s in d.story_ids}
    for story in stories:
        if story not in covered:
            problems.append(f"{story} is delivered by no ticket")
    return problems


def _cycle(drafts: Sequence[TicketDraft]) -> list[str] | None:
    """A cycle in the blocking edges as an ordered list (first label repeated at the end)."""
    edges = {d.id: list(d.blocked_by) for d in drafts}
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        path.append(node)
        for nxt in edges.get(node, []):
            if state.get(nxt) == 1:
                return [*path[path.index(nxt) :], nxt]
            if state.get(nxt) is None:
                found = visit(nxt)
                if found:
                    return found
        state[node] = 2
        path.pop()
        return None

    for draft in drafts:
        if state.get(draft.id) is None:
            found = visit(draft.id)
            if found:
                return found
    return None


def validate_dag(drafts: Sequence[TicketDraft]) -> list[Ticket]:
    """S9.3: reject unknown blockers, duplicate IDs and cycles (naming the cycle); otherwise
    renumber T-01... in topological order, ties by original order, rewriting blocked_by."""
    labels = [d.id for d in drafts]
    duplicates = sorted({x for x in labels if labels.count(x) > 1})
    if duplicates:
        raise DagError(f"duplicate ticket IDs: {', '.join(duplicates)}")
    for draft in drafts:
        unknown = [b for b in draft.blocked_by if b not in labels]
        if unknown:
            raise DagError(f"ticket {draft.id} is blocked by unknown tickets: {', '.join(unknown)}")
    cycle = _cycle(drafts)
    if cycle:
        raise DagError("the blocking edges contain a cycle: " + " → ".join(cycle))
    order: list[TicketDraft] = []
    done: set[str] = set()
    remaining = list(drafts)
    while remaining:
        ready = next(d for d in remaining if all(b in done for b in d.blocked_by))
        order.append(ready)
        done.add(ready.id)
        remaining.remove(ready)
    width = max(2, len(str(len(order))))
    new_id = {d.id: f"T-{i + 1:0{width}d}" for i, d in enumerate(order)}
    return [
        Ticket(
            id=new_id[d.id],
            title=d.title,
            what_to_build=d.what_to_build,
            blocked_by=[new_id[b] for b in dict.fromkeys(d.blocked_by)],
            acceptance_criteria=d.acceptance_criteria,
            story_ids=d.story_ids,
            kind=d.kind,  # type: ignore[arg-type]
        )
        for d in order
    ]


def tickets_summary(tickets: Sequence[Ticket]) -> str:
    """The breakdown as a chat message: one line per ticket, in build order."""
    lines = [
        f"- {t.id}: {t.title}"
        + (f" (blocked by {', '.join(t.blocked_by)})" if t.blocked_by else "")
        for t in tickets
    ]
    return (
        f"Here is the breakdown: {len(tickets)} ticket{'s' if len(tickets) != 1 else ''}, numbered "
        "in build order.\n\n" + "\n".join(lines)
    )
