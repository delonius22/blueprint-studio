"""T-01: the agent refuses to start, naming what is wrong (S1.4, S1.7, S1.8, S12.2)."""

import asyncio
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import httpx2
import pytest
from conftest import APP_ASSETS, INTERVIEW_KEY, REVIEW_KEY, valid_env
from fakes import ScriptedChatModel, tool_call

from blueprint.app import prepare
from blueprint.assets import ASSET_FILES, AssetError
from blueprint.capability import CapabilityError, check_models
from blueprint.models import RoleModels
from blueprint.settings import ConfigError, Settings, load_settings

REQUIRED = [
    "MODEL_BASE_URL",
    "MODEL_NAME",
    "REVIEW_MODEL_BASE_URL",
    "REVIEW_MODEL_NAME",
    "DATABASE_URL",
]
PARSED = ["SESSION_TOKEN_BUDGET", "PORT", "LANGSMITH_TRACING", "SKIP_MODEL_CHECK"]


# --- S1.4 (as overridden by MODEL-CONNECTION.md) -------------------------------------------


@pytest.mark.parametrize("name", REQUIRED)
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_required_variable_is_named(
    env: dict[str, str], name: str, value: str | None
) -> None:
    if value is None:
        del env[name]
    else:
        env[name] = value
    with pytest.raises(ConfigError, match=name):
        load_settings(env)


@pytest.mark.parametrize("name", PARSED)
def test_unparseable_variable_is_named(env: dict[str, str], name: str) -> None:
    env[name] = "not-a-value"
    with pytest.raises(ConfigError, match=name):
        load_settings(env)


def test_defaults_and_blank_keys(env: dict[str, str]) -> None:
    env["MODEL_API_KEY"] = ""
    del env["REVIEW_MODEL_API_KEY"]
    del env["SKIP_MODEL_CHECK"]
    settings = load_settings(env)
    assert settings.session_token_budget == 2_000_000
    assert (settings.langsmith_tracing, settings.skip_model_check) == (False, False)
    assert (settings.host, settings.port) == ("0.0.0.0", 8000)
    assert settings.interview.api_key.get_secret_value() == ""


def test_settings_never_print_keys(env: dict[str, str]) -> None:
    settings = load_settings(env)
    for text in (repr(settings), str(settings), settings.model_dump_json()):
        assert INTERVIEW_KEY not in text
        assert REVIEW_KEY not in text


def test_process_exits_naming_the_variable() -> None:
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("MODEL_", "REVIEW_"))}
    environment |= valid_env()
    del environment["REVIEW_MODEL_NAME"]
    result = subprocess.run(
        [sys.executable, "-m", "blueprint"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1
    assert "refusing to start" in result.stderr
    assert "REVIEW_MODEL_NAME" in result.stderr


# --- S12.1, S12.2 ----------------------------------------------------------------------------


def test_packaged_assets_are_verbatim_copies_of_the_repository() -> None:
    packaged = files("blueprint") / "app_assets"
    for name in ASSET_FILES:
        assert (packaged / name).read_bytes() == (APP_ASSETS / name).read_bytes(), name
    assert sorted(p.name for p in APP_ASSETS.iterdir()) == sorted(ASSET_FILES)


@pytest.mark.parametrize("name", ASSET_FILES)
async def test_missing_asset_is_named(env: dict[str, str], tmp_path: Path, name: str) -> None:
    _copy_assets(tmp_path, skip=name)
    with pytest.raises(AssetError, match=f"{name} is missing"):
        await prepare(env, assets_root=tmp_path)


@pytest.mark.parametrize("name", ASSET_FILES)
async def test_empty_asset_is_named(env: dict[str, str], tmp_path: Path, name: str) -> None:
    _copy_assets(tmp_path)
    (tmp_path / name).write_text("  \n")
    with pytest.raises(AssetError, match=f"{name} is empty"):
        await prepare(env, assets_root=tmp_path)


async def test_prepare_loads_assets(env: dict[str, str]) -> None:
    runtime = await prepare(env)
    assert runtime.assets.to_spec == (APP_ASSETS / "to-spec.md").read_text()
    assert runtime.assets.design_judge_merge == (APP_ASSETS / "design-judge-merge.md").read_text()


def _copy_assets(target: Path, skip: str | None = None) -> None:
    for name in ASSET_FILES:
        if name != skip:
            (target / name).write_bytes((APP_ASSETS / name).read_bytes())


# --- S1.7 startup capability check ---------------------------------------------------------


def _healthy(name: str) -> ScriptedChatModel:
    return ScriptedChatModel.with_script(
        tool_call("Ping", {"message": "pong"}), {"ok": True}, name=name
    )


def _builder(interview: ScriptedChatModel, review: ScriptedChatModel):  # type: ignore[no-untyped-def]
    def build(_: Settings) -> RoleModels:
        return RoleModels(interview=interview, review=review)

    return build


async def test_check_runs_for_both_roles(env: dict[str, str]) -> None:
    env["SKIP_MODEL_CHECK"] = "false"
    interview, review = _healthy("interview"), _healthy("review")
    await prepare(env, build=_builder(interview, review))
    for model in (interview, review):
        assert model.remaining == 0
        assert model.calls[0].tools == ["Ping"]
        assert model.calls[1].structured_method == "json_schema"


async def test_structured_output_falls_back_to_tool_calling(env: dict[str, str]) -> None:
    env["SKIP_MODEL_CHECK"] = "false"
    review = ScriptedChatModel.with_script(
        tool_call("Ping", {"message": "pong"}), ValueError("json_schema unsupported"), {"ok": True}
    )
    await prepare(env, build=_builder(_healthy("interview"), review))
    assert [c.structured_method for c in review.calls[1:]] == ["json_schema", "function_calling"]


@pytest.mark.parametrize(
    ("role", "capability", "script"),
    [
        ("interview", "tool-calling", [ValueError("tools not supported")]),
        ("review", "tool-calling", [tool_call("Other", {})]),
        (
            "review",
            "structured-output",
            [tool_call("Ping", {}), ValueError("no"), ValueError("no")],
        ),
    ],
)
async def test_failed_check_names_role_capability_base_url_and_model(
    env: dict[str, str], role: str, capability: str, script: list[object]
) -> None:
    env["SKIP_MODEL_CHECK"] = "false"
    broken = ScriptedChatModel.with_script(*script)  # type: ignore[arg-type]
    models = (
        (broken, _healthy("review")) if role == "interview" else (_healthy("interview"), broken)
    )
    with pytest.raises(CapabilityError) as caught:
        await prepare(env, build=_builder(*models))
    message = str(caught.value)
    prefix = "MODEL" if role == "interview" else "REVIEW_MODEL"
    assert f"the {role} model failed the {capability} check" in message
    assert env[f"{prefix}_BASE_URL"] in message
    assert env[f"{prefix}_NAME"] in message


class HangingModel(ScriptedChatModel):
    async def _handle(self, request: httpx2.Request) -> httpx2.Response:
        await asyncio.sleep(30)
        raise AssertionError("unreachable")


async def test_unresponsive_model_is_refused_within_the_time_limit(env: dict[str, str]) -> None:
    settings = load_settings(env)
    models = RoleModels(interview=_healthy("interview"), review=HangingModel())
    with pytest.raises(CapabilityError) as caught:
        await check_models(models, settings, timeout_s=0.2)
    message = str(caught.value)
    assert "the review model failed the tool-calling check" in message
    assert "no answer within 0.2 s" in message
    assert env["REVIEW_MODEL_BASE_URL"] in message


async def test_skip_model_check_makes_no_model_calls(env: dict[str, str]) -> None:
    interview, review = ScriptedChatModel.with_script(), ScriptedChatModel.with_script()
    await prepare(env, build=_builder(interview, review))
    assert interview.calls == [] and review.calls == []


# --- S1.8 review_model_distinct ------------------------------------------------------------


@pytest.mark.parametrize(
    ("review_url", "review_name", "distinct"),
    [
        ("https://interview.example/v1", "interview-model", False),
        ("https://interview.example/v1/", "interview-model", False),
        ("https://interview.example/v1", "other-model", True),
        ("https://review.example/v1", "interview-model", True),
    ],
)
async def test_review_model_distinct(
    env: dict[str, str], review_url: str, review_name: str, distinct: bool
) -> None:
    env["REVIEW_MODEL_BASE_URL"], env["REVIEW_MODEL_NAME"] = review_url, review_name
    runtime = await prepare(env)
    assert runtime.review_model_distinct is distinct
