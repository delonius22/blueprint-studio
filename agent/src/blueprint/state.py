"""Session state (SPECS S2.1, S2.2, S3.1).

Values are plain JSON (see ``blueprint.domain``) so that checkpoints, AG-UI
state snapshots and frontend writes share one representation.
"""

from typing import Any

from copilotkit import CopilotKitState

from blueprint.domain import Design

JSON = dict[str, Any]


class DesignState(CopilotKitState):
    """The single source of truth for a session (S2.1, S2.2)."""

    session_id: str
    stage: str
    current_step: int
    confirmed_steps: list[int]
    design: JSON
    agent_design: JSON | None
    critiques: list[JSON]
    scorecard: JSON | None
    gaps: list[JSON]
    review_model_distinct: bool
    prd_draft: JSON | None
    prd_versions: list[JSON]
    proposed_changes: list[JSON]
    seams: list[JSON]
    tickets: list[JSON]
    tickets_approved_at: str | None
    id_counters: dict[str, int]
    tokens_used: dict[str, int]
    token_budget: int
    last_error: JSON | None


# Fields of DesignState that belong to the session (S2.2), as opposed to the
# conversation (messages) and CopilotKit's own bookkeeping.
SESSION_FIELDS: tuple[str, ...] = tuple(
    name for name in DesignState.__annotations__ if name not in ("messages", "copilotkit")
)


def new_session_state(session_id: str, token_budget: int, review_model_distinct: bool) -> JSON:
    """Every S2.2 field with the initial values of S3.1."""
    return {
        "session_id": session_id,
        "stage": "interview",
        "current_step": 1,
        "confirmed_steps": [],
        "design": Design().model_dump(mode="json"),
        "agent_design": None,
        "critiques": [],
        "scorecard": None,
        "gaps": [],
        "review_model_distinct": review_model_distinct,
        "prd_draft": None,
        "prd_versions": [],
        "proposed_changes": [],
        "seams": [],
        "tickets": [],
        "tickets_approved_at": None,
        "id_counters": {},
        "tokens_used": {"interview": 0, "review": 0},
        "token_budget": token_budget,
        "last_error": None,
    }
