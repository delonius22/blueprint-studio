"""PRD v1.1 with the to-spec method, and the test seams (SPECS S8.1-S8.4).

The vendored ``to-spec`` text is given to the model verbatim, with the app's
framing around it: synthesize without asking questions, write into PRD v1.1
instead of a tracker (PRD D8), and leave the seam check to its own step.
"""

import json
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import Field, ValidationError

from blueprint.assets import Assets
from blueprint.changes import change_problem
from blueprint.design import issue_id
from blueprint.domain import (
    SIGNED_OFF_SECTIONS,
    Design,
    Gap,
    Model,
    PrdDoc,
    ProposedChange,
    Seam,
    UserStory,
)

FRAMING = (
    "You are running the to-spec method below for Blueprint Studio. The user has already signed "
    "off PRD v1.0; extend it into PRD v1.1. Synthesize from what is already known: do NOT ask "
    "the user any questions. There is no codebase and no issue tracker: instead of publishing, "
    "return the structured output. Sketching and checking test seams is a separate step, so do "
    "not do it here. Never change the signed-off sections: if something in them should change, "
    "list it as a proposed change instead, with the section name and, when it targets one item, "
    "its FR-, NFR- or F- ID. Every user story belongs to exactly one existing feature and names "
    "at least one existing FR- or NFR- ID; every functional requirement is covered by at least "
    "one story."
)


class StoryDraft(Model):
    feature_id: str
    actor: str
    feature: str = Field(description='What the actor wants: the text after "I want".')
    benefit: str = Field(description='The text after "so that".')
    acceptance_criteria: list[str]
    requirement_ids: list[str]


class ChangeDraft(Model):
    section: str = Field(description=f"One of: {', '.join(SIGNED_OFF_SECTIONS)}.")
    target_id: str | None = None
    kind: str = Field(description="add, modify or remove")
    current_text: str | None = None
    proposed_text: str | None = None
    reason: str


class SpecOut(Model):
    solution: str
    user_stories: list[StoryDraft]
    implementation_decisions: list[str]
    further_notes: list[str]
    proposed_changes: list[ChangeDraft]


class SeamDraft(Model):
    name: str
    description: str
    covers: list[str] = Field(description="The US-, FR-, NFR- or F- IDs this seam tests.")


class SeamsOut(Model):
    seams: list[SeamDraft]


def gap_note(gap: Gap) -> str:
    """An open gap as a further note: verbatim, prefixed by its ID (S8.1)."""
    note = f" Note: {gap.note}" if gap.note else ""
    return f"{gap.id}: {gap.risk} Decision needed: {gap.decision_needed}{note}"


def _transcript(messages: Sequence[BaseMessage]) -> str:
    lines = []
    for message in messages:
        role = {"human": "User", "ai": "Interviewer"}.get(message.type)
        if role and message.text.strip():
            lines.append(f"{role}: {message.text.strip()}")
    return "\n\n".join(lines) or "(no conversation)"


def synthesizer_messages(
    assets: Assets, signed: PrdDoc, design: Design, messages: Sequence[BaseMessage]
) -> list[BaseMessage]:
    """S8.1: to-spec verbatim (with its attribution), v1.0, the design record, the transcript."""
    return [
        SystemMessage(FRAMING + "\n\n" + assets.to_spec),
        HumanMessage(
            "## Signed-off PRD v1.0\n```json\n"
            + signed.model_dump_json(indent=2, include=set(SIGNED_OFF_SECTIONS))
            + "\n```\n\n## Design record\n```json\n"
            + design.model_dump_json(indent=2)
            + "\n```\n\n## Conversation\n"
            + _transcript(messages)
        ),
    ]


def spec_problems(out: SpecOut, signed: PrdDoc) -> list[str]:
    """S8.2: stories trace to existing features and requirements, every FR is covered, and
    proposed changes name signed-off sections and existing targets."""
    problems: list[str] = []
    features = {f.id for f in signed.features}
    frs = {r.id for r in signed.functional_requirements}
    nfrs = {n.id for n in signed.non_functional_requirements}
    for i, story in enumerate(out.user_stories, 1):
        if story.feature_id not in features:
            problems.append(f"story {i} names feature {story.feature_id}, which does not exist")
        if not story.requirement_ids:
            problems.append(f"story {i} names no requirement")
        for requirement in story.requirement_ids:
            if requirement not in frs | nfrs:
                problems.append(f"story {i} names {requirement}, which is not an FR or NFR")
    covered = {r for s in out.user_stories for r in s.requirement_ids}
    for requirement in sorted(frs - covered, key=lambda x: int(x.split("-")[1])):
        problems.append(f"{requirement} is covered by no user story")
    for i, change in enumerate(out.proposed_changes, 1):
        if change.section not in SIGNED_OFF_SECTIONS:
            problems.append(
                f"proposed change {i} names {change.section}, which is not a signed-off section"
            )
        if change.target_id is not None and change.target_id not in features | frs | nfrs:
            problems.append(f"proposed change {i} targets {change.target_id}, which does not exist")
        if change.kind not in ("add", "modify", "remove"):
            problems.append(
                f"proposed change {i} has kind {change.kind}; use add, modify or remove"
            )
        elif change.section in SIGNED_OFF_SECTIONS:
            try:
                candidate = ProposedChange.model_validate({"id": f"CHG-{i}", **change.model_dump()})
            except ValidationError as exc:
                problems.append(f"proposed change {i} is incomplete: {exc.errors()[0]['msg']}")
                continue
            problem = change_problem(candidate, signed)
            if problem:
                problems.append(f"proposed change {i} cannot be applied: {problem}")
    return problems


def build_v1_1_draft(
    out: SpecOut, signed: PrdDoc, counters: dict[str, int]
) -> tuple[PrdDoc, list[ProposedChange]]:
    """The draft: v1.0's signed-off sections untouched, plus the extension sections (S8.1)."""
    stories = [
        UserStory(id=issue_id(counters, "US"), **story.model_dump()) for story in out.user_stories
    ]
    notes = [*out.further_notes, *(gap_note(g) for g in signed.open_gaps)]
    draft = signed.model_copy(
        update={
            "solution": out.solution,
            "user_stories": stories,
            "implementation_decisions": out.implementation_decisions,
            "further_notes": notes,
        },
        deep=True,
    )
    changes = [
        ProposedChange(id=issue_id(counters, "CHG"), decision="pending", **change.model_dump())
        for change in out.proposed_changes
    ]
    return draft, changes


def seam_messages(
    assets: Assets, draft: PrdDoc, feedback: str | None, previous: Sequence[Seam]
) -> list[BaseMessage]:
    """S8.3: to-spec step 2 only: the highest seams, as few as possible."""
    task = (
        "Do step 2 of the to-spec method below and nothing else: sketch the seams at which this "
        "system will be tested. Use the highest seams possible and as few as possible; the ideal "
        "number is one. For each seam give a name, a description, and the IDs it covers. The user "
        "will check them with you afterwards in the app, so do not ask now."
    )
    parts = ["## PRD v1.1 draft\n```json\n" + draft.model_dump_json(indent=2) + "\n```"]
    if feedback:
        parts.append(
            "## Seams you proposed before\n```json\n"
            + json.dumps([s.model_dump() for s in previous], indent=2)
            + "\n```\n## The user's feedback\n"
            + feedback
        )
    return [SystemMessage(task + "\n\n" + assets.to_spec), HumanMessage("\n\n".join(parts))]


def coverable_ids(draft: PrdDoc) -> set[str]:
    return (
        {s.id for s in draft.user_stories}
        | {r.id for r in draft.functional_requirements}
        | {n.id for n in draft.non_functional_requirements}
        | {f.id for f in draft.features}
    )


def seam_problems(seams: Sequence[SeamDraft], draft: PrdDoc) -> list[str]:
    problems: list[str] = []
    if not seams:
        problems.append("propose at least one seam")
    known = coverable_ids(draft)
    for seam in seams:
        unknown = [c for c in seam.covers if c not in known]
        if unknown:
            problems.append(f"seam {seam.name!r} covers unknown IDs: {', '.join(unknown)}")
    return problems


def issue_seams(drafts: Sequence[SeamDraft], counters: dict[str, int]) -> list[Seam]:
    return [Seam(id=issue_id(counters, "SEAM"), **d.model_dump()) for d in drafts]


def approved_seams(answer: Any, proposed: Sequence[Seam], counters: dict[str, int]) -> list[Seam]:
    """The seams the user approved, possibly edited (S8.3): known IDs kept, new ones issued."""
    known = {s.id for s in proposed}
    seams: list[Seam] = []
    for raw in answer if isinstance(answer, list) else []:
        if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
            continue
        seam_id = raw.get("id") if raw.get("id") in known else issue_id(counters, "SEAM")
        seams.append(
            Seam(
                id=str(seam_id),
                name=str(raw["name"]).strip(),
                description=str(raw.get("description", "")).strip(),
                covers=[str(c) for c in raw.get("covers") or []],
            )
        )
    return seams


def seam_decision(seam: Seam) -> str:
    """A seam as a testing decision of PRD v1.1 (S8.4)."""
    covers = f" Covers {', '.join(seam.covers)}." if seam.covers else ""
    return f"{seam.id}: {seam.name}. {seam.description}{covers}"
