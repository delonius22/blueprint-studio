"""Session state (SPECS S2). The full field list arrives with sessions in T-02."""

from copilotkit import CopilotKitState


class DesignState(CopilotKitState):
    """The single source of truth for a session (S2.1)."""
