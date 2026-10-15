"""Proposed changes to signed-off PRD content, and PRD v1.2 (SPECS S8.5, S2.13, PRD FR-19).

How an approved change is applied is QUESTIONS.md Q-11 (open); this module holds
reading (a): every change is an exact edit of what the user saw, and a change these
rules cannot apply is rejected at validation (S8.2), so an approved change is
always applied exactly as approved.
"""

from collections.abc import Sequence

from blueprint.design import issue_id
from blueprint.domain import Feature, PrdDoc, PrdNfr, PrdRequirement, ProposedChange

TEXT_LISTS = ("goals", "users", "scope", "out_of_scope")


def change_problem(change: ProposedChange, doc: PrdDoc) -> str | None:
    """Why ``change`` cannot be applied to ``doc``; None when it can."""
    section, kind, target = change.section, change.kind, change.target_id
    text = (change.proposed_text or "").strip()
    current = (change.current_text or "").strip()
    if section == "open_gaps":
        return "open gaps come from the design review and cannot be changed"
    if section == "problem_statement":
        if kind in ("add", "modify") and not text:
            return "needs proposed_text"
        if kind in ("modify", "remove") and current and current not in doc.problem_statement:
            return "current_text is not in the problem statement"
        return None
    if section in TEXT_LISTS:
        entries: list[str] = getattr(doc, section)
        if kind in ("add", "modify") and not text:
            return "needs proposed_text"
        if kind in ("modify", "remove") and current not in entries:
            return f"current_text must equal an entry of {section}"
        return None
    items = {
        "functional_requirements": {r.id for r in doc.functional_requirements},
        "non_functional_requirements": {n.id for n in doc.non_functional_requirements},
        "features": {f.id for f in doc.features},
    }[section]
    features = {f.id for f in doc.features}
    if kind == "add":
        if section == "features":
            return "a feature cannot be added on its own: it must group at least one requirement"
        if not text:
            return "needs proposed_text"
        if section == "functional_requirements" and target not in features:
            return "adding a functional requirement needs target_id naming its feature (F-)"
        return None
    if target not in items:
        return f"{kind} needs target_id naming an item of {section}"
    if kind == "modify" and not text:
        return "needs proposed_text"
    if kind == "remove" and section == "features":
        feature = next(f for f in doc.features if f.id == target)
        if feature.requirement_ids:
            return "a feature can be removed only once it groups no requirement"
    return None


def apply_changes(
    doc: PrdDoc, changes: Sequence[ProposedChange], counters: dict[str, int]
) -> PrdDoc:
    """A copy of ``doc`` with every change applied in order (reading (a) of Q-11)."""
    result = doc.model_copy(deep=True)
    for change in changes:
        text = (change.proposed_text or "").strip()
        current = (change.current_text or "").strip()
        section, kind, target = change.section, change.kind, change.target_id
        if section == "problem_statement":
            if kind == "add":
                result.problem_statement = f"{result.problem_statement}\n\n{text}".strip()
            elif kind == "modify":
                result.problem_statement = (
                    result.problem_statement.replace(current, text, 1) if current else text
                )
            else:
                result.problem_statement = result.problem_statement.replace(current, "", 1).strip()
        elif section in TEXT_LISTS:
            entries = list(getattr(result, section))
            if kind == "add":
                entries.append(text)
            elif kind == "modify":
                entries[entries.index(current)] = text
            else:
                entries.remove(current)
            setattr(result, section, entries)
        elif section == "functional_requirements":
            if kind == "add":
                new = PrdRequirement(
                    id=issue_id(counters, "FR"), feature_id=str(target), statement=text
                )
                result.functional_requirements.append(new)
                result.features = [
                    f.model_copy(update={"requirement_ids": [*f.requirement_ids, new.id]})
                    if f.id == target
                    else f
                    for f in result.features
                ]
            elif kind == "modify":
                result.functional_requirements = [
                    r.model_copy(update={"statement": text}) if r.id == target else r
                    for r in result.functional_requirements
                ]
            else:
                result.functional_requirements = [
                    r for r in result.functional_requirements if r.id != target
                ]
                kept: list[Feature] = []
                for feature in result.features:
                    ids = [i for i in feature.requirement_ids if i != target]
                    if ids:
                        kept.append(feature.model_copy(update={"requirement_ids": ids}))
                result.features = kept
        elif section == "non_functional_requirements":
            if kind == "add":
                result.non_functional_requirements.append(
                    PrdNfr(id=issue_id(counters, "NFR"), category="other", statement=text)
                )
            elif kind == "modify":
                result.non_functional_requirements = [
                    n.model_copy(update={"statement": text}) if n.id == target else n
                    for n in result.non_functional_requirements
                ]
            else:
                result.non_functional_requirements = [
                    n for n in result.non_functional_requirements if n.id != target
                ]
        elif section == "features":
            if kind == "modify":
                result.features = [
                    f.model_copy(update={"description": text}) if f.id == target else f
                    for f in result.features
                ]
            else:
                result.features = [f for f in result.features if f.id != target]
    return result


def change_decisions(answer: object) -> dict[str, str]:
    """review_changes answers a decision per change ID (S8.5): approved or rejected."""
    items = answer.get("decisions") if isinstance(answer, dict) else answer
    decisions: dict[str, str] = {}
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and isinstance(item.get("change_id"), str):
            value = str(item.get("decision", "")).lower()
            if value in ("approve", "approved"):
                decisions[item["change_id"]] = "approved"
            elif value in ("reject", "rejected"):
                decisions[item["change_id"]] = "rejected"
    return decisions
