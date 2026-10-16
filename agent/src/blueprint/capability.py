"""Startup capability check for both model roles (SPECS S1.7, MODEL-CONNECTION.md).

Each role's model must make one trivial tool call and return one trivial
structured output. Structured output asks for JSON-schema mode first and falls
back once to tool calling (S13.4).
"""

import asyncio

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from blueprint.errors import StartupError
from blueprint.models import (
    ROLES,
    STRUCTURED_METHODS,
    ChatModel,
    RoleModels,
    complete,
    structured_request,
    structured_value,
)
from blueprint.settings import Role, RoleConfig, Settings


class CapabilityError(StartupError):
    """A role's model cannot call tools or return structured output."""


class Ping(BaseModel):
    """Answer a ping from Blueprint Studio's startup check."""

    message: str = Field(description="Always the word 'pong'.")


class PingResult(BaseModel):
    ok: bool = Field(description="Always true.")


# Per model call, so an unreachable endpoint refuses instead of hanging at startup.
CALL_TIMEOUT_S = 60.0

TOOL_PROMPT = "Call the Ping tool once with message 'pong'. Do not reply with text."
STRUCTURED_PROMPT = "Reply with ok set to true."


def _refusal(role: Role, capability: str, config: RoleConfig, reason: str) -> CapabilityError:
    return CapabilityError(
        f"the {role} model failed the {capability} check "
        f"(base URL {config.base_url}, model {config.model_name}): {reason}"
    )


def _failure(exc: Exception, timeout_s: float) -> str:
    if isinstance(exc, TimeoutError):
        return f"no answer within {timeout_s:g} s"
    return f"{type(exc).__name__}: {exc}"


async def _check_tool_calling(model: ChatModel, timeout_s: float) -> str | None:
    try:
        async with asyncio.timeout(timeout_s):
            response = await complete(model, [HumanMessage(TOOL_PROMPT)], [Ping])
    except Exception as exc:
        return _failure(exc, timeout_s)
    if not any(call["name"] == "Ping" for call in response.tool_calls):
        return "the model answered without calling the tool"
    return None


async def _check_structured_output(model: ChatModel, timeout_s: float) -> str | None:
    reasons: list[str] = []
    for method in STRUCTURED_METHODS:
        try:
            async with asyncio.timeout(timeout_s):
                response = await complete(
                    model,
                    [HumanMessage(STRUCTURED_PROMPT)],
                    **structured_request(PingResult, method),
                )
        except Exception as exc:
            reasons.append(f"{method}: {_failure(exc, timeout_s)}")
            continue
        try:
            structured_value(PingResult, response, method)
        except ValueError:
            reasons.append(f"{method}: the answer did not match the schema")
            continue
        return None
    return "; ".join(reasons)


async def _check_role(role: Role, model: ChatModel, config: RoleConfig, timeout_s: float) -> None:
    reason = await _check_tool_calling(model, timeout_s)
    if reason is not None:
        raise _refusal(role, "tool-calling", config, reason)
    reason = await _check_structured_output(model, timeout_s)
    if reason is not None:
        raise _refusal(role, "structured-output", config, reason)


async def check_models(
    models: RoleModels, settings: Settings, timeout_s: float = CALL_TIMEOUT_S
) -> None:
    """Check both roles; raise naming the first role (interview, then review) that fails."""
    results = await asyncio.gather(
        *(
            _check_role(role, models.for_role(role), settings.role(role), timeout_s)
            for role in ROLES
        ),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, BaseException):
            raise result
