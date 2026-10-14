"""The one factory for chat models (SPECS S1.6, S1.8 as overridden by MODEL-CONNECTION.md).

Every chat model in the app is built here, for one of two roles, through
LangChain's ``init_chat_model`` speaking the OpenAI-compatible Chat Completions
protocol. No other module creates a model or imports a provider SDK.
"""

from dataclasses import dataclass

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from blueprint.settings import Role, RoleConfig, Settings

ROLES: tuple[Role, ...] = ("interview", "review")


@dataclass(frozen=True)
class RoleModels:
    interview: BaseChatModel
    review: BaseChatModel

    def for_role(self, role: Role) -> BaseChatModel:
        return self.interview if role == "interview" else self.review


def build_chat_model(config: RoleConfig) -> BaseChatModel:
    model = init_chat_model(
        config.model_name,
        model_provider="openai",
        base_url=config.base_url,
        # A keyless local server still needs a non-empty bearer value.
        api_key=config.api_key.get_secret_value() or "not-needed",
        stream_usage=True,
    )
    assert isinstance(model, BaseChatModel)
    return model


def build_models(settings: Settings) -> RoleModels:
    return RoleModels(
        interview=build_chat_model(settings.interview),
        review=build_chat_model(settings.review),
    )


def _identity(config: RoleConfig) -> tuple[str, str]:
    return (config.base_url.rstrip("/"), config.model_name)


def review_model_distinct(settings: Settings) -> bool:
    """True when the review model's (base URL, model name) differs from the interview model's."""
    return _identity(settings.review) != _identity(settings.interview)
