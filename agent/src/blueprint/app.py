"""Startup and the FastAPI application (SPECS S1.4, S1.7, S1.8, S4.1, S12.2)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI
from langgraph.graph.state import CompiledStateGraph

from blueprint.assets import Assets, load_assets
from blueprint.capability import check_models
from blueprint.models import RoleModels, build_models, review_model_distinct
from blueprint.settings import Settings, load_settings

AGENT_NAME = "blueprint"


@dataclass(frozen=True)
class Runtime:
    """Everything the agent resolves once at startup."""

    settings: Settings
    assets: Assets
    models: RoleModels
    review_model_distinct: bool


async def prepare(
    environ: Mapping[str, str],
    *,
    assets_root: Traversable | Path | None = None,
    build: Callable[[Settings], RoleModels] = build_models,
) -> Runtime:
    """Resolve settings, assets and models, refusing to start on the first problem."""
    settings = load_settings(environ)
    assets = load_assets(assets_root)
    models = build(settings)
    if not settings.skip_model_check:
        await check_models(models, settings)
    return Runtime(settings, assets, models, review_model_distinct(settings))


def create_app(graph: CompiledStateGraph[Any, Any, Any, Any]) -> FastAPI:
    app = FastAPI(title="Blueprint Studio agent", version="0.1.0")
    agent = LangGraphAGUIAgent(
        name=AGENT_NAME,
        description="Blueprint Studio system-design interviewer",
        graph=graph,
    )
    add_langgraph_fastapi_endpoint(app, agent, "/agent")
    return app
