"""Diagrams.md: every diagram of the design as Mermaid, ready to render (SPECS S11.3)."""

from blueprint.domain.state import SessionState
from blueprint.exports.diagrams import markdown

INTRO = (
    "Mermaid diagrams of the design: the architecture, the data model and one sequence "
    "diagram per data flow. GitHub, GitLab, Notion and mermaid.live render them."
)


def render_diagrams(state: SessionState, session_name: str) -> bytes:
    sections = markdown(state.design)
    if not sections:
        raise LookupError("nothing to draw yet")
    lines = [f"# {session_name} — Diagrams", "", INTRO, "", *sections]
    return ("\n".join(lines).rstrip("\n") + "\n").encode("utf-8")
