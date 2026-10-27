"""T-01: every model client comes from the one two-role factory (S1.6, MODEL-CONNECTION.md)."""

import ast
from pathlib import Path

import openai
from conftest import INTERVIEW_KEY, REVIEW_KEY

import blueprint
from blueprint.config.settings import load_settings
from blueprint.llm.clients import build_models

PROVIDER_MODULES = ("openai", "anthropic", "langchain_openai", "langchain_anthropic")
SOURCE = Path(blueprint.__file__).parent


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_only_the_factory_imports_a_provider_sdk() -> None:
    importers = {
        path.relative_to(SOURCE).as_posix()
        for path in SOURCE.rglob("*.py")
        if any(n.split(".")[0] in PROVIDER_MODULES for n in _imports(path))
    }
    assert importers == {"llm/clients.py"}


def test_factory_builds_both_roles_from_their_own_variables(env: dict[str, str]) -> None:
    models = build_models(load_settings(env))
    expected = {
        "interview": ("https://interview.example/v1", "interview-model", INTERVIEW_KEY),
        "review": ("https://review.example/v1", "review-model", REVIEW_KEY),
    }
    for role, (url, name, key) in expected.items():
        model = models.for_role(role)  # type: ignore[arg-type]
        assert isinstance(model.client, openai.AsyncOpenAI)
        assert (str(model.client.base_url).rstrip("/"), model.model) == (url, name)
        assert model.client.api_key == key
        assert (model.client.max_retries, model.client.timeout) == (0, 120.0)  # S13.1 retries
