"""Entry point: ``python -m blueprint`` starts the agent service or refuses, naming why."""

import asyncio
import os
import sys

import uvicorn
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from blueprint.app import create_app, prepare
from blueprint.errors import StartupError
from blueprint.graph import build_graph


async def serve() -> None:
    print("blueprint: starting; checking configuration, app-assets and both models", flush=True)
    runtime = await prepare(os.environ)
    settings = runtime.settings
    check = "skipped" if settings.skip_model_check else "passed for both roles"
    print(f"blueprint: startup model check {check}", flush=True)
    print(f"blueprint: review_model_distinct={runtime.review_model_distinct}", flush=True)
    async with AsyncConnectionPool(
        settings.database_url.get_secret_value(),
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
        await checkpointer.setup()
        app = create_app(build_graph(runtime.models, checkpointer))
        server = uvicorn.Server(uvicorn.Config(app, host=settings.host, port=settings.port))
        await server.serve()


def main() -> None:
    try:
        asyncio.run(serve())
    except StartupError as exc:
        print(f"blueprint: refusing to start: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
