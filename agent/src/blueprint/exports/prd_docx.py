"""PRD v1.x.docx (SPECS S10.4): the frozen PRD version, section by section."""

from blueprint.domain.models import Design, PrdVersion, ProposedChange
from blueprint.domain.state import SessionState
from blueprint.exports.diagrams import all_diagrams
from blueprint.exports.docx_util import (
    bullets,
    code_block,
    new_document,
    parse_time,
    table,
    to_bytes,
)

ATTRIBUTION = (
    "This document was extended with the to-spec method from mattpocock-skills 1.2.3 "
    "(MIT License, © 2026 Matt Pocock)."
)


def _num(value: float | None) -> str:
    return "" if value is None else f"{value:g}"


def render_prd(state: SessionState, session_name: str, version: str) -> bytes:
    found = next((v for v in state.prd_versions if v.version == version), None)
    if found is None:
        raise LookupError(f"PRD v{version} has not been approved")
    return _render(
        found,
        session_name,
        [c for c in state.proposed_changes if c.decision == "approved"],
        state.design,
    )


def _render(
    entry: PrdVersion,
    session_name: str,
    approved_changes: list[ProposedChange],
    design: Design,
) -> bytes:
    doc = entry.doc
    approved = parse_time(entry.approved_at)
    document = new_document(f"{session_name} — PRD v{entry.version}")
    document.add_heading(f"{session_name} — PRD v{entry.version}", level=0)
    document.add_paragraph(
        f"Version {entry.version}, approved {approved.strftime('%Y-%m-%d %H:%M UTC')}"
    )

    features = {f.id: f.name for f in doc.features}
    document.add_heading("Problem Statement", level=1)
    document.add_paragraph(doc.problem_statement or "None.")
    document.add_heading("Goals", level=1)
    bullets(document, doc.goals)
    document.add_heading("Users and Stakeholders", level=1)
    bullets(document, doc.users)
    document.add_heading("Features", level=1)
    for feature in doc.features:
        document.add_heading(f"{feature.id}: {feature.name}", level=2)
        document.add_paragraph(feature.description)
        document.add_paragraph(f"Requirements: {', '.join(feature.requirement_ids)}")
    document.add_heading("Functional Requirements", level=1)
    table(
        document,
        ["ID", "Feature", "Requirement"],
        [
            [r.id, f"{r.feature_id}: {features.get(r.feature_id, '')}", r.statement]
            for r in doc.functional_requirements
        ],
    )
    document.add_heading("Non-Functional Requirements", level=1)
    table(
        document,
        ["ID", "Category", "Requirement", "Metric", "Target", "Unit"],
        [
            [n.id, n.category, n.statement, n.metric or "", _num(n.target), n.unit or ""]
            for n in doc.non_functional_requirements
        ],
    )
    document.add_heading("Scope", level=1)
    bullets(document, doc.scope)
    document.add_heading("Out of Scope", level=1)
    bullets(document, doc.out_of_scope)
    document.add_heading("Open Gaps and Accepted Risks", level=1)
    table(
        document,
        ["ID", "Lens", "Severity", "Affected items", "Risk", "Decision needed", "Note"],
        [
            [
                g.id,
                g.lens,
                g.severity,
                ", ".join(g.item_ids),
                g.risk,
                g.decision_needed,
                g.note or "",
            ]
            for g in doc.open_gaps
        ],
    )
    document.add_heading("Diagrams", level=1)
    diagrams = all_diagrams(design)
    if not diagrams:
        document.add_paragraph("None: no entities or components were recorded.")
    else:
        document.add_paragraph(
            "Mermaid source. Diagrams.md in the downloads has them ready to render; any Mermaid "
            "renderer, such as mermaid.live, also draws a pasted diagram."
        )
    for title, source in diagrams:
        document.add_heading(title, level=2)
        code_block(document, source)

    if entry.version != "1.0":
        document.add_heading("Solution", level=1)
        document.add_paragraph(doc.solution or "None.")
        document.add_heading("User Stories", level=1)
        for story in doc.user_stories:
            paragraph = document.add_paragraph(style="List Number")
            paragraph.add_run(f"{story.id}").bold = True
            paragraph.add_run(
                f" ({story.feature_id}; {', '.join(story.requirement_ids)}): As {story.actor}, "
                f"I want {story.feature}, so that {story.benefit}"
            )
        document.add_heading("Implementation Decisions", level=1)
        bullets(document, doc.implementation_decisions)
        document.add_heading("Testing Decisions", level=1)
        bullets(document, doc.testing_decisions)
        document.add_heading("Further Notes", level=1)
        bullets(document, doc.further_notes)
    if entry.version == "1.2":
        document.add_heading("Changes from v1.1", level=1)
        table(
            document,
            ["ID", "Section", "Target", "Change", "Current text", "Proposed text", "Reason"],
            [
                [
                    c.id,
                    c.section,
                    c.target_id or "",
                    c.kind,
                    c.current_text or "",
                    c.proposed_text or "",
                    c.reason,
                ]
                for c in approved_changes
            ],
        )
    if entry.version != "1.0":
        document.add_paragraph(ATTRIBUTION)
    return to_bytes(document, approved)
