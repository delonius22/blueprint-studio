"""The download kinds, their availability and their renderers (SPECS S10.1-S10.3).

Every renderer is a pure function ``(state, session_name) -> bytes``: no I/O and
no model call (S10.1). Availability is decided here, never in the browser.
"""

from collections.abc import Callable
from dataclasses import dataclass

from blueprint.diagrams import all_diagrams
from blueprint.exports.bundle_zip import render_bundle
from blueprint.exports.context_md import render_context
from blueprint.exports.delivery_docx import render_requirements, render_user_stories
from blueprint.exports.diagrams_md import render_diagrams
from blueprint.exports.prd_docx import render_prd
from blueprint.state import SessionState

Renderer = Callable[[SessionState, str], bytes]


@dataclass(frozen=True)
class Kind:
    kind: str
    media_type: str
    file_name: Callable[[str], str]


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
KINDS: dict[str, Kind] = {
    k.kind: k
    for k in (
        Kind("prd-v1.0.docx", DOCX, lambda _: "PRD v1.0.docx"),
        Kind("prd-v1.1.docx", DOCX, lambda _: "PRD v1.1.docx"),
        Kind("prd-v1.2.docx", DOCX, lambda _: "PRD v1.2.docx"),
        Kind("requirements.docx", DOCX, lambda _: "Requirements.docx"),
        Kind("user-stories.docx", DOCX, lambda _: "UserStories.docx"),
        Kind("context.md", "text/markdown; charset=utf-8", lambda _: "context.md"),
        Kind("diagrams.md", "text/markdown; charset=utf-8", lambda _: "Diagrams.md"),
        Kind("bundle.zip", "application/zip", lambda name: f"{name} - Blueprint.zip"),
    )
}

RENDERERS: dict[str, Renderer] = {
    "prd-v1.0.docx": lambda state, name: render_prd(state, name, "1.0"),
    "prd-v1.1.docx": lambda state, name: render_prd(state, name, "1.1"),
    "prd-v1.2.docx": lambda state, name: render_prd(state, name, "1.2"),
    "requirements.docx": render_requirements,
    "user-stories.docx": render_user_stories,
    "context.md": render_context,
    "diagrams.md": render_diagrams,
}


def _bundle(state: SessionState, session_name: str) -> bytes:
    """S10.8: every available kind except the bundle itself."""
    entries = [
        (KINDS[kind].file_name(session_name), RENDERERS[kind](state, session_name))
        for kind in KINDS
        if kind != "bundle.zip" and unmet(state, kind) is None
    ]
    return render_bundle(state, entries)


RENDERERS["bundle.zip"] = _bundle


def unmet(state: SessionState, kind: str) -> str | None:
    """S10.3: why a kind is not available yet, or None when it is."""
    if kind.startswith("prd-v"):
        version = kind.removeprefix("prd-v").removesuffix(".docx")
        if not any(v.version == version for v in state.prd_versions):
            return f"PRD v{version} has not been approved yet"
        return None
    if kind == "diagrams.md":  # drawn as soon as there is something to draw
        if not all_diagrams(state.design):
            return "available once entities or components are recorded"
        return None
    if state.stage != "complete":
        return "available once the ticket breakdown is approved"
    return None


def render(state: SessionState, kind: str, session_name: str) -> bytes:
    return RENDERERS[kind](state, session_name)
