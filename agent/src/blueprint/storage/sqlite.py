"""Local mode: sessions and graph checkpoints in one SQLite file, with no database server.

Selected by a ``DATABASE_URL`` of the form ``sqlite:///<path>``; a relative path is taken
from the agent's working directory. Server mode (Docker Compose) uses Postgres instead.
"""

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from blueprint.storage.sessions import SqlSessionStore

SQLITE_PREFIX = "sqlite:///"

# Fixed width with microseconds, so text order is time order (the list sorts on it).
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def sqlite_path(database_url: str) -> str | None:
    """The file named by a ``sqlite:///<path>`` URL, or None for any other URL."""
    if not database_url.startswith(SQLITE_PREFIX):
        return None
    return database_url.removeprefix(SQLITE_PREFIX)


class SqliteDatabase:
    """The store's tables in SQLite, on their own autocommit connection."""

    time_type = "TEXT"
    blob_type = "BLOB"

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        self.lock = asyncio.Lock()  # one statement at a time on the shared connection

    async def rows(self, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        async with self.lock, self.conn.execute(query, tuple(params)) as cursor:
            return [tuple(record) for record in await cursor.fetchall()]

    def stamp(self, moment: datetime) -> str:
        return moment.astimezone(UTC).strftime(TIME_FORMAT)

    def moment(self, value: Any) -> datetime:
        return datetime.strptime(value, TIME_FORMAT).replace(tzinfo=UTC)


@asynccontextmanager
async def open_sqlite(path: str) -> AsyncIterator[tuple[AsyncSqliteSaver, SqlSessionStore]]:
    """The checkpointer and the session store over one SQLite file, both set up."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with (
        aiosqlite.connect(path, isolation_level=None) as store_conn,
        aiosqlite.connect(path) as checkpoint_conn,
    ):
        await store_conn.execute("PRAGMA journal_mode=WAL")  # readers never block the writer
        for conn in (store_conn, checkpoint_conn):
            await conn.execute("PRAGMA busy_timeout=5000")
        checkpointer = AsyncSqliteSaver(checkpoint_conn)
        await checkpointer.setup()
        store = SqlSessionStore(SqliteDatabase(store_conn))
        await store.setup()
        yield checkpointer, store
