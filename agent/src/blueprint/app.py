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
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import AsyncConnectionPool

from blueprint.api import AGENT_NAME, SessionAgent, install_error_handlers, session_routes
from blueprint.assets import Assets, load_assets
from blueprint.capability import check_models
from blueprint.graph import build_graph
from blueprint.log import log_event
from blueprint.models import RoleModels, build_models, review_model_distinct
from blueprint.openapi import TITLE, VERSION
from blueprint.settings import Settings, load_settings
from blueprint.store import SessionStore


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
    graph: CompiledStateGraph[Any, Any, Any, Any], store: SessionStore | None = None
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

        agent.exists, agent.after_run = exists, after_run
    add_langgraph_fastapi_endpoint(app, agent, "/agent", include_in_schema=False)
    return app


async def assemble(runtime: Runtime, pool: AsyncConnectionPool[Any]) -> FastAPI:
    """The full service: Postgres checkpoints (S4.2), the session API (S3) and /agent (S4.1)."""
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    store = SessionStore(pool)
    await store.setup()
    graph = build_graph(runtime.models, checkpointer, runtime.assets)
    app = create_app(graph, store)
    app.include_router(
        session_routes(
            store,
            graph,
            checkpointer,
            runtime.settings.session_token_budget,
            runtime.review_model_distinct,
        )
    )
    return app
