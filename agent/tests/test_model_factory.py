"""T-01: every chat model comes from the one two-role factory (S1.6, MODEL-CONNECTION.md)."""

import ast
from pathlib import Path

from conftest import INTERVIEW_KEY, REVIEW_KEY
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

import blueprint
from blueprint.models import build_models
from blueprint.settings import load_settings

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


def test_no_module_imports_a_provider_sdk() -> None:
    for path in SOURCE.rglob("*.py"):
        offending = {n for n in _imports(path) if n.split(".")[0] in PROVIDER_MODULES}
        assert not offending, f"{path.name} imports {offending}"


def test_only_the_factory_builds_chat_models() -> None:
    builders = {
        path.name
        for path in SOURCE.rglob("*.py")
        if any("init_chat_model" in n or "chat_models" in n for n in _imports(path))
    }
    assert builders == {"models.py"}


def test_factory_builds_both_roles_from_their_own_variables(env: dict[str, str]) -> None:
    models = build_models(load_settings(env))
    expected = {
        "interview": ("https://interview.example/v1", "interview-model", INTERVIEW_KEY),
        "review": ("https://review.example/v1", "review-model", REVIEW_KEY),
    }
    for role, (url, name, key) in expected.items():
        model = models.for_role(role)  # type: ignore[arg-type]
        assert isinstance(model, ChatOpenAI)
        assert (model.openai_api_base, model.model_name) == (url, name)
        assert isinstance(model.openai_api_key, SecretStr)
        assert model.openai_api_key.get_secret_value() == key
