"""Local mode: sessions and graph checkpoints in one SQLite file, with no database server.

Selected by a ``DATABASE_URL`` of the form ``sqlite:///<path>``; a relative path is taken
from the agent's working directory. Server mode (Docker Compose) uses Postgres instead.
"""

import asyncio
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from blueprint.store import COLUMNS, SessionRow, decode_cursor, split_page

SQLITE_PREFIX = "sqlite:///"

# Fixed width with microseconds, so text order is time order (the list sorts on it).
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

SCHEMA = (
    """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    stage TEXT NOT NULL,
    current_step INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
""",
    "CREATE INDEX IF NOT EXISTS sessions_updated_at_id ON sessions (updated_at DESC, id DESC)",
)


def sqlite_path(database_url: str) -> str | None:
    """The file named by a ``sqlite:///<path>`` URL, or None for any other URL."""
    if not database_url.startswith(SQLITE_PREFIX):
        return None
    return database_url.removeprefix(SQLITE_PREFIX)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(TIME_FORMAT)


def _row(record: Iterable[Any]) -> SessionRow:
    session_id, name, stage, current_step, created_at, updated_at = record
    return SessionRow(
        id=session_id,
        name=name,
        stage=stage,
        current_step=current_step,
        created_at=datetime.strptime(created_at, TIME_FORMAT).replace(tzinfo=UTC),
        updated_at=datetime.strptime(updated_at, TIME_FORMAT).replace(tzinfo=UTC),
    )


class SqliteSessionStore:
    """The ``sessions`` table in SQLite, on its own autocommit connection."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        self.lock = asyncio.Lock()  # one statement at a time on the shared connection

    async def _fetch(self, query: str, params: Iterable[Any] = ()) -> list[SessionRow]:
        async with self.lock, self.conn.execute(query, tuple(params)) as cursor:
            return [_row(record) for record in await cursor.fetchall()]

    async def setup(self) -> None:
        for statement in SCHEMA:
            await self._fetch(statement)

    async def create(self, session_id: str, name: str, stage: str, current_step: int) -> SessionRow:
        now = _stamp(datetime.now(UTC))
        (row,) = await self._fetch(
            f"INSERT INTO sessions ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?) RETURNING {COLUMNS}",
            (session_id, name, stage, current_step, now, now),
        )
        return row

    async def get(self, session_id: str) -> SessionRow | None:
        rows = await self._fetch(f"SELECT {COLUMNS} FROM sessions WHERE id = ?", (session_id,))
        return rows[0] if rows else None

    async def page(self, limit: int, cursor: str | None) -> tuple[list[SessionRow], str | None]:
        """Sessions by updated_at descending (ties by id), keyset-paginated."""
        query = f"SELECT {COLUMNS} FROM sessions"
        params: list[Any] = []
        if cursor is not None:
            updated_at, session_id = decode_cursor(cursor)
            query += " WHERE (updated_at, id) < (?, ?)"
            params += [_stamp(updated_at), session_id]
        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit + 1)
        return split_page(await self._fetch(query, params), limit)

    async def rename(self, session_id: str, name: str) -> SessionRow | None:
        rows = await self._fetch(
            f"UPDATE sessions SET name = ?, updated_at = ? WHERE id = ? RETURNING {COLUMNS}",
            (name, _stamp(datetime.now(UTC)), session_id),
        )
        return rows[0] if rows else None

    async def record_progress(self, session_id: str, stage: str, current_step: int) -> None:
        await self._fetch(
            "UPDATE sessions SET stage = ?, current_step = ?, updated_at = ? WHERE id = ?",
            (stage, current_step, _stamp(datetime.now(UTC)), session_id),
        )

    async def delete(self, session_id: str) -> None:
        await self._fetch("DELETE FROM sessions WHERE id = ?", (session_id,))


@asynccontextmanager
async def open_sqlite(path: str) -> AsyncIterator[tuple[AsyncSqliteSaver, SqliteSessionStore]]:
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
        store = SqliteSessionStore(store_conn)
        await store.setup()
        yield checkpointer, store
