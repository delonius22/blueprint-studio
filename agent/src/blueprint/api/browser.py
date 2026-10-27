"""Canvas edits from the browser (SPECS S2.15, S5.9, S11.3).

The workspace writes edits with ``agent.setState``; they reach the agent as the
next run's ``state``. Only the design record and its ID counters may change
there (and ``last_error`` may be cleared); every other session field is the
server's. A write is checked against the checkpoint and either taken whole or
refused whole: a refused write keeps the old state and sets ``last_error``.
"""

from typing import Any

from pydantic import ValidationError

from blueprint.domain.models import DESIGN_PREFIXES, Design
from blueprint.domain.state import SESSION_FIELDS
from blueprint.interview.tools import ID_PATTERN, violations

EDITABLE = ("design", "id_counters")
INVALID_EDIT = "invalid_edit"


def _ids(design: Design) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for field in DESIGN_PREFIXES:
        for item in getattr(design, field):
            items[item.id] = item
    return items


def edit_problems(
    old_design: Design, old_counters: dict[str, int], design: Any, counters: Any
) -> tuple[list[str], Design | None]:
    """Why a browser write cannot be taken; empty when it can (with the validated design)."""
    try:
        candidate = Design.model_validate(design)
    except ValidationError as exc:
        return [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()], None
    if not isinstance(counters, dict) or not all(isinstance(v, int) for v in counters.values()):
        return ["id_counters must map ID prefixes to numbers"], None
    problems = list(violations(candidate, counters))
    for prefix, issued in old_counters.items():
        if counters.get(prefix, 0) < issued:
            problems.append(f"the {prefix} counter cannot go back from {issued}")
    old_ids = _ids(old_design)
    for item_id in _ids(candidate):
        match = ID_PATTERN.match(item_id)
        if (
            item_id not in old_ids
            and match
            and int(match.group(2)) <= old_counters.get(match.group(1), 0)
        ):
            problems.append(f"{item_id} was issued before and cannot be reused")
    return problems, candidate


def changed_ids(before: Design | None, after: Design) -> dict[str, list[str]]:
    """What changed between two designs, by item ID (S5.9)."""
    old = _ids(before or Design())
    new = _ids(after)
    result = {
        "added": [i for i in new if i not in old],
        "changed": [i for i in new if i in old and new[i] != old[i]],
        "deleted": [i for i in old if i not in new],
    }
    if (before or Design()).cap_stance != after.cap_stance:
        result["changed"].append("cap_stance")
    return result


def edit_note(before: Design | None, after: Design) -> str | None:
    changes = changed_ids(before, after)
    parts = [f"{kind} {', '.join(ids)}" for kind, ids in changes.items() if ids]
    if not parts:
        return None
    return (
        "Since your last turn the user edited the canvas directly: "
        + "; ".join(parts)
        + ". Acknowledge these edits by ID in your reply and take them into account."
    )


def apply_browser_write(checkpoint: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """The state a run may start from: the checkpoint plus the browser's valid edits."""
    if not checkpoint:
        return incoming
    state = {k: v for k, v in incoming.items() if k not in SESSION_FIELDS}
    state |= {k: checkpoint[k] for k in SESSION_FIELDS if k in checkpoint}
    if "last_error" in incoming and incoming["last_error"] is None:
        state["last_error"] = None
    if all(incoming.get(k, checkpoint.get(k)) == checkpoint.get(k) for k in EDITABLE):
        return state
    old_design = Design.model_validate(checkpoint["design"])
    problems, candidate = edit_problems(
        old_design,
        dict(checkpoint.get("id_counters") or {}),
        incoming.get("design", checkpoint["design"]),
        incoming.get("id_counters", checkpoint.get("id_counters")),
    )
    if problems:
        state["last_error"] = {
            "code": INVALID_EDIT,
            "message": "That edit was not saved: " + "; ".join(problems),
            "retryable": False,
        }
        return state
    assert candidate is not None
    state["design"] = candidate.model_dump(mode="json")
    state["id_counters"] = dict(incoming.get("id_counters") or {})
    if (state.get("last_error") or {}).get("code") == INVALID_EDIT:
        state["last_error"] = None
    return state
