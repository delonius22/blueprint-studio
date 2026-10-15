"""T-01: one .env configures the stack; .env.example documents it (S1.2, S1.3, S1.5)."""

import re

from conftest import REPO_ROOT

VARIABLES = [
    "MODEL_BASE_URL",
    "MODEL_API_KEY",
    "MODEL_NAME",
    "REVIEW_MODEL_BASE_URL",
    "REVIEW_MODEL_API_KEY",
    "REVIEW_MODEL_NAME",
    "DATABASE_URL",
    "AGENT_URL",
    "SESSION_TOKEN_BUDGET",
    "LANGSMITH_TRACING",
    "SKIP_MODEL_CHECK",
    "HOST",
    "PORT",
]


def _assignments(text: str, *, commented: bool) -> dict[str, str]:
    prefix = r"#\s*" if commented else ""
    return dict(re.findall(rf"^{prefix}([A-Z_]+)=(.*)$", text, flags=re.MULTILINE))


def test_env_example_documents_every_variable_with_both_blocks() -> None:
    text = (REPO_ROOT / ".env.example").read_text()
    active = _assignments(text, commented=False)
    assert sorted(active) == sorted(VARIABLES)
    anthropic = _assignments(text, commented=True)
    for role in ("MODEL", "REVIEW_MODEL"):
        assert active[f"{role}_BASE_URL"].startswith("https://")
        assert anthropic[f"{role}_BASE_URL"] == "https://api.anthropic.com/v1/"
        assert {f"{role}_API_KEY", f"{role}_NAME"} <= anthropic.keys()
    for name, value in active.items():
        if name.endswith("_API_KEY"):
            assert value.startswith("<"), f"{name} must be a placeholder"


def test_compose_starts_three_services_and_keeps_keys_out_of_web() -> None:
    text = (REPO_ROOT / "docker-compose.yml").read_text()
    services = re.search(r"^services:\n(.*?)^volumes:", text, flags=re.MULTILINE | re.DOTALL)
    assert services is not None
    names = re.findall(r"^  ([a-z]+):$", services.group(1), flags=re.MULTILINE)
    assert names == ["db", "agent", "web"]
    web = services.group(1).split("\n  web:\n", 1)[1]
    assert "env_file" not in web
    assert "API_KEY" not in web
    agent = services.group(1).split("\n  agent:\n", 1)[1].split("\n  web:\n", 1)[0]
    assert "- path: .env" in agent
