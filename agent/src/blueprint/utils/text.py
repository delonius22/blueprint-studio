"""Text formatting shared by prompts, chat messages and documents."""

from collections.abc import Sequence

from langchain_core.messages import BaseMessage

ROLES = {"human": "User", "ai": "Interviewer"}


def transcript(messages: Sequence[BaseMessage]) -> str:
    """The conversation as plain text: user and interviewer turns only, tool traffic left out."""
    lines = [
        f"{ROLES[m.type]}: {m.text.strip()}" for m in messages if m.type in ROLES and m.text.strip()
    ]
    return "\n\n".join(lines) or "(no conversation yet)"


def number(value: float | None) -> str:
    """A number as people write it: ``50`` not ``50.0``; empty for None."""
    return "" if value is None else f"{value:g}"


def plural(count: int, noun: str, many: str | None = None) -> str:
    """``1 gap``, ``3 gaps``; ``many`` for an irregular plural."""
    return f"{count} {noun if count == 1 else many or noun + 's'}"
