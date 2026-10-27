"""The attachments table in both stores (SPEC-document-import §3)."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from conftest import open_pool

from blueprint.imports.files import ParsedFile, Section
from blueprint.storage.sessions import PostgresDatabase, SqlSessionStore
from blueprint.storage.sqlite import open_sqlite

PARSED = ParsedFile("text", "text/markdown", [Section("Goals", "Fast redirects")], ["note"])


@pytest.fixture(params=["sqlite", "postgres"])
async def store(request: pytest.FixtureRequest, tmp_path: Path) -> AsyncIterator[SqlSessionStore]:
    if request.param == "sqlite":
        async with open_sqlite(str(tmp_path / "blueprint.db")) as (_, sqlite_store):
            yield sqlite_store
        return
    database_url: str = request.getfixturevalue("database_url")
    async with open_pool(database_url) as pool:
        postgres_store = SqlSessionStore(PostgresDatabase(pool))
        await postgres_store.setup()
        yield postgres_store


async def test_attachments_are_numbered_per_session_and_never_reuse_a_number(
    store: SqlSessionStore,
) -> None:
    await store.create("s1", "One", "interview", 1)
    await store.create("s2", "Two", "interview", 1)
    first = await store.add_attachment("s1", "brief.md", "prd", b"# Goals", PARSED)
    second = await store.add_attachment("s1", "more.md", "prd", b"# More", PARSED)
    other = await store.add_attachment("s2", "brief.md", "prd", b"# Goals", PARSED)
    assert (first.id, second.id, other.id) == ("ATT-1", "ATT-2", "ATT-1")
    assert first.size == 7 and first.warnings == ["note"] and len(first.sha256) == 64

    await store.remove_attachment("s1", "ATT-2")
    assert [a.id for a in await store.attachments("s1")] == ["ATT-1"]
    assert await store.attachment("s1", "ATT-2") is None
    third = await store.add_attachment("s1", "again.md", "prd", b"# Again", PARSED)
    assert third.id == "ATT-3"


async def test_a_stored_attachment_keeps_its_bytes_and_sections(store: SqlSessionStore) -> None:
    await store.create("s1", "One", "interview", 1)
    await store.add_attachment("s1", "brief.md", "prd", b"# Goals", PARSED)
    stored = await store.attachment("s1", "ATT-1")
    assert stored is not None
    assert stored.content == b"# Goals"
    assert stored.sections == [Section("Goals", "Fast redirects")]
    assert await store.attachment("s1", "not-an-id") is None


async def test_deleting_a_session_deletes_its_attachments(store: SqlSessionStore) -> None:
    await store.create("s1", "One", "interview", 1)
    await store.add_attachment("s1", "brief.md", "prd", b"# Goals", PARSED)
    await store.delete("s1")
    assert await store.attachments("s1") == []
    await store.create("s1", "One again", "interview", 1)
    assert (await store.add_attachment("s1", "b.md", "prd", b"x", PARSED)).id == "ATT-1"
