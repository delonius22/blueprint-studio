"""The Step 5 scorecard (SPECS S5.8, S2.8, PRD FR-9, G5).

Every score is backed by verbatim quotes from the session. PRD OQ-6 asked which
turns may be quoted; the answer is the user's own messages only, so QUOTES_FROM
is "user".
"""

import re
from collections.abc import Sequence
from typing import Annotated, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import Field, ValidationError

from blueprint.assets import Assets
from blueprint.domain import DIMENSIONS, Design, DimensionScore, Model, Scorecard
from blueprint.llm import InvalidStructuredOutput, Meter, ModelGateway
from blueprint.prompts import design_summary

# Q-10 (PRD OQ-6), answered: quote only the user's messages. "conversation" would also allow
# the interviewer's turns; it is kept only so tests can show the check distinguishes the two.
QuotesFrom = Literal["user", "conversation"]
QUOTES_FROM: QuotesFrom = "user"


class ScorecardError(Exception):
    """The model's scorecard was still invalid after one corrective retry."""


class ScorecardDraft(Model):
    dimensions: Annotated[list[DimensionScore], Field(min_length=5, max_length=5)]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _quotable(messages: Sequence[BaseMessage], quotes_from: QuotesFrom) -> list[str]:
    kinds: tuple[type[BaseMessage], ...] = (
        (HumanMessage,) if quotes_from == "user" else (HumanMessage, AIMessage)
    )
    return [_normalise(m.text) for m in messages if isinstance(m, kinds) and m.text.strip()]


def problems(
    draft: ScorecardDraft, messages: Sequence[BaseMessage], quotes_from: QuotesFrom
) -> list[str]:
    """Why a draft cannot be stored: dimensions missing or repeated, evidence missing or not a quote."""
    found: list[str] = []
    names = [d.dimension for d in draft.dimensions]
    for dimension in DIMENSIONS:
        if names.count(dimension) != 1:
            found.append(f"score '{dimension}' exactly once")
    sources = _quotable(messages, quotes_from)
    where = "the user's messages" if quotes_from == "user" else "the conversation"
    for score in draft.dimensions:
        if not score.evidence:
            found.append(f"give '{score.dimension}' at least one quote as evidence")
        for quote in score.evidence:
            if not any(_normalise(quote) in source for source in sources):
                found.append(f"'{quote}' ({score.dimension}) is not a verbatim quote from {where}")
    return found


def scorecard_prompt(assets: Assets, design: Design, quotes_from: QuotesFrom) -> str:
    source = (
        "the user's own messages"
        if quotes_from == "user"
        else "the conversation (user or interviewer)"
    )
    return "\n\n".join(
        [
            assets.course_context.rstrip("\n"),
            "## Your task\n"
            "The user has confirmed all five steps. Score their performance on each of the five "
            "evaluation dimensions above, in this order: communication, structure, judgment, depth, "
            "time. Give each a score from 1 (weak) to 4 (strong), one or more pieces of evidence, "
            f"and one piece of advice. Every piece of evidence must be a verbatim quote from {source}, "
            "copied exactly.",
            "## Design record\n" + design_summary(design),
        ]
    )


def _transcript(messages: Sequence[BaseMessage]) -> str:
    lines = []
    for message in messages:
        role = (
            "User"
            if isinstance(message, HumanMessage)
            else "Interviewer"
            if isinstance(message, AIMessage)
            else None
        )
        if role and message.text.strip():
            lines.append(f"{role}: {message.text.strip()}")
    return "\n\n".join(lines)


async def make_scorecard(
    gateway: ModelGateway,
    meter: Meter,
    assets: Assets,
    design: Design,
    messages: Sequence[BaseMessage],
    config: RunnableConfig | None = None,
    quotes_from: QuotesFrom = QUOTES_FROM,
) -> Scorecard:
    prompt: list[BaseMessage] = [
        SystemMessage(scorecard_prompt(assets, design, quotes_from)),
        HumanMessage("Conversation:\n\n" + _transcript(messages)),
    ]
    issues: list[str] = []
    for _attempt in range(2):
        try:
            draft = await gateway.structured(meter, "interview", ScorecardDraft, prompt, config)
        except (InvalidStructuredOutput, ValidationError) as exc:
            issues = [str(exc)]
        else:
            issues = problems(draft, messages, quotes_from)
            if not issues:
                order = {name: index for index, name in enumerate(DIMENSIONS)}
                return Scorecard(
                    dimensions=sorted(draft.dimensions, key=lambda d: order[d.dimension])
                )
        prompt = [
            *prompt,
            HumanMessage(
                "Your scorecard could not be used. Fix these and answer again:\n- "
                + "\n- ".join(issues)
            ),
        ]
    raise ScorecardError("; ".join(issues))
