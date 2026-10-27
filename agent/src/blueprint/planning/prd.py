"""PRD v1.0: drafting and its rules (SPECS S7.1, S7.2, S2.10, S2.12).

The model writes only the narrative parts: problem statement, goals, users,
features (grouping the functional requirements), scope, and which features each
open gap concerns. Requirements are never rewritten: the functional and
non-functional requirements are copied verbatim from the design record, the
out-of-scope list from the design's notes, and the open gaps are the accepted
gaps.
"""

import json
from collections.abc import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import Field

from blueprint.domain.models import Design, Feature, Gap, Model, PrdDoc, PrdNfr, PrdRequirement
from blueprint.interview.tools import issue_id


class FeatureDraft(Model):
    ref: str = Field(description="A short label of your choice, unique within this draft, e.g. f1.")
    name: str
    description: str
    requirement_ids: list[str] = Field(description="The FR- IDs this feature groups.")


class GapFeatures(Model):
    gap_id: str
    feature_refs: list[str] = Field(description="The refs of the features this open gap concerns.")


class PrdDraftOut(Model):
    problem_statement: str
    goals: list[str]
    users: list[str] = Field(description="Users and stakeholders.")
    features: list[FeatureDraft]
    scope: list[str] = Field(description="What is in scope, in plain sentences.")
    gap_features: list[GapFeatures]


def drafter_messages(
    design: Design,
    open_gaps: Sequence[Gap],
    previous: PrdDoc | None = None,
    reason: str | None = None,
) -> list[BaseMessage]:
    system = (
        "You draft PRD v1.0 for a system the user designed with an interviewer. Write the problem "
        "statement, goals, users and stakeholders, and scope from the design record below, and group "
        "every functional requirement (FR) into features: each FR in exactly one feature, each feature "
        "with at least one FR. Do not add, drop or reword requirements; they are copied into the PRD "
        "verbatim. For every open gap, name the features it concerns. Do not add features, "
        "requirements or solutions that the design record does not contain."
    )
    parts = [
        "## Design record\n```json\n" + design.model_dump_json(indent=2) + "\n```",
        "## Open gaps and accepted risks\n```json\n"
        + json.dumps([g.model_dump(mode="json") for g in open_gaps], indent=2)
        + "\n```",
    ]
    if previous is not None and reason:
        parts.append(
            "## Your previous draft, which the user rejected\n```json\n"
            + previous.model_dump_json(
                indent=2, include={"problem_statement", "goals", "users", "features", "scope"}
            )
            + "\n```\n## The user's reason\n"
            + reason
        )
    return [SystemMessage(system), HumanMessage("\n\n".join(parts))]


def draft_problems(out: PrdDraftOut, design: Design, open_gaps: Sequence[Gap]) -> list[str]:
    """S7.2: every FR in exactly one feature; every feature has an FR; every open gap has a
    feature; no unknown IDs."""
    problems: list[str] = []
    frs = [r.id for r in design.functional_requirements]
    refs = [f.ref for f in out.features]
    if len(set(refs)) != len(refs):
        problems.append("feature refs must be unique")
    for feature in out.features:
        if not feature.requirement_ids:
            problems.append(
                f"feature {feature.ref} ({feature.name}) groups no functional requirement"
            )
        for requirement in feature.requirement_ids:
            if requirement not in frs:
                problems.append(
                    f"feature {feature.ref} names {requirement}, which is not a functional requirement"
                )
    for requirement in frs:
        count = sum(requirement in f.requirement_ids for f in out.features)
        if count != 1:
            problems.append(f"{requirement} is in {count} features; it must be in exactly one")
    gap_ids = {g.id for g in open_gaps}
    mapped: dict[str, list[str]] = {}
    for entry in out.gap_features:
        if entry.gap_id not in gap_ids:
            problems.append(f"{entry.gap_id} is not an open gap")
        for ref in entry.feature_refs:
            if ref not in refs:
                problems.append(f"{entry.gap_id} names feature {ref}, which is not in the draft")
        mapped.setdefault(entry.gap_id, []).extend(entry.feature_refs)
    for gap in open_gaps:
        if not mapped.get(gap.id):
            problems.append(f"open gap {gap.id} must name at least one feature")
    return problems


def build_prd(
    out: PrdDraftOut,
    design: Design,
    open_gaps: Sequence[Gap],
    counters: dict[str, int],
    previous: PrdDoc | None = None,
) -> PrdDoc:
    """Assemble the PRD: the model's narrative plus the verbatim copies of S7.1.

    A feature keeps its ID from the previous draft when its name is unchanged; any other
    feature gets a new F- ID (S2.5)."""
    earlier = {f.name.strip().casefold(): f.id for f in (previous.features if previous else [])}
    ids: dict[str, str] = {}
    features: list[Feature] = []
    for draft in out.features:
        feature_id = earlier.pop(draft.name.strip().casefold(), None) or issue_id(counters, "F")
        ids[draft.ref] = feature_id
        features.append(
            Feature(
                id=feature_id,
                name=draft.name,
                description=draft.description,
                requirement_ids=draft.requirement_ids,
            )
        )
    feature_of = {r: f.id for f in features for r in f.requirement_ids}
    gap_features = {e.gap_id: [ids[ref] for ref in e.feature_refs] for e in out.gap_features}
    return PrdDoc(
        problem_statement=out.problem_statement,
        goals=out.goals,
        users=out.users,
        features=features,
        functional_requirements=[
            PrdRequirement(id=r.id, feature_id=feature_of[r.id], statement=r.statement)
            for r in design.functional_requirements
        ],
        non_functional_requirements=[
            PrdNfr(
                id=n.id,
                category=n.category,
                statement=n.statement,
                metric=n.metric,
                target=n.target,
                unit=n.unit,
            )
            for n in design.non_functional_requirements
        ],
        scope=out.scope,
        out_of_scope=[note.text for note in design.out_of_scope],
        open_gaps=[
            g.model_copy(update={"feature_ids": list(dict.fromkeys(gap_features.get(g.id, [])))})
            for g in open_gaps
        ],
    )


def signoff_summary(doc: PrdDoc) -> str:
    return (
        f"PRD v1.0 is ready for sign-off: {len(doc.features)} features, "
        f"{len(doc.functional_requirements)} functional and {len(doc.non_functional_requirements)} "
        f"non-functional requirements, {len(doc.open_gaps)} open gaps and accepted risks. "
        "Review it in the PRD viewer, then sign it off or tell me what to change."
    )


def current_prd(versions: Sequence[dict[str, object]]) -> PrdDoc | None:
    """S8.6: the current PRD is the newest version; every later stage and download reads it."""
    return PrdDoc.model_validate(versions[-1]["doc"]) if versions else None
