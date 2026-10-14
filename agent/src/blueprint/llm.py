"""Model calls shared by the graph's nodes.

Structured output asks for JSON-schema mode first and falls back to tool
calling (SPECS S13.4, MODEL-CONNECTION.md).
"""

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

STRUCTURED_METHODS = ("json_schema", "function_calling")


async def structured[T: BaseModel](
    model: BaseChatModel,
    schema: type[T],
    messages: Sequence[BaseMessage],
    config: RunnableConfig | None = None,
) -> T:
    """One structured-output call, returning a validated ``schema`` instance."""
    last_error: Exception | None = None
    for method in STRUCTURED_METHODS:
        try:
            result: Any = await model.with_structured_output(schema, method=method).ainvoke(
                list(messages), config
            )
        except Exception as exc:
            last_error = exc
            continue
        return schema.model_validate(result)
    assert last_error is not None
    raise last_error
