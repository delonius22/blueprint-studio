"""Requirements.docx and UserStories.docx (SPECS S10.5, S10.6), from the current PRD (S8.6)
and the approved tickets, stamped with tickets_approved_at (S10.9)."""

from collections.abc import Sequence

from blueprint.domain.models import PrdDoc, Ticket
from blueprint.domain.state import SessionState
from blueprint.exports.docx_util import bullets, new_document, parse_time, table, to_bytes


def _current(state: SessionState) -> PrdDoc:
    if not state.prd_versions or state.tickets_approved_at is None:
        raise LookupError("available once the ticket breakdown is approved")
    return state.prd_versions[-1].doc


def build_waves(tickets: Sequence[Ticket]) -> list[list[Ticket]]:
    """Wave n holds the tickets whose blockers are all in earlier waves."""
    waves: list[list[Ticket]] = []
    placed: set[str] = set()
    remaining = list(tickets)
    while remaining:
        wave = [t for t in remaining if all(b in placed for b in t.blocked_by)]
        if not wave:
            raise ValueError("the blocking edges contain a cycle")
        waves.append(wave)
        placed.update(t.id for t in wave)
        remaining = [t for t in remaining if t.id not in placed]
    return waves


def _covering(doc: PrdDoc, requirement: str) -> str:
    return ", ".join(s.id for s in doc.user_stories if requirement in s.requirement_ids) or "—"


def render_requirements(state: SessionState, session_name: str) -> bytes:
    doc = _current(state)
    features = {f.id: f.name for f in doc.features}
    document = new_document(f"{session_name} — Requirements")
    document.add_heading(f"{session_name} — Requirements", level=0)
    document.add_paragraph(f"From PRD v{state.prd_versions[-1].version}, the current PRD.")
    document.add_heading("Functional Requirements", level=1)
    table(
        document,
        ["ID", "Feature", "Requirement", "Covering stories"],
        [
            [
                r.id,
                f"{r.feature_id}: {features.get(r.feature_id, '')}",
                r.statement,
                _covering(doc, r.id),
            ]
            for r in doc.functional_requirements
        ],
    )
    document.add_heading("Non-Functional Requirements", level=1)
    table(
        document,
        ["ID", "Category", "Requirement", "Covering stories"],
        [
            [n.id, n.category, n.statement, _covering(doc, n.id)]
            for n in doc.non_functional_requirements
        ],
    )
    document.add_heading("Appendix: Open Gaps and Accepted Risks", level=1)
    if not doc.open_gaps:
        document.add_paragraph("None.")
    else:
        table(
            document,
            [
                "ID",
                "Lens",
                "Severity",
                "Features",
                "Affected items",
                "Risk",
                "Decision needed",
                "Note",
            ],
            [
                [
                    g.id,
                    g.lens,
                    g.severity,
                    ", ".join(g.feature_ids),
                    ", ".join(g.item_ids),
                    g.risk,
                    g.decision_needed,
                    g.note or "",
                ]
                for g in doc.open_gaps
            ],
        )
    return to_bytes(document, parse_time(str(state.tickets_approved_at)))


def render_user_stories(state: SessionState, session_name: str) -> bytes:
    doc = _current(state)
    tickets = sorted(state.tickets, key=lambda t: t.id)
    delivered_by = {s.id: [t.id for t in tickets if s.id in t.story_ids] for s in doc.user_stories}
    document = new_document(f"{session_name} — User Stories")
    document.add_heading(f"{session_name} — User Stories", level=0)
    document.add_heading("User Stories", level=1)
    for feature in doc.features:
        document.add_heading(f"{feature.id}: {feature.name}", level=2)
        stories = [s for s in doc.user_stories if s.feature_id == feature.id]
        if not stories:
            document.add_paragraph("No stories.")
        for story in stories:
            paragraph = document.add_paragraph()
            paragraph.add_run(story.id).bold = True
            paragraph.add_run(
                f": As {story.actor}, I want {story.feature}, so that {story.benefit}"
            )
            document.add_paragraph(
                f"Requirements: {', '.join(story.requirement_ids)}. "
                f"Delivered by: {', '.join(delivered_by[story.id]) or '—'}."
            )
            bullets(document, story.acceptance_criteria, empty="No acceptance criteria.")
    document.add_heading("Tickets", level=1)
    for ticket in tickets:
        document.add_heading(f"{ticket.id}: {ticket.title}", level=2)
        document.add_paragraph(ticket.what_to_build)
        document.add_paragraph(
            f"Blocked by: {', '.join(ticket.blocked_by) or 'None (can start immediately)'}"
        )
        document.add_paragraph(f"Delivers: {', '.join(ticket.story_ids)}")
        for criterion in ticket.acceptance_criteria:
            document.add_paragraph(f"☐ {criterion}")
    document.add_heading("Build Waves", level=1)
    rows = []
    for number, wave in enumerate(build_waves(tickets), 1):
        blockers = sorted({b for t in wave for b in t.blocked_by})
        rows.append([str(number), ", ".join(t.id for t in wave), ", ".join(blockers) or "—"])
    table(document, ["Wave", "Tickets", "Blocked by"], rows)
    return to_bytes(document, parse_time(str(state.tickets_approved_at)))
