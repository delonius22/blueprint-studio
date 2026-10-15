import os
import shutil
import subprocess
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ASSETS = REPO_ROOT / "app-assets"
INTERVIEW_KEY = "sk-interview-test-key-0001"
REVIEW_KEY = "sk-review-test-key-0002"


def valid_env() -> dict[str, str]:
    return {
        "MODEL_BASE_URL": "https://interview.example/v1",
        "MODEL_API_KEY": INTERVIEW_KEY,
        "MODEL_NAME": "interview-model",
        "REVIEW_MODEL_BASE_URL": "https://review.example/v1",
        "REVIEW_MODEL_API_KEY": REVIEW_KEY,
        "REVIEW_MODEL_NAME": "review-model",
        "DATABASE_URL": "postgresql://blueprint:blueprint@localhost:5432/blueprint",
        "SKIP_MODEL_CHECK": "true",
    }


@pytest.fixture
def env() -> dict[str, str]:
    return valid_env()


# --- Postgres for the session API and checkpoint tests ----------------------------------------
# Uses TEST_DATABASE_URL when set; otherwise starts a throwaway postgres:16 container.
# Without either (a machine with no Docker), these tests are skipped; test_sqlite.py covers
# local mode there.


@pytest.fixture(scope="session")
def postgres_admin_url() -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    if shutil.which("docker") is None:
        pytest.skip("Postgres tests need TEST_DATABASE_URL or Docker")
    container = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "-e",
            "POSTGRES_PASSWORD=test",
            "-p",
            "127.0.0.1::5432",
            "postgres:16",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    try:
        port = (
            subprocess.run(
                ["docker", "port", container, "5432/tcp"],
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        url = f"postgresql://postgres:test@127.0.0.1:{port}/postgres"
        deadline = time.monotonic() + 60
        while True:
            try:
                psycopg.connect(url, connect_timeout=2).close()
                break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.3)
        yield url
    finally:
        subprocess.run(["docker", "stop", container], capture_output=True, check=False)


@pytest.fixture
def database_url(postgres_admin_url: str) -> Iterator[str]:
    """A fresh, empty database per test."""
    name = f"t_{uuid.uuid4().hex}"
    with psycopg.connect(postgres_admin_url, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    yield postgres_admin_url.rsplit("/", 1)[0] + f"/{name}"
    with psycopg.connect(postgres_admin_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {name} WITH (FORCE)")


def open_pool(url: str) -> AsyncConnectionPool[Any]:
    return AsyncConnectionPool(
        url,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )


@pytest.fixture
async def pool(database_url: str) -> AsyncIterator[AsyncConnectionPool[Any]]:
    async with open_pool(database_url) as opened:
        yield opened
