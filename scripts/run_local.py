"""Run Blueprint Studio locally, without Docker: the agent (uv) and the web app (Node).

    python3 scripts/run_local.py           # development server, picks up code changes
    python3 scripts/run_local.py --prod    # production build, then serve it
    python3 scripts/run_local.py --port 3001

Settings come from .env at the repository root (copy .env.example). With the default
DATABASE_URL=sqlite:///blueprint.db, sessions are kept in agent/blueprint.db; no database
server is needed. Both processes listen on 127.0.0.1 only, so nothing is reachable from
another machine, whatever HOST says in .env. Ctrl+C stops both processes. Standard library
only, Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
# Local mode serves this machine only: both servers bind to loopback, never to every interface.
LOOPBACK = "127.0.0.1"


def fail(message: str) -> NoReturn:
    print(f"run_local: {message}", file=sys.stderr)
    sys.exit(1)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip("'\"")
    return values


def tool(name: str, hint: str) -> str:
    found = shutil.which(name)
    if found is None:
        fail(f"{name} is not on PATH; {hint}")
    return str(found)


def start(
    command: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.Popen[bytes]:
    # Each child gets its own process group so that stopping it also stops what it started.
    if sys.platform == "win32":
        return subprocess.Popen(
            command, cwd=cwd, env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    return subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True)


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)


def wait_for_agent(agent: subprocess.Popen[bytes], health_url: str, timeout_s: float) -> None:
    """The agent checks both models at startup, so allow it time; stop if it gives up."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if agent.poll() is not None:
            fail(f"the agent stopped (exit code {agent.returncode}); see its message above")
        try:
            with urllib.request.urlopen(health_url, timeout=2):
                return
        except OSError:
            time.sleep(0.5)
    fail(f"the agent did not answer {health_url} within {timeout_s:.0f}s")


def interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def main() -> None:
    # Ctrl+C and a polite kill both stop the agent and the web app with the launcher,
    # even when the launcher was started in the background (where SIGINT starts ignored).
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    parser = argparse.ArgumentParser(description="Run Blueprint Studio locally, without Docker.")
    parser.add_argument(
        "--prod", action="store_true", help="build and serve the production web app"
    )
    parser.add_argument("--port", type=int, default=3000, help="web app port (default 3000)")
    args = parser.parse_args()

    if not ENV_FILE.is_file():
        fail(f"no .env found; copy .env.example to {ENV_FILE} and fill in both model roles")
    settings = read_env(ENV_FILE)
    agent_url = (settings.get("AGENT_URL") or "http://127.0.0.1:8000").rstrip("/")

    uv = tool("uv", "install it from https://docs.astral.sh/uv/")
    node = tool("node", "install Node.js 24 from https://nodejs.org/")
    npm = tool("npm", "it comes with Node.js")

    web = ROOT / "web"
    if not (web / "node_modules").is_dir():
        print("run_local: installing the web app's packages (first run only)", flush=True)
        subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=web, check=True)
    if args.prod:
        print("run_local: building the web app", flush=True)
        subprocess.run([npm, "run", "build"], cwd=web, check=True)

    processes: list[subprocess.Popen[bytes]] = []
    try:
        print(
            "run_local: starting the agent (uv installs Python and packages on first run)",
            flush=True,
        )
        # A variable already in the environment wins over --env-file, so HOST is loopback here.
        agent = start(
            [uv, "run", "--env-file", str(ENV_FILE), "python", "-m", "blueprint"],
            ROOT / "agent",
            dict(os.environ, HOST=LOOPBACK),
        )
        processes.append(agent)
        wait_for_agent(agent, f"{agent_url}/agent/health", timeout_s=600)

        next_bin = str(web / "node_modules" / "next" / "dist" / "bin" / "next")
        mode = "start" if args.prod else "dev"
        web_env = dict(os.environ, AGENT_URL=agent_url, NEXT_TELEMETRY_DISABLED="1")
        processes.append(
            start([node, next_bin, mode, "-H", LOOPBACK, "-p", str(args.port)], web, web_env)
        )
        print(f"run_local: Blueprint Studio is starting at http://{LOOPBACK}:{args.port} "
              "(Ctrl+C stops it)", flush=True)  # fmt: skip

        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        fail("a process stopped unexpectedly; see its message above")
    except KeyboardInterrupt:
        print("\nrun_local: stopping", flush=True)
    finally:
        for process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    main()
