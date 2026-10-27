"""A completed session for the export seam: PRD v1.0 and v1.1, stories, approved tickets."""

from typing import Any

from test_prd import signed_off_state

from blueprint.domain.models import Ticket, UserStory
from blueprint.domain.state import SessionState


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


# Steps 2 and 3 of the design, so a complete session has diagrams to draw.
STEPS_2_AND_3: dict[str, Any] = {
    "entities": [
        {"id": "ENT-1", "name": "Link", "fields": [
            {"name": "code", "type": "char(7)", "key": "pk"},
            {"name": "target", "type": "text", "key": "none"},
            {"name": "owner_id", "type": "uuid", "key": "fk", "references": "ENT-2"},
        ]},
        {"id": "ENT-2", "name": "Owner", "fields": [{"name": "id", "type": "uuid", "key": "pk"}]},
    ],
    "relationships": [{"id": "REL-1", "from_entity": "ENT-2", "to_entity": "ENT-1", "cardinality": "1:N"}],
    "components": [
        {"id": "CMP-1", "name": "Browser", "kind": "client", "responsibility": "Follows short links"},
        {"id": "CMP-2", "name": "Redirect service", "kind": "service", "responsibility": "Resolves codes"},
        {"id": "CMP-3", "name": "Links", "kind": "database", "responsibility": "Stores links"},
    ],
    "flows": [
        {"id": "FLOW-1", "name": "Follow a short link", "kind": "read", "steps": [
            {"from_component": "CMP-1", "to_component": "CMP-2", "label": "GET /{code}"},
            {"from_component": "CMP-2", "to_component": "CMP-3", "label": "look up the code"},
        ]},
    ],
}  # fmt: skip


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
            "design": base.design.model_dump() | STEPS_2_AND_3,
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
