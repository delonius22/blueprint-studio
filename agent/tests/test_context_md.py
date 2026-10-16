"""T-17: the Jira hand-off, context.md (S10.3, S10.7, S12.3, FR-26, G3)."""

import re
from typing import Any

from conftest import REPO_ROOT
from fixtures import complete_state
from psycopg_pool import AsyncConnectionPool
from service import build_service, client

from blueprint.domain import Gap
from blueprint.downloads import render

EXPECTED = REPO_ROOT / "agent" / "tests" / "expected" / "context.md"
EXAMPLE = REPO_ROOT / "agent" / "tests" / "expected" / "example-context.md"


def rendered(**extra: Any) -> str:
    return render(complete_state(**extra), "context.md", "URL shortener").decode("utf-8")


def test_context_md_matches_the_checked_in_expected_file_byte_for_byte() -> None:
    assert render(complete_state(), "context.md", "URL shortener") == EXPECTED.read_bytes()


def test_the_fixed_parts_match_the_worked_example() -> None:
    """Sections 1-4, the report and the attribution are the template of the worked example."""
    example = EXAMPLE.read_text().replace("Blueprint Studio", "URL shortener")
    ours = rendered()

    def fixed(text: str) -> tuple[str, str]:
        # The diagram appendix sits between the report and the attribution; it is no template.
        tail = re.sub(r"\n## Appendix: diagrams .*?(?=\n---\n)", "", text, flags=re.DOTALL)
        return text[: text.index("## 5. Features")], tail[tail.index("## 9. Report") :]

    assert fixed(ours) == fixed(example)
    headings = re.findall(r"^## .+$", ours, flags=re.MULTILINE)
    assert headings == [
        "## 1. Your role", "## 2. Jira project",
        "## 3. Mapping table — edit this table to match your Jira, then follow it exactly",
        "## 4. Rules", "## 5. Features", "## 6. User stories", "## 7. Tickets", "## 8. Open gaps", "## 9. Report",
        "## Appendix: diagrams (reference only)",
    ]  # fmt: skip


def test_the_mapping_rules_and_stop_conditions_are_all_there() -> None:
    text = rendered()
    assert "| Feature (`F-n`) | Epic | — | — |" in text
    assert "| User story (`US-n`) | Story | The Epic of its feature | — |" in text
    assert (
        '| Ticket (`T-nn`) | Task | The Epic of its first delivered story | "relates to" each delivered story; "is blocked by" each blocking ticket |'
        in text
    )
    for rule in (
        "no extra issues, sub-tasks, features, stories or tickets",
        "Use each item's **Summary** line as the issue summary",
        "features, then stories, then tickets in ID order",
        "Never create an issue for a gap",
        "search the project for issues whose summary starts with any ID in this file. If one exists, stop and ask",
        "does not exist in the project, stop and ask",
        "If anything else is ambiguous, stop and ask",
        "If either line is blank when you start, ask the user",
    ):
        assert rule in text, rule
    assert text.endswith(
        "*Ticket and spec method: to-tickets / to-spec, mattpocock-skills 1.2.3 (MIT, © 2026 Matt Pocock).*\n"
    )


def test_every_feature_story_and_ticket_appears_with_every_field() -> None:
    state = complete_state()
    doc = state.prd_versions[-1].doc
    text = rendered()
    for feature in doc.features:
        assert f"- **Summary:** {feature.id}: {feature.name}" in text
        assert f"- **Description:** {feature.description}" in text
    for r in doc.functional_requirements:
        assert f"  - {r.id}: {r.statement}" in text
    for story in doc.user_stories:
        block = text[text.index(f"### {story.id}\n") :].split("\n### ")[0]
        assert f"- **Summary:** {story.id}: {story.feature[0].upper()}{story.feature[1:]}" in block
        assert f"- **Feature:** {story.feature_id}" in block
        assert (
            f"- **Story:** As {story.actor}, I want {story.feature}, so that {story.benefit}."
            in block
        )
        assert f"- **Requirements:** {', '.join(story.requirement_ids)}" in block
        assert all(f"  - {c}" in block for c in story.acceptance_criteria)
    for ticket in state.tickets:
        block = text[text.index(f"### {ticket.id}: ") :].split("\n### ")[0]
        assert f"- **Summary:** {ticket.id}: {ticket.title}" in block
        assert f"- **Blocked by:** {', '.join(ticket.blocked_by) or 'None'}" in block
        assert f"- **What to build:** {ticket.what_to_build}" in block
        assert all(f"  - [ ] {c}" in block for c in ticket.acceptance_criteria)
    assert "- **Parent feature:** F-2 (from US-3)" in text


def test_every_open_gap_appears_under_each_of_its_features() -> None:
    base = complete_state()
    v11 = base.prd_versions[-1]
    two = Gap(id="GAP-3", lens="maintainability", item_ids=["FR-2", "FR-3"], risk="No owner", decision_needed="Who owns it?",
              severity="medium", status="accepted", feature_ids=["F-1", "F-2"])  # fmt: skip
    doc = v11.doc.model_copy(update={"open_gaps": [*v11.doc.open_gaps, two]})
    text = rendered(prd_versions=[base.prd_versions[0], v11.model_copy(update={"doc": doc})])
    gaps = text[text.index("## 8. Open gaps") : text.index("## 9. Report")]
    assert gaps.count("**GAP-3**") == 2 and gaps.count("**GAP-1**") == 1
    assert (
        gaps.index("### F-1: Short links")
        < gaps.index("**GAP-1**")
        < gaps.index("### F-2: Link owners")
    )
    assert "Note: v1" in gaps
    assert "GAP" not in text[: text.index("## 8. Open gaps")].split("## 4. Rules")[1].replace(
        "Paste each open gap", ""
    )


async def test_context_md_is_409_before_completion_then_served(
    pool: AsyncConnectionPool[Any],
) -> None:
    app = await build_service(pool)
    async with client(app) as http:
        session = (await http.post("/api/sessions", json={"name": "URL shortener"})).json()
        url = f"/api/sessions/{session['id']}/downloads/context.md"
        assert (await http.get(url)).status_code == 409
        config = {"configurable": {"thread_id": session["id"]}}
        await app.state.graph.aupdate_state(config, complete_state().model_dump(mode="json"))
        response = await http.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.content == EXPECTED.read_bytes()
