"""The design review on the review model (SPECS S6, MODEL-CONNECTION.md "Design judge prompts").

Three reviewers, one per lens, each receive the design record (not the
transcript) under ``design-judge-reviewer.md`` with ``{lens}`` filled in. The
merger combines their findings under ``design-judge-merge.md``. The model's
merge is then held to S6.4 by plain code: findings citing no existing item are
dropped, nothing the reviewers did not find is kept, duplicates are combined
keeping the higher severity, and the survivors get ``GAP`` IDs.
"""

import json
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from blueprint.config.assets import Assets
from blueprint.domain.models import Design, Gap, Lens, Model, Severity
from blueprint.interview.tools import all_item_ids, issue_id

LENSES: tuple[Lens, ...] = ("security", "efficiency", "maintainability")
SEVERITY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}
LENS_RANK: dict[str, int] = {lens: i for i, lens in enumerate(LENSES)}


class GapFinding(Model):
    lens: Lens
    item_ids: list[str]
    risk: str
    decision_needed: str
    severity: Severity


class Findings(Model):
    findings: list[GapFinding]


class MergedGaps(Model):
    gaps: list[GapFinding]


def _record(design: Design) -> str:
    return (
        "## Design record\n"
        "Every item carries its ID. Functional requirements (FR) and non-functional requirements "
        "(NFR) are part of the record.\n\n```json\n"
        + design.model_dump_json(indent=2, exclude_defaults=False)
        + "\n```"
    )


def reviewer_messages(assets: Assets, lens: Lens, design: Design) -> list[BaseMessage]:
    """S6.1: the lens prompt and the design record; the transcript is deliberately absent."""
    return [
        SystemMessage(assets.design_judge_reviewer.replace("{lens}", lens)),
        HumanMessage(_record(design)),
    ]


def merger_messages(
    assets: Assets, design: Design, findings: Sequence[GapFinding]
) -> list[BaseMessage]:
    payload = json.dumps({"findings": [f.model_dump() for f in findings]}, indent=2)
    return [
        SystemMessage(assets.design_judge_merge),
        HumanMessage(
            _record(design)
            + "\n\n## Findings from the three design judges\n```json\n"
            + payload
            + "\n```"
        ),
    ]


def _normal(text: str) -> str:
    return re.sub(r"\W+", " ", text).strip().casefold()


def cited(findings: Sequence[GapFinding], design: Design) -> list[GapFinding]:
    """Keep only item IDs that exist; drop findings left citing nothing (S6.4)."""
    existing = all_item_ids(design)
    kept: list[GapFinding] = []
    for finding in findings:
        ids = list(dict.fromkeys(i for i in finding.item_ids if i in existing))
        if ids and finding.risk.strip() and finding.decision_needed.strip():
            kept.append(finding.model_copy(update={"item_ids": ids}))
    return kept


def combine(findings: Sequence[GapFinding]) -> list[GapFinding]:
    """Findings on the same items with the same risk become one, keeping the higher severity."""
    groups: dict[tuple[tuple[str, ...], str], GapFinding] = {}
    for finding in findings:
        key = (tuple(sorted(finding.item_ids)), _normal(finding.risk))
        current = groups.get(key)
        if current is None or (SEVERITY_RANK[finding.severity], LENS_RANK[finding.lens]) < (
            SEVERITY_RANK[current.severity],
            LENS_RANK[current.lens],
        ):
            groups[key] = finding
    return list(groups.values())


def held_to_inputs(merged: Sequence[GapFinding], inputs: Sequence[GapFinding]) -> list[GapFinding]:
    """The merger may only filter and combine (G3): each gap must rest on an input finding of
    the same lens that cites all of its items."""
    return [
        gap
        for gap in merged
        if any(f.lens == gap.lens and set(gap.item_ids) <= set(f.item_ids) for f in inputs)
    ]


def gap_register(
    merged: Sequence[GapFinding],
    inputs: Sequence[GapFinding],
    design: Design,
    counters: dict[str, int],
) -> list[Gap]:
    """S6.4: the merged findings, held to the rules, ordered by severity, with GAP IDs."""
    survivors = combine(held_to_inputs(cited(merged, design), inputs))
    survivors.sort(key=lambda g: (SEVERITY_RANK[g.severity], g.item_ids[0]))
    return [
        Gap(id=issue_id(counters, "GAP"), status="open", **finding.model_dump())
        for finding in survivors
    ]


def review_summary(gaps: Sequence[Gap]) -> str:
    if not gaps:
        return "Design review complete: the three design judges found no gaps. Next, the PRD draft."
    counts = {s: sum(1 for g in gaps if g.severity == s) for s in ("high", "medium", "low")}
    detail = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    return (
        f"Design review complete: {len(gaps)} gap{'s' if len(gaps) != 1 else ''} ({detail}). "
        "They are listed in the gap register; answer each one or accept it as an open risk."
    )


def findings_payload(findings: Sequence[GapFinding], lens: Lens) -> list[dict[str, Any]]:
    """A reviewer reports for its own lens only."""
    return [f.model_copy(update={"lens": lens}).model_dump() for f in findings]
