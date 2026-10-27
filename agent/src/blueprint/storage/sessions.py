"""The ``sessions`` and ``attachments`` tables (PRD D10, SPECS S3.2, S14.3).

Graph state lives in the LangGraph checkpointer under thread ID = session ID (S4.2); the
sessions table only holds what the session list needs, and the attachments table holds
uploaded files, which never enter the checkpoint.

``SqlSessionStore`` writes every query once, with ``?`` placeholders, over a ``Database``
adapter: ``PostgresDatabase`` here (server mode) or ``storage.sqlite.SqliteDatabase``
(local mode). The adapters differ only in placeholders, column types and timestamps.
"""

import base64
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from psycopg.rows import tuple_row
from psycopg_pool import AsyncConnectionPool

from blueprint.domain.models import DocumentRole
from blueprint.imports.files import ParsedFile, Section

SCHEMA = (
    """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    stage TEXT NOT NULL,
    current_step INTEGER NOT NULL,
    created_at {time} NOT NULL,
    updated_at {time} NOT NULL
)
""",
    "CREATE INDEX IF NOT EXISTS sessions_updated_at_id ON sessions (updated_at DESC, id DESC)",
    """
CREATE TABLE IF NOT EXISTS attachments (
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    kind TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    warnings TEXT NOT NULL,
    sections TEXT NOT NULL,
    content {blob},
    removed BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (session_id, seq)
)
""",
)

COLUMNS = "id, name, stage, current_step, created_at, updated_at"
# Removed attachments keep their row (without content), so an ATT number is never reused.
ATTACHMENT_COLUMNS = "seq, name, role, kind, media_type, size, sha256, warnings"


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


@dataclass(frozen=True)
class AttachmentRow:
    """An uploaded file as the attachment listing shows it."""

    id: str
    name: str
    role: DocumentRole
    kind: str
    media_type: str
    size: int
    sha256: str
    warnings: list[str]


@dataclass(frozen=True)
class StoredAttachment:
    """An uploaded file with its bytes and sections, for the importer and the content route."""

    row: AttachmentRow
    content: bytes
    sections: list[Section]


def attachment_seq(attachment_id: str) -> int | None:
    """The table key of an ``ATT-<n>`` ID, or None when the ID has another shape."""
    prefix, _, number = attachment_id.partition("-")
    return int(number) if prefix == "ATT" and number.isdigit() else None


def _attachment(record: Sequence[Any]) -> AttachmentRow:
    seq, name, role, kind, media_type, size, sha256, warnings = record
    return AttachmentRow(
        f"ATT-{seq}", name, role, kind, media_type, size, sha256, json.loads(warnings)
    )


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


class AttachmentSource(Protocol):
    """What the importer node needs: one stored file of a session."""

    async def attachment(self, session_id: str, attachment_id: str) -> StoredAttachment | None: ...


class Database(Protocol):
    """One SQL database as the store uses it."""

    time_type: str
    blob_type: str

    async def rows(self, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        """Run ``query`` (``?`` placeholders) and return its rows as tuples."""
        ...

    def stamp(self, moment: datetime) -> Any:
        """A timestamp as this database stores it."""
        ...

    def moment(self, value: Any) -> datetime:
        """A stored timestamp as a datetime."""
        ...


class SqlSessionStore:
    """What the session API, the agent endpoint and the importer need from the two tables."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def setup(self) -> None:
        for statement in SCHEMA:
            await self.db.rows(statement.format(time=self.db.time_type, blob=self.db.blob_type))

    def _session(self, record: Sequence[Any]) -> SessionRow:
        session_id, name, stage, current_step, created_at, updated_at = record
        created, updated = self.db.moment(created_at), self.db.moment(updated_at)
        return SessionRow(session_id, name, stage, current_step, created, updated)

    async def _sessions(self, query: str, params: Sequence[Any]) -> list[SessionRow]:
        return [self._session(record) for record in await self.db.rows(query, params)]

    def _now(self) -> Any:
        return self.db.stamp(datetime.now(UTC))

    # --- sessions ------------------------------------------------------------------------------

    async def create(self, session_id: str, name: str, stage: str, current_step: int) -> SessionRow:
        now = self._now()
        (row,) = await self._sessions(
            f"INSERT INTO sessions ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?) RETURNING {COLUMNS}",
            (session_id, name, stage, current_step, now, now),
        )
        return row

    async def get(self, session_id: str) -> SessionRow | None:
        rows = await self._sessions(f"SELECT {COLUMNS} FROM sessions WHERE id = ?", (session_id,))
        return rows[0] if rows else None

    async def page(self, limit: int, cursor: str | None) -> tuple[list[SessionRow], str | None]:
        """Sessions by updated_at descending (ties by id), keyset-paginated (S3.2)."""
        query = f"SELECT {COLUMNS} FROM sessions"
        params: list[Any] = []
        if cursor is not None:
            updated_at, session_id = decode_cursor(cursor)
            query += " WHERE (updated_at, id) < (?, ?)"
            params += [self.db.stamp(updated_at), session_id]
        rows = await self._sessions(
            query + " ORDER BY updated_at DESC, id DESC LIMIT ?", [*params, limit + 1]
        )
        if len(rows) > limit:
            return rows[:limit], encode_cursor(rows[limit - 1])
        return rows, None

    async def rename(self, session_id: str, name: str) -> SessionRow | None:
        rows = await self._sessions(
            f"UPDATE sessions SET name = ?, updated_at = ? WHERE id = ? RETURNING {COLUMNS}",
            (name, self._now(), session_id),
        )
        return rows[0] if rows else None

    async def record_progress(self, session_id: str, stage: str, current_step: int) -> None:
        """Called after each agent run so the list shows the stage and recent activity."""
        await self.db.rows(
            "UPDATE sessions SET stage = ?, current_step = ?, updated_at = ? WHERE id = ?",
            (stage, current_step, self._now(), session_id),
        )

    async def delete(self, session_id: str) -> None:
        await self.db.rows("DELETE FROM attachments WHERE session_id = ?", (session_id,))
        await self.db.rows("DELETE FROM sessions WHERE id = ?", (session_id,))

    # --- attachments (S14.3) -----------------------------------------------------------------

    async def add_attachment(
        self, session_id: str, name: str, role: DocumentRole, data: bytes, parsed: ParsedFile
    ) -> AttachmentRow:
        sections = json.dumps([[s.locator, s.text] for s in parsed.sections])
        (record,) = await self.db.rows(
            "INSERT INTO attachments (session_id, seq, name, role, kind, media_type, size, "
            "sha256, warnings, sections, content) VALUES "
            "(?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM attachments WHERE session_id = ?), "
            f"?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING {ATTACHMENT_COLUMNS}",
            (
                session_id,
                session_id,
                name,
                role,
                parsed.kind,
                parsed.media_type,
                len(data),
                hashlib.sha256(data).hexdigest(),
                json.dumps(parsed.warnings),
                sections,
                data,
            ),
        )
        return _attachment(record)

    async def attachments(self, session_id: str) -> list[AttachmentRow]:
        records = await self.db.rows(
            f"SELECT {ATTACHMENT_COLUMNS} FROM attachments "
            "WHERE session_id = ? AND NOT removed ORDER BY seq",
            (session_id,),
        )
        return [_attachment(record) for record in records]

    async def attachment(self, session_id: str, attachment_id: str) -> StoredAttachment | None:
        records = await self.db.rows(
            f"SELECT {ATTACHMENT_COLUMNS}, content, sections FROM attachments "
            "WHERE session_id = ? AND seq = ? AND NOT removed",
            (session_id, attachment_seq(attachment_id)),
        )
        if not records:
            return None
        *columns, content, sections = records[0]
        stored = [Section(*s) for s in json.loads(sections)]
        return StoredAttachment(_attachment(columns), bytes(content), stored)

    async def remove_attachment(self, session_id: str, attachment_id: str) -> None:
        await self.db.rows(
            "UPDATE attachments SET removed = true, content = NULL, sections = '[]' "
            "WHERE session_id = ? AND seq = ?",
            (session_id, attachment_seq(attachment_id)),
        )


class PostgresDatabase:
    """Server mode: Postgres through the shared psycopg pool."""

    time_type = "TIMESTAMPTZ"
    blob_type = "BYTEA"

    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self.pool = pool

    async def rows(self, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        async with self.pool.connection() as conn, conn.cursor(row_factory=tuple_row) as cursor:
            await cursor.execute(query.replace("?", "%s"), tuple(params))
            return await cursor.fetchall() if cursor.description else []

    def stamp(self, moment: datetime) -> datetime:
        return moment

    def moment(self, value: Any) -> datetime:
        assert isinstance(value, datetime)
        return value
