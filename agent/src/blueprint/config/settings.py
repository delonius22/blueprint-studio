"""Configuration from the environment (SPECS S1.3, S1.4 as overridden by MODEL-CONNECTION.md).

Each model role is configured by exactly three variables: a base URL, an API key
and a model name. Keys are held as ``SecretStr`` so a settings object never
prints them (S1.5).
"""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, SecretStr

from blueprint.config.errors import StartupError

Role = Literal["interview", "review"]

_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


class ConfigError(StartupError):
    """A required variable is missing or a variable cannot be parsed."""


class RoleConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str
    api_key: SecretStr
    model_name: str


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    interview: RoleConfig
    review: RoleConfig
    database_url: SecretStr
    session_token_budget: int = 2_000_000
    langsmith_tracing: bool = False
    skip_model_check: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    def role(self, role: Role) -> RoleConfig:
        return self.interview if role == "interview" else self.review


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required but is not set")
    return value


def _integer(
    environ: Mapping[str, str], name: str, default: int, minimum: int, maximum: int
) -> int:
    raw = environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from None
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


def _boolean(environ: Mapping[str, str], name: str, default: bool) -> bool:
    raw = environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise ConfigError(f"{name} must be true or false, got {raw!r}")


DATABASE_SCHEMES = ("postgresql://", "postgres://", "sqlite:///")


def _database_url(environ: Mapping[str, str]) -> str:
    """Postgres for the server (Docker Compose), a SQLite file for local runs."""
    url = _required(environ, "DATABASE_URL")
    if not url.startswith(DATABASE_SCHEMES):
        # Never echo the URL: it may hold a password.
        raise ConfigError(
            "DATABASE_URL must start with postgresql:// (server) or sqlite:/// (local)"
        )
    return url


def _role(environ: Mapping[str, str], prefix: str) -> RoleConfig:
    return RoleConfig(
        base_url=_required(environ, f"{prefix}_BASE_URL"),
        api_key=SecretStr(environ.get(f"{prefix}_API_KEY", "").strip()),
        model_name=_required(environ, f"{prefix}_NAME"),
    )


def load_settings(environ: Mapping[str, str]) -> Settings:
    """Read and validate every agent variable, naming the first one that is wrong."""
    return Settings(
        interview=_role(environ, "MODEL"),
        review=_role(environ, "REVIEW_MODEL"),
        database_url=SecretStr(_database_url(environ)),
        session_token_budget=_integer(environ, "SESSION_TOKEN_BUDGET", 2_000_000, 1, 10**12),
        langsmith_tracing=_boolean(environ, "LANGSMITH_TRACING", False),
        skip_model_check=_boolean(environ, "SKIP_MODEL_CHECK", False),
        host=environ.get("HOST", "").strip() or "0.0.0.0",
        port=_integer(environ, "PORT", 8000, 1, 65535),
    )
