"""Startup and the FastAPI application (SPECS S1.4, S1.7, S1.8, S4.1, S12.2)."""

import re
import time
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import AsyncConnectionPool

from blueprint.api.agent import AGENT_NAME, SessionAgent
from blueprint.api.openapi import TITLE, VERSION
from blueprint.api.routes import install_error_handlers, session_routes
from blueprint.config.assets import Assets, load_assets
from blueprint.config.settings import Settings, load_settings
from blueprint.graph.build import build_graph
from blueprint.llm.capability import check_models, check_vision
from blueprint.llm.clients import RoleModels, build_models, review_model_distinct
from blueprint.storage.sessions import PostgresDatabase, SqlSessionStore
from blueprint.utils.log import log_event


@dataclass(frozen=True)
class Runtime:
    """Everything the agent resolves once at startup."""

    settings: Settings
    assets: Assets
    models: RoleModels
    review_model_distinct: bool
    vision_supported: bool = False


async def prepare(
    environ: Mapping[str, str],
    *,
    assets_root: Traversable | Path | None = None,
    build: Callable[[Settings], RoleModels] = build_models,
    vision: bool | None = None,
) -> Runtime:
    """Resolve settings, assets and models, refusing to start on the first problem.

    ``vision`` overrides the image probe (tests); otherwise the probe runs with the model check.
    """
    settings = load_settings(environ)
    assets = load_assets(assets_root)
    models = build(settings)
    if not settings.skip_model_check:
        await check_models(models, settings)
    if vision is None:
        vision = not settings.skip_model_check and await check_vision(models.interview)
        if not vision:
            log_event("vision_unavailable", model=settings.interview.model_name)
    return Runtime(settings, assets, models, review_model_distinct(settings), vision)


def apply_tracing(settings: Settings, environ: MutableMapping[str, str]) -> None:
    """S13.5: LANGSMITH_TRACING switches LangSmith tracing through LangChain's own variable."""
    environ["LANGSMITH_TRACING"] = "true" if settings.langsmith_tracing else "false"


DOWNLOAD_PATH = re.compile(r"^/api/sessions/(?P<session>[^/]+)/downloads/(?P<kind>[^/]+)$")


class DownloadTimer:
    """Logs ``export_ms`` for every download request (S13.5, NFR-2); other paths pass through."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        match = DOWNLOAD_PATH.match(scope.get("path", "")) if scope["type"] == "http" else None
        if match is None:
            await self.app(scope, receive, send)
            return
        start = time.monotonic()
        status: dict[str, int] = {}

        async def record(message: Any) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, record)
        finally:
            log_event(
                "download",
                session_id=match["session"],
                kind=match["kind"],
                status=status.get("code"),
                export_ms=round((time.monotonic() - start) * 1000),
            )


def create_app(
    graph: CompiledStateGraph[Any, Any, Any, Any], store: SqlSessionStore | None = None
) -> FastAPI:
    """The agent endpoint at /agent (S4.1); with a store, runs are limited to existing sessions."""
    app = FastAPI(title=TITLE, version=VERSION)
    app.add_middleware(DownloadTimer)
    install_error_handlers(app)
    agent = SessionAgent(
        name=AGENT_NAME,
        description="Blueprint Studio system-design interviewer",
        graph=graph,
    )
    if store is not None:
        sessions = store

        async def exists(session_id: str) -> bool:
            return await sessions.get(session_id) is not None

        async def after_run(session_id: str) -> None:
            values = (await graph.aget_state({"configurable": {"thread_id": session_id}})).values
            await sessions.record_progress(session_id, values["stage"], values["current_step"])

        agent.exists, agent.after_run, agent.attachments = exists, after_run, sessions.attachments
    add_langgraph_fastapi_endpoint(app, agent, "/agent", include_in_schema=False)
    return app


async def assemble(runtime: Runtime, pool: AsyncConnectionPool[Any]) -> FastAPI:
    """The full service over Postgres (server mode): checkpoints (S4.2), sessions (S3), /agent."""
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    store = SqlSessionStore(PostgresDatabase(pool))
    await store.setup()
    return assemble_from(runtime, checkpointer, store)


def assemble_from(
    runtime: Runtime, checkpointer: BaseCheckpointSaver[Any], store: SqlSessionStore
) -> FastAPI:
    """The full service over a checkpointer and a session store that are already set up."""
    graph = build_graph(runtime.models, checkpointer, runtime.assets, files=store)
    app = create_app(graph, store)
    app.state.graph = graph  # for operators' scripts and tests; the API never needs it
    app.include_router(
        session_routes(
            store,
            graph,
            checkpointer,
            runtime.settings.session_token_budget,
            runtime.review_model_distinct,
            runtime.vision_supported,
        )
    )
    return app
