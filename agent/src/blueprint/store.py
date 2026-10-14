"""The ``sessions`` table: name, stage and timestamps for listing (PRD D10, SPECS S3.2).

Graph state lives in the LangGraph checkpointer under thread ID = session ID
(S4.2); this table only holds what the session list needs.
"""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg_pool import AsyncConnectionPool

SCHEMA = (
    """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    stage TEXT NOT NULL,
    current_step INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
""",
    "CREATE INDEX IF NOT EXISTS sessions_updated_at_id ON sessions (updated_at DESC, id DESC)",
)

COLUMNS = "id, name, stage, current_step, created_at, updated_at"


class InvalidCursor(ValueError):
    pass


@dataclass(frozen=True)
class SessionRow:
    id: str
    name: str
    stage: str
    current_step: int
    created_at: datetime
    updated_at: datetime


def encode_cursor(row: SessionRow) -> str:
    raw = json.dumps([row.updated_at.isoformat(), row.id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        updated_at, session_id = json.loads(raw)
        return datetime.fromisoformat(updated_at), str(session_id)
    except (ValueError, TypeError) as exc:
        raise InvalidCursor("cursor is not valid") from exc


def _row(record: dict[str, Any]) -> SessionRow:
    return SessionRow(**record)


class SessionStore:
    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self.pool = pool

    async def setup(self) -> None:
        async with self.pool.connection() as conn:
            for statement in SCHEMA:
                await conn.execute(statement)

    async def create(self, session_id: str, name: str, stage: str, current_step: int) -> SessionRow:
        async with self.pool.connection() as conn:
            cursor = await conn.execute(
                f"INSERT INTO sessions (id, name, stage, current_step) VALUES (%s, %s, %s, %s) "
                f"RETURNING {COLUMNS}",
                (session_id, name, stage, current_step),
            )
            return _row(await cursor.fetchone())

    async def get(self, session_id: str) -> SessionRow | None:
        async with self.pool.connection() as conn:
            cursor = await conn.execute(
                f"SELECT {COLUMNS} FROM sessions WHERE id = %s", (session_id,)
            )
            record = await cursor.fetchone()
            return _row(record) if record else None

    async def page(self, limit: int, cursor: str | None) -> tuple[list[SessionRow], str | None]:
        """Sessions by updated_at descending (ties by id), keyset-paginated."""
        query = f"SELECT {COLUMNS} FROM sessions"
        params: list[Any] = []
        if cursor is not None:
            updated_at, session_id = decode_cursor(cursor)
            query += " WHERE (updated_at, id) < (%s, %s)"
            params += [updated_at, session_id]
        query += " ORDER BY updated_at DESC, id DESC LIMIT %s"
        params.append(limit + 1)
        async with self.pool.connection() as conn:
            rows = [_row(r) for r in await (await conn.execute(query, params)).fetchall()]
        if len(rows) > limit:
            return rows[:limit], encode_cursor(rows[limit - 1])
        return rows, None

    async def rename(self, session_id: str, name: str) -> SessionRow | None:
        async with self.pool.connection() as conn:
            cursor = await conn.execute(
                f"UPDATE sessions SET name = %s, updated_at = now() WHERE id = %s "
                f"RETURNING {COLUMNS}",
                (name, session_id),
            )
            record = await cursor.fetchone()
            return _row(record) if record else None

    async def record_progress(self, session_id: str, stage: str, current_step: int) -> None:
        """Called after each agent run so the list shows the stage and recent activity."""
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE sessions SET stage = %s, current_step = %s, updated_at = now() "
                "WHERE id = %s",
                (stage, current_step, session_id),
            )

    async def delete(self, session_id: str) -> None:
        async with self.pool.connection() as conn:
            await conn.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
