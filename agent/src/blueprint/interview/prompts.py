"""The interviewer's system prompt (SPECS S5.2).

Assembled, in order, from: the vendored interviewer instructions, the vendored
course context, the current stage and step, a compact ID-labelled summary of
the design record, and any edit note (S5.9).
"""

from typing import Any

from blueprint.config.assets import Assets
from blueprint.domain.models import Design

STEP_NAMES = {
    1: "Clarify Requirements",
    2: "Data & API Layer",
    3: "High-Level Architecture",
    4: "Scale, Bottlenecks and Reliability",
    5: "Trade-Offs and Extensions",
}


def _num(value: float) -> str:
    return f"{value:g}"


def design_summary(design: Design) -> str:
    """One line per item, each starting with its ID; sections in Design order."""
    sections: list[tuple[str, list[str]]] = [
        (
            "Functional requirements",
            [f"{r.id}: {r.statement}" for r in design.functional_requirements],
        ),
        (
            "Non-functional requirements",
            [
                f"{n.id} [{n.category}]: {n.statement}"
                + (
                    f" ({' '.join(p for p in (n.metric, _num(n.target) if n.target is not None else None, n.unit) if p)})"
                    if n.metric or n.target is not None or n.unit
                    else ""
                )
                for n in design.non_functional_requirements
            ],
        ),
        ("Out of scope", [f"{o.id}: {o.text}" for o in design.out_of_scope]),
        (
            "Capacity estimates",
            [
                f"{e.id}: {e.quantity} = {e.formula} = {_num(e.result)} {e.unit}"
                for e in design.capacity_estimates
            ],
        ),
        (
            "Entities",
            [
                f"{e.id}: {e.name} ("
                + ", ".join(
                    f"{f.name}: {f.type}"
                    + (f" {f.key.upper()}" if f.key != "none" else "")
                    + (f" -> {f.references}" if f.references else "")
                    for f in e.fields
                )
                + ")"
                + (f" indexes: {', '.join(e.indexes)}" if e.indexes else "")
                + (f" ~{e.est_record_bytes} B/record" if e.est_record_bytes else "")
                for e in design.entities
            ],
        ),
        (
            "Relationships",
            [
                f"{r.id}: {r.from_entity} {r.cardinality} {r.to_entity}"
                for r in design.relationships
            ],
        ),
        (
            "Endpoints",
            [
                f"{e.id}: {e.method} {e.path} — request: {e.request}; response: {e.response}"
                + (f"; pagination: {e.pagination}" if e.pagination else "")
                + (f"; errors: {', '.join(e.errors)}" if e.errors else "")
                + (f"; rate limit: {e.rate_limit}" if e.rate_limit else "")
                for e in design.endpoints
            ],
        ),
        (
            "Storage choices",
            [
                f"{s.id} [{s.status}]: {s.data} -> {s.technology}"
                + (f" — because {s.justification}" if s.justification else "")
                + (
                    f"; rejected: {', '.join(s.rejected_alternatives)}"
                    if s.rejected_alternatives
                    else ""
                )
                for s in design.storage_choices
            ],
        ),
        (
            "Components",
            [f"{c.id} [{c.kind}]: {c.name} — {c.responsibility}" for c in design.components],
        ),
        (
            "Flows",
            [
                f"{f.id} [{f.kind}]: {f.name}: "
                + "; ".join(f"{s.from_component} -> {s.to_component} ({s.label})" for s in f.steps)
                for f in design.flows
            ],
        ),
        (
            "CAP stance",
            [f"{design.cap_stance.choice}: {design.cap_stance.rationale}"]
            if design.cap_stance
            else [],
        ),
        (
            "Cache policies",
            [
                f"{c.id}: {c.data} — {c.strategy}, {c.eviction}"
                + (f", TTL {c.ttl_seconds} s" if c.ttl_seconds is not None else "")
                for c in design.cache_policies
            ],
        ),
        (
            "Single points of failure",
            [
                f"{s.id}: {s.component_id} — {s.risk}; mitigation: {s.mitigation or 'NONE'}"
                for s in design.spofs
            ],
        ),
        (
            "Failure modes",
            [
                f"{f.id}: {f.scenario} -> {f.behaviour}"
                + (f"; recovery: {f.recovery}" if f.recovery else "")
                for f in design.failure_modes
            ],
        ),
        (
            "Observability",
            [
                f"{s.id} [{s.kind}]: {s.name}"
                + (f" (threshold {s.threshold})" if s.threshold else "")
                for s in design.observability
            ],
        ),
        (
            "Trade-offs",
            [
                f"{t.id}: {t.decision} — gained {t.gained}; sacrificed {t.sacrificed}"
                for t in design.tradeoffs
            ],
        ),
        ("Extensions", [f"{e.id}: {e.text}" for e in design.extensions]),
    ]
    lines = [f"### {title}\n" + "\n".join(items) for title, items in sections if items]
    return "\n\n".join(lines) if lines else "(nothing recorded yet)"


# A new session opens on "What would you like to build?": the first message is the user's brief.
OPENING = (
    "## Opening\n"
    'Nothing is recorded yet: the user\'s message answers "What would you like to build?", in '
    "as much or as little detail as they have. Before you ask anything, record every functional "
    "requirement, non-functional target and out-of-scope boundary it already states, with your "
    "tools, so the user never has to repeat it. Then ask only about what Step 1 still needs, a "
    "few questions at a time. If the message says little more than the kind of system, start "
    "Step 1 from the beginning and ask everything it needs. The user only answers your questions: "
    "lead every turn."
)


def interviewer_prompt(
    assets: Assets,
    stage: str,
    current_step: int,
    design: Design,
    edit_note: str | None = None,
    gap_answers: str | None = None,
) -> str:
    parts = [
        assets.interviewer_instructions.rstrip("\n"),
        assets.course_context.rstrip("\n"),
        "## Current session\n"
        f"Stage: {stage}\n"
        f"Step: {current_step} of 5 — {STEP_NAMES[current_step]}\n"
        "Record every fact the user settles with your tools; the design record below is what "
        "has been recorded so far, each item labelled with its ID.\n"
        "When the problem matches one of the reference blueprints in the course context "
        "(media streaming, reservations, real-time messaging), name the pattern and its key "
        "technique as something to consider, never as the answer.",
        "## Design record\n" + design_summary(design),
    ]
    if stage == "interview" and not any(design.model_dump().values()):
        parts.append(OPENING)
    if edit_note:
        parts.append("## Edits made by the user\n" + edit_note)
    if gap_answers:
        parts.append("## Gap answers to record\n" + gap_answers)
    return "\n\n".join(parts)


def critic_prompt(assets: Assets, step: int, design: Design) -> str:
    """The critic's system prompt (S5.8): the course rubric, the confirmed step and the record."""
    return "\n\n".join(
        [
            assets.course_context.rstrip("\n"),
            "## Your task\n"
            f"The user has just confirmed Step {step} of 5 — {STEP_NAMES[step]}. "
            "Critique that step of their design against the framework and the five evaluation "
            "dimensions above. Return three lists: strengths and alignment; bottlenecks and "
            "unaddressed trade-offs; probing or next-step questions. Ground every point in the "
            "design record or the conversation, citing item IDs where they apply. Do not add "
            "requirements or design items, and do not answer your own questions.",
            "## Design record\n" + design_summary(design),
        ]
    )


def transcript(messages: list[Any]) -> str:
    """The conversation as plain text: user and interviewer turns only."""
    lines: list[str] = []
    for message in messages:
        text = getattr(message, "text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        role = {"human": "User", "ai": "Interviewer"}.get(getattr(message, "type", ""))
        if role:
            lines.append(f"{role}: {text.strip()}")
    return "\n\n".join(lines) if lines else "(no conversation yet)"
