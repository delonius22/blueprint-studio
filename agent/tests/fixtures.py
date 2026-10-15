"""A completed session for the export seam: PRD v1.0 and v1.1, stories, approved tickets."""

from typing import Any

from test_prd import signed_off_state

from blueprint.domain import Ticket, UserStory
from blueprint.state import SessionState


def _story(n: int, feature: str, requirements: list[str], want: str, benefit: str) -> UserStory:
    return UserStory(
        id=f"US-{n}",
        feature_id=feature,
        actor="an anonymous user" if feature == "F-1" else "a link owner",
        feature=want,
        benefit=benefit,
        acceptance_criteria=[f"Criterion {n}.1", f"Criterion {n}.2"],
        requirement_ids=requirements,
    )


STORIES = [
    _story(1, "F-1", ["FR-1", "NFR-1"], "to shorten a long URL", "I can share it"),
    _story(2, "F-1", ["FR-2"], "to be redirected from a short URL", "I reach the page"),
    _story(3, "F-2", ["FR-3"], "to see my links", "I can manage them"),
]
TICKETS = [
    Ticket(id="T-01", title="Walking skeleton", what_to_build="Shorten a URL end to end.", blocked_by=[],
           acceptance_criteria=["POST /urls returns a code"], story_ids=["US-1"], kind="slice"),
    Ticket(id="T-02", title="Redirect", what_to_build="Resolve a code to its URL.", blocked_by=["T-01"],
           acceptance_criteria=["GET /{code} answers 301", "Unknown codes answer 404"], story_ids=["US-2"], kind="slice"),
    Ticket(id="T-03", title="Owner list", what_to_build="List an owner's links.", blocked_by=["T-01"],
           acceptance_criteria=["Lists links newest first"], story_ids=["US-3"], kind="slice"),
]  # fmt: skip


def complete_state(**extra: Any) -> SessionState:
    base = signed_off_state()
    v10 = base.prd_versions[0]
    v11 = v10.doc.model_copy(update={
        "solution": "A small web service that issues short codes and redirects.",
        "user_stories": STORIES,
        "implementation_decisions": ["Codes are base62"],
        "testing_decisions": ["SEAM-1: HTTP API. Drive the public API end to end."],
        "further_notes": ["Analytics may come later", "GAP-1: Open creation Decision needed: Who? Note: v1"],
    })  # fmt: skip
    return SessionState.model_validate(
        base.model_dump()
        | {
            "stage": "complete",
            "prd_draft": v11.model_dump(),
            "prd_versions": [
                v10.model_dump(),
                {"version": "1.1", "approved_at": "2026-10-14T13:00:00Z", "doc": v11.model_dump()},
            ],
            "tickets": [t.model_dump() for t in TICKETS],
            "tickets_approved_at": "2026-10-14T15:45:00Z",
        }
        | extra
    )
