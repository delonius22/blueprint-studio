"""Moving Pydantic models in and out of graph state, which holds plain JSON (SPECS S2.1)."""

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel


def dump(items: Iterable[BaseModel]) -> list[dict[str, Any]]:
    """Models as the JSON values state stores."""
    return [item.model_dump(mode="json") for item in items]


def load[M: BaseModel](model: type[M], state: Mapping[str, Any], key: str) -> list[M]:
    """A state list as models; a missing or empty field is an empty list."""
    return [model.model_validate(value) for value in state.get(key) or []]
