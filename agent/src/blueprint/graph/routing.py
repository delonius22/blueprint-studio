"""Where each run and each node goes next (SPECS S5.1).

Every function here is a pure function of state: no I/O, no model.
"""

from collections.abc import Mapping
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from blueprint.domain.state import DesignState
from blueprint.graph.gates import (
    CONFIRM_STEP,
    REVIEW_IMPORT,
    SIGN_OFF_PRD,
    backend_calls,
    confirm_calls,
    last_answer,
    last_message,
    pending_gate,
    step_approved,
)
from blueprint.review.gaps import LENSES

REVIEWERS = [f"review_{lens}" for lens in LENSES]

# After the PRD sign-off every stage runs by itself; a run (or a retry) resumes where it stopped.
AUTOMATIC_STAGES = {
    "prd_draft": "prd_drafter",
    "spec_synthesis": "spec_synthesizer",
    "seam_gate": "seam_proposer",
    "change_review": "change_applier",
    "ticket_breakdown": "ticket_planner",
    "ticket_gate": "completer",
}
# The node a gate's answer goes to; any other answer, including a rejection, goes to the
# interviewer.
ANSWERED_GATES = {SIGN_OFF_PRD: "prd_drafter", REVIEW_IMPORT: "import_applier"}


def route_start(state: DesignState) -> str | list[str]:
    """Route a new run by what the user just sent.

    An approved ``confirm_step`` goes to the critic (S5.7, S5.8), other gate answers to the node
    that reads them, a newly attached file to the importer, a chat message to the interviewer.
    A run with nothing new ends at once (the workspace re-syncs a thread that way).
    """
    if state.get("last_error"):
        return END
    stage = state.get("stage")
    if stage == "design_review":
        return REVIEWERS  # the review runs (or re-runs after a failure)
    messages = list(state.get("messages") or [])
    answer = last_answer(messages)
    if answer is not None:
        name, content = answer
        if name == CONFIRM_STEP and step_approved(content):
            return "critic"
        return ANSWERED_GATES.get(name, "interviewer")
    if stage == "interview" and any(
        a.get("status") == "parsed" for a in state.get("attachments") or []
    ):
        return "importer"
    if pending_gate(messages):
        return END  # a card is waiting: a run that adds nothing never opens it again
    if stage in AUTOMATIC_STAGES:
        return AUTOMATIC_STAGES[str(stage)]
    return "interviewer" if isinstance(last_message(state), HumanMessage) else END


def route_interviewer(state: DesignState) -> str:
    """Backend calls and confirm_step go to design_tools; a text reply or an error ends the run,
    unless every gap is settled, when the PRD draft starts (S6.5)."""
    if state.get("last_error"):
        return END
    last = last_message(state)
    if isinstance(last, AIMessage) and (backend_calls(state, last) or confirm_calls(last)):
        return "design_tools"
    return "prd_drafter" if state.get("stage") == "prd_draft" else END


def route_design_tools(state: DesignState) -> str:
    """Back to the interviewer, unless a frontend gate call from the same turn awaits the user."""
    messages = state.get("messages") or []
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    turn = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    if turn and any(call["id"] not in answered for call in turn.tool_calls):
        return END
    return "interviewer"


def route_importer(state: DesignState) -> str:
    """A review_import card ends the run; with nothing to review the interviewer goes on."""
    if state.get("last_error") or pending_gate(list(state.get("messages") or [])):
        return END
    return "interviewer"


def route_critic(state: DesignState) -> str | list[str]:
    """After Step 5 the design review starts: three reviewers in parallel (S6.1)."""
    if state.get("last_error") or state.get("stage") != "design_review":
        return END
    return REVIEWERS


def _reached(state: DesignState, stage: str) -> bool:
    return not state.get("last_error") and state.get("stage") == stage


def route_gap_merger(state: DesignState) -> str:
    """Zero gaps goes straight to the PRD draft (S6.4)."""
    return "prd_drafter" if _reached(state, "prd_draft") else END


def route_prd_drafter(state: DesignState) -> str:
    """Sign-off starts the to-spec synthesis (S7.4, S8.1)."""
    return "spec_synthesizer" if _reached(state, "spec_synthesis") else END


def route_change_applier(state: DesignState) -> str:
    """Once the changes are applied, the tickets are planned from the current PRD (S8.5, S8.6)."""
    return "ticket_planner" if _reached(state, "ticket_breakdown") else END


def route_seam_proposer(state: DesignState) -> str:
    """Once PRD v1.1 is frozen: the proposed changes when synthesis made any, otherwise
    straight to the tickets (S8.4)."""
    if state.get("last_error"):
        return END
    return {"change_review": "change_applier", "ticket_breakdown": "ticket_planner"}.get(
        str(state.get("stage")), END
    )


def route_spec_synthesizer(state: DesignState) -> str:
    return END if state.get("last_error") else "seam_proposer"


def route_ticket_planner(state: DesignState) -> str:
    return END if state.get("last_error") else "dag_validator"


def route_dag_validator(state: Mapping[str, Any]) -> str:
    """S9.3: invalid edges go back to the planner with the error (a bounded number of times);
    a valid breakdown completes the session."""
    if state.get("last_error"):
        return END
    planning = state.get("planning") or {}
    return "ticket_planner" if planning.get("error") else "completer"
