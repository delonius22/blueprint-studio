"""Entry point: ``python -m blueprint`` starts the agent service or refuses, naming why."""

import asyncio
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from blueprint.app import apply_tracing, assemble, assemble_from, prepare
from blueprint.config.errors import StartupError
from blueprint.config.settings import Settings
from blueprint.storage.sqlite import open_sqlite, sqlite_path
from blueprint.utils import log


async def _listen(app: FastAPI, settings: Settings) -> None:
    server = uvicorn.Server(
        uvicorn.Config(app, host=settings.host, port=settings.port, log_config=None)
    )
    await server.serve()


async def serve() -> None:
    log.configure(secrets=())
    log.log_event("startup", message="checking configuration, app-assets and both models")
    runtime = await prepare(os.environ)
    settings = runtime.settings
    log.configure(
        secrets=(
            settings.interview.api_key.get_secret_value(),
            settings.review.api_key.get_secret_value(),
            settings.database_url.get_secret_value(),
        )
    )
    apply_tracing(settings, os.environ)
    check = "skipped" if settings.skip_model_check else "passed for both roles"
    log.log_event("startup", message=f"startup model check {check}")
    log.log_event("startup", message=f"review_model_distinct={runtime.review_model_distinct}")
    database_url = settings.database_url.get_secret_value()
    path = sqlite_path(database_url)
    if path is not None:
        log.log_event("startup", message=f"local mode: SQLite database {Path(path).resolve()}")
        async with open_sqlite(path) as (checkpointer, store):
            await _listen(assemble_from(runtime, checkpointer, store), settings)
        return
    async with AsyncConnectionPool(
        database_url,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    ) as pool:
        await _listen(await assemble(runtime, pool), settings)


def main() -> None:
    try:
        asyncio.run(serve())
    except StartupError as exc:
        log.log_event("startup_refused", level=40, message=f"refusing to start: {exc}")
        print(f"blueprint: refusing to start: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
