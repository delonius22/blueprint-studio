# Blueprint Studio

A web app where an AI agent walks you through the five-step system-design framework. A second model then reviews the design for security, efficiency and maintainability gaps. The app drafts a PRD for you to sign off, extends it with `to-spec`, breaks it into tickets with `to-tickets`, and hands back Word documents plus a `context.md` that any agent can follow to create the Jira issues.

Built with CopilotKit and LangGraph (Python). It runs on any OpenAI-compatible model endpoint.

## Run it

You need Docker with Compose.

```sh
cp .env.example .env    # fill in both model roles (see below)
docker compose up --build
```

Then open <http://localhost:3000>.

The app uses two model roles, each configured by a base URL, an API key and a model name:

| Role | Variables | Used for |
|---|---|---|
| Interview | `MODEL_BASE_URL`, `MODEL_API_KEY`, `MODEL_NAME` | The interviewer, critiques, PRD drafting, `to-spec`, `to-tickets` |
| Review | `REVIEW_MODEL_BASE_URL`, `REVIEW_MODEL_API_KEY`, `REVIEW_MODEL_NAME` | The design judge: security, efficiency and maintainability reviewers and the gap merger |

- **Endpoints:** any OpenAI-compatible Chat Completions endpoint works, including OpenAI, Anthropic's compatibility endpoint, a gateway such as LiteLLM or OpenRouter, or a local server such as Ollama.
- **Startup check:** both models must support tool calling and structured output, and the agent checks this at startup.
- **Use two different models:** if both roles point at the same model, the review still runs, but the app warns that the cross-model check is off.
- **Other settings:** `.env.example` documents the rest.

All model calls go through one factory, `agent/src/blueprint/models.py`. API keys stay in the agent container and never reach the web container.

## Run without Docker

You need these on the machine:
- [uv](https://docs.astral.sh/uv/), which downloads Python 3.14 itself if it's missing.
- Node.js 24.
- A Postgres database. Either install Postgres locally and create an empty database (`createuser -P blueprint` then `createdb -O blueprint blueprint`), or use a hosted Postgres such as Neon or Supabase.

The agent creates its tables on first start.

In `.env`, point two settings at your machine instead of the Docker service names:

```sh
DATABASE_URL=postgresql://blueprint:<password>@localhost:5432/blueprint
AGENT_URL=http://localhost:8000
```

Then start the agent and the web app in two terminals:

```sh
# Terminal 1: the agent, on port 8000
cd agent
uv run --env-file ../.env python -m blueprint    # installs Python 3.14 and dependencies on first run

# Terminal 2: the web app, on port 3000
cd web
npm ci
npm run build
AGENT_URL=http://localhost:8000 npm start
```

- **Windows (PowerShell):** set the variable first with `$env:AGENT_URL="http://localhost:8000"`, then run `npm start`.
- **Startup warning:** `next start` warns that it "does not work with output: standalone". That warning is harmless here: the app runs normally.
- **Port in use:** to use a port other than 3000, run `npm start -- -p <port>`.

## Layout

| Path | What it is |
|---|---|
| `agent/` | Python 3.14 service (FastAPI, LangGraph, CopilotKit, python-docx), managed with `uv` |
| `web/` | Next.js 16 App Router front end with the CopilotKit v2 hooks |
| `app-assets/` | Runtime prompts the agent ships verbatim: interviewer instructions, course context, design-judge prompts, `to-spec`, `to-tickets` and their MIT licence |
| `docker-compose.yml` | Postgres, agent and web |
| `docker-compose.e2e.yml` | Override for the end-to-end test that swaps in a scripted fake model |

## Develop and test

No API key or network access is needed: the tests use scripted fake models.

```sh
# Agent: lint, types, tests (the tests start a throwaway postgres:16 container, so Docker must be running)
cd agent
uv sync
uv run ruff check . && uv run mypy && uv run pytest

# Web: types, unit tests, end-to-end smoke test
cd web
npm ci
npx tsc --noEmit && npm test
npx playwright install chromium
npm run test:e2e        # builds and starts the full stack, then runs five sessions to zip download
```

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
| `TICKETS.md` | The 20 tickets the app was built from, with acceptance criteria |
| `QUESTIONS.md` | Conflicts and questions raised during the build, and how each was settled |
