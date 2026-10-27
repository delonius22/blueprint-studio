"""context.md, the Jira hand-off (SPECS S10.7, S12.3, PRD FR-26, G3).

A fixed template, in order: role, Jira project, mapping table, rules, the features,
user stories, tickets and open gaps of the current PRD and breakdown, and the
required report; it ends with the to-tickets / to-spec attribution line.
"""

from blueprint.domain.models import Feature, PrdDoc, Ticket, UserStory
from blueprint.domain.state import SessionState
from blueprint.exports.diagrams import markdown

ATTRIBUTION = "*Ticket and spec method: to-tickets / to-spec, mattpocock-skills 1.2.3 (MIT, © 2026 Matt Pocock).*"


# The user fills these in; the trailing space matches the worked example (agent/tests/expected/example-context.md).
BLANK = " "


def _header(name: str) -> str:
    return f"""# Jira hand-off — {name}

## 1. Your role

You are creating Jira issues for **{name}**. This file is your only source: every issue you create comes from it, and nothing else does. Work through the sections below in order, follow the mapping table exactly as the user has left it, and stop and ask whenever this file does not settle a question.

## 2. Jira project

- Site:{BLANK}
- Project key:{BLANK}

If either line is blank when you start, ask the user for it before doing anything else.

## 3. Mapping table — edit this table to match your Jira, then follow it exactly

| Concept | Jira issue type | Parent | Links |
|---|---|---|---|
| Feature (`F-n`) | Epic | — | — |
| User story (`US-n`) | Story | The Epic of its feature | — |
| Ticket (`T-nn`) | Task | The Epic of its first delivered story | "relates to" each delivered story; "is blocked by" each blocking ticket |

## 4. Rules

- Create exactly one issue per ID listed in sections 5 to 7, and nothing else: no extra issues, sub-tasks, features, stories or tickets.
- Use each item's **Summary** line as the issue summary and its remaining fields as the description, as given. Format them for Jira; do not reword them.
- Create in this order: features, then stories, then tickets in ID order, so every parent and link target exists when you need it.
- Paste each open gap (section 8) into the description of its feature's Epic, under the heading "Open gaps and accepted risks". Never create an issue for a gap.
- Before creating anything, search the project for issues whose summary starts with any ID in this file. If one exists, stop and ask.
- If an issue type or link type named in the mapping table does not exist in the project, stop and ask.
- If anything else is ambiguous, stop and ask. Never guess and never fill a gap with your own content.
"""


REPORT = """## 9. Report

When you have finished, reply with:

1. A table with columns ID, Issue type, Jira key, Parent key, Links created, with one row per ID in sections 5 to 7.
2. A list of anything you did not create and why. It should be empty.
"""
CLOSING = f"""
---

{ATTRIBUTION}
"""
# The template's own footer, before the diagram appendix existed.
FOOTER = REPORT + CLOSING


def _capitalised(text: str) -> str:
    text = text.strip()
    return text[:1].upper() + text[1:]


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def _feature(feature: Feature, doc: PrdDoc) -> list[str]:
    statements = {r.id: r.statement for r in doc.functional_requirements}
    lines = [
        f"### {feature.id}: {feature.name}",
        "",
        f"- **Summary:** {feature.id}: {feature.name}",
    ]
    if feature.description.strip():
        lines.append(f"- **Description:** {feature.description.strip()}")
    lines.append("- **Requirements:**")
    lines += [f"  - {r}: {statements.get(r, '')}" for r in feature.requirement_ids]
    return [*lines, ""]


def _story(story: UserStory, tickets: list[Ticket]) -> list[str]:
    delivered = [t.id for t in tickets if story.id in t.story_ids]
    lines = [
        f"### {story.id}",
        "",
        f"- **Summary:** {story.id}: {_capitalised(story.feature)}",
        f"- **Feature:** {story.feature_id}",
        f"- **Story:** As {story.actor}, I want {story.feature.strip()}, so that {_sentence(story.benefit)}",
        f"- **Requirements:** {', '.join(story.requirement_ids)}",
    ]
    if story.acceptance_criteria:
        lines.append("- **Acceptance criteria:**")
        lines += [f"  - {c}" for c in story.acceptance_criteria]
    lines.append(f"- **Delivered by:** {', '.join(delivered) or 'None'}")
    return [*lines, ""]


def _ticket(ticket: Ticket, stories: dict[str, UserStory]) -> list[str]:
    first = ticket.story_ids[0]
    parent = stories[first].feature_id if first in stories else "unknown"
    lines = [
        f"### {ticket.id}: {ticket.title}",
        "",
        f"- **Summary:** {ticket.id}: {ticket.title}",
        f"- **Parent feature:** {parent} (from {first})",
        f"- **Delivers stories:** {', '.join(ticket.story_ids)}",
        f"- **Blocked by:** {', '.join(ticket.blocked_by) or 'None'}",
        f"- **Kind:** {ticket.kind}",
        f"- **What to build:** {ticket.what_to_build.strip()}",
        "- **Acceptance criteria:**",
    ]
    lines += [f"  - [ ] {c}" for c in ticket.acceptance_criteria]
    return [*lines, ""]


def _gaps(doc: PrdDoc) -> list[str]:
    if not doc.open_gaps:
        return ["None recorded for this project.", ""]
    lines: list[str] = []
    for feature in doc.features:
        gaps = [g for g in doc.open_gaps if feature.id in g.feature_ids]
        if not gaps:
            continue
        lines += [f"### {feature.id}: {feature.name}", ""]
        for gap in gaps:
            note = f" Note: {gap.note}" if gap.note else ""
            lines.append(
                f"- **{gap.id}** ({gap.lens}, {gap.severity}; affects {', '.join(gap.item_ids)}): "
                f"Risk: {gap.risk} Decision needed: {gap.decision_needed}{note}"
            )
        lines.append("")
    return lines


def render_context(state: SessionState, session_name: str) -> bytes:
    if not state.prd_versions or state.tickets_approved_at is None:
        raise LookupError("available once the ticket breakdown is approved")
    doc = state.prd_versions[-1].doc  # S8.6: the current PRD
    tickets = sorted(state.tickets, key=lambda t: t.id)
    stories = {s.id: s for s in doc.user_stories}
    lines = [_header(session_name), "## 5. Features", ""]
    for feature in doc.features:
        lines += _feature(feature, doc)
    lines += ["## 6. User stories", ""]
    for story in doc.user_stories:
        lines += _story(story, tickets)
    lines += ["## 7. Tickets", ""]
    for ticket in tickets:
        lines += _ticket(ticket, stories)
    lines += ["## 8. Open gaps", "", *_gaps(doc)]
    return ("\n".join(lines) + "\n" + REPORT + _appendix(state) + CLOSING).encode("utf-8")


def _appendix(state: SessionState) -> str:
    """The design's diagrams after the report: context for the reader, never issues."""
    diagrams = markdown(state.design, heading_level=3)
    if not diagrams:
        return ""
    intro = "These illustrate the design. They are not items: do not create issues from them."
    return "\n".join(["", "## Appendix: diagrams (reference only)", "", intro, "", *diagrams])
