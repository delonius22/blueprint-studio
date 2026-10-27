# Blueprint Studio

A web app where an AI agent walks you through the five-step system-design framework. A second model then reviews the design for security, efficiency and maintainability gaps. The app drafts a PRD for you to sign off, extends it with `to-spec`, breaks it into tickets with `to-tickets`, and hands back Word documents, Mermaid diagrams of the design (`Diagrams.md`: architecture, data model and one sequence per flow) and a `context.md` that any agent can follow to create the Jira issues.

You can also attach what you already have: a PRD or spec (`.md`, `.txt`, `.pdf`, `.docx`), a diagram (`.mmd`, `.drawio`, or an image when the interview model reads images) or notes. The agent quotes what each file states, you accept, edit or reject each item before it is recorded, items for later steps wait for their step, and the interviewer asks about whatever the file leaves weak.

Built with CopilotKit and LangGraph (Python). It runs on any OpenAI-compatible model endpoint.

## Run it

There are two modes. Both read the same `.env`:

```sh
cp .env.example .env    # fill in both model roles (see below)
```

| | Local mode | Server mode |
|---|---|---|
| For | Your own machine, no Docker | A server, in containers |
| Start | `python3 scripts/run_local.py` | `docker compose up --build` |
| Needs | [uv](https://docs.astral.sh/uv/), Node.js 24 and any Python 3 | Docker with Compose |
| Database | A SQLite file, `agent/blueprint.db`: nothing to install | Postgres, in its own container |
| Opens at | <http://127.0.0.1:3000>, this machine only | <http://localhost:3000> |

### Local mode

```sh
python3 scripts/run_local.py           # Windows: py scripts\run_local.py
```

The launcher:
- installs the web app's packages on first run;
- starts the agent, letting `uv` download Python 3.14 and the agent's packages on first run;
- waits for the agent's startup model check;
- starts the web app.

Both servers listen on `127.0.0.1` only, so neither is reachable from another machine, even if `.env` sets `HOST=0.0.0.0`. Ctrl+C stops everything.

| Option | What it does |
|---|---|
| (none) | Runs the web app's development server, which picks up code changes |
| `--prod` | Builds and serves the production web app instead |
| `--port <n>` | Uses another web port |

Sessions are kept in `agent/blueprint.db`. Delete that file to start fresh.

To use a local Postgres instead of SQLite, set `DATABASE_URL=postgresql://<user>:<password>@localhost:5432/<database>`. The agent creates its tables on first start.

To run the two processes yourself instead of using the launcher:
- **Agent:** in `agent/`, run `uv run --env-file ../.env python -m blueprint`.
- **Web app:** in `web/`, run `npm ci`, then `npm run build`, then `AGENT_URL=http://127.0.0.1:8000 npm start -- -H 127.0.0.1`. Without `-H`, Next.js listens on every network interface. On Windows PowerShell, set the address first with `$env:AGENT_URL="http://127.0.0.1:8000"`.

`npm start` warns that it "does not work with output: standalone". The app runs normally anyway; the setting is there for the server image.

### Server mode

```sh
docker compose up --build
```

Compose runs Postgres, the agent and the web app. The model settings come from `.env`. Compose fixes `DATABASE_URL`, `AGENT_URL`, `HOST` and `PORT` itself, so a `.env` written for local mode works unchanged.

### Models

The app uses two model roles, each configured by a base URL, an API key and a model name:

| Role | Variables | Used for |
|---|---|---|
| Interview | `MODEL_BASE_URL`, `MODEL_API_KEY`, `MODEL_NAME` | The interviewer, critiques, PRD drafting, `to-spec`, `to-tickets` |
| Review | `REVIEW_MODEL_BASE_URL`, `REVIEW_MODEL_API_KEY`, `REVIEW_MODEL_NAME` | The design judge: security, efficiency and maintainability reviewers and the gap merger |

- **Endpoints:** any OpenAI-compatible Chat Completions endpoint works, including OpenAI, Anthropic's compatibility endpoint, a gateway such as LiteLLM or OpenRouter, or a local server such as Ollama.
- **Startup check:** both models must support tool calling and structured output, and the agent checks this at startup.
- **Use two different models:** if both roles point at the same model, the review still runs, but the app warns that the cross-model check is off.
- **Other settings:** `.env.example` documents the rest.

All model calls go through OpenAI's Python SDK (`openai.AsyncOpenAI`, Chat Completions), and `agent/src/blueprint/llm/clients.py` is the only module that uses it. API keys stay with the agent and never reach the web app.

## Layout

| Path | What it is |
|---|---|
| `agent/` | Python 3.14 service (FastAPI, LangGraph, CopilotKit, the OpenAI SDK, python-docx), managed with `uv` |
| `web/` | Next.js 16 App Router front end with the CopilotKit v2 hooks |
| `app-assets/` | Runtime prompts the agent ships verbatim: interviewer instructions, course context, design-judge prompts, the document importer, `to-spec`, `to-tickets` and their MIT licence |
| `scripts/run_local.py` | Local mode: starts the agent and the web app without Docker |
| `docker-compose.yml` | Server mode: Postgres, agent and web |
| `docker-compose.e2e.yml` | Override for the end-to-end test that swaps in a scripted fake model |

The agent's package, `agent/src/blueprint/`, has one folder per concern:

| Folder | What it holds |
|---|---|
| `config/` | Settings from `.env`, the vendored prompts, startup errors |
| `domain/` | The typed shapes of a session (`models.py`) and the graph state (`state.py`) |
| `llm/` | The model clients, the call gateway (retries, budget, logging) and the startup check |
| `graph/` | The graph's wiring, its pure routing, gate messages and what nodes share |
| `interview/` | The interviewer's tools, prompt, critic, scorecard and nodes |
| `imports/` | Reading attached files, the import proposal and its nodes |
| `review/` | The design review, gap resolution and their nodes |
| `planning/` | PRD v1.0, `to-spec`, proposed changes, tickets and their nodes |
| `storage/` | The sessions and attachments tables over Postgres or SQLite |
| `api/` | The REST routes, the agent endpoint and the OpenAPI export |
| `exports/` | Every download, the Mermaid diagrams included |
| `utils/` | Small helpers several packages share |

The web app groups its components the same way: `components/workspace/`, `canvas/`, `gates/`, `attachments/`, `review/`, `delivery/` and `sessions/`.

## Develop and test

No API key is needed: the tests use scripted fake models. The first `uv sync` and `npm ci` download packages.

```sh
# Agent: lint, types, tests
cd agent
uv sync
uv run ruff check . && uv run mypy && uv run pytest

# Web: types, unit tests, end-to-end smoke test
cd ../web
npm ci
npx tsc --noEmit && npm test
npx playwright install chromium
npm run test:e2e        # needs Docker: builds the server stack, then runs five sessions to zip download
```

- **Postgres tests (server mode):** these start a throwaway `postgres:16` container, or use the database in `TEST_DATABASE_URL`. On a machine with neither, they are skipped. The SQLite tests for local mode need nothing.
- **End-to-end test without Docker:** run it against local mode instead.
  1. Start the fake model with `python3 web/e2e/fake_model.py 9999`.
  2. Point both roles' base URL in `.env` at `http://127.0.0.1:9999/v1`.
  3. Start the app with `python3 scripts/run_local.py --port 3100`.
  4. Run `E2E_REUSE_STACK=1 npm run test:e2e` in `web/`.

The end-to-end test is in `web/e2e/smoke.spec.ts`:
- **What it runs:** five concurrent sessions, each from creating the session to downloading the zip.
- **Accessibility:** it scans the pages for WCAG 2.1 AA in light and dark themes.
- **Reusing a running stack:** set `E2E_REUSE_STACK=1` to use a stack that's already up.

## Design documents

| File | What it is |
|---|---|
| `PRD.md` | Problem, features, functional and non-functional requirements, user stories, decisions (`D#`) |
| `SPECS.md` | The numbered technical clauses (`S#.#`) that the code and tests cite |
| `MODEL-CONNECTION.md` | How the app connects to models; overrides SPECS §1 where they differ |
| `SPEC-document-import.md` | The document-import feature as specified and approved; SPECS §14 holds its clauses |
