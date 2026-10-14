# CLAUDE.md — Blueprint Studio build brief

You are building **Blueprint Studio**: a web app where an AI agent (CopilotKit + LangGraph Python, any capable model) interviews a user through the five-step system-design framework, has a second model review the design for security, efficiency and maintainability gaps, drafts and versions a signed-off PRD, runs the `to-spec` and `to-tickets` methods, and hands back Word documents plus a Jira `context.md`.

Your work is the **closed list** in `TICKETS.md`: build those 20 tickets, to their acceptance criteria, in dependency order.

## Sources, in order of authority

1. `TICKETS.md` — the closed list; the only source of work.
2. `MODEL-CONNECTION.md` — how the app connects to models; it overrides SPECS S1.3, S1.4, S1.6 and S1.8.
3. `SPECS.md` — the technical contract; every acceptance criterion cites its clauses (`S#.#`).
4. `PRD.md` — the reasons: features, requirements, stories, decisions (`D#`), open questions (`OQ-#`).
5. `docs/` — Word versions of the PRD for humans, and `docs/context.md`, a worked example of the Jira hand-off format in S10.7.

When two sources disagree, the higher one wins and you record the conflict in `QUESTIONS.md`.

## The closed list

The 20 tickets are `T-01` to `T-20`. Every line of code you write serves an acceptance criterion of one of them.

- Tickets stay as written: you do not create, split, merge, renumber or reorder them.
- The product stays as specified: you add no feature, screen, endpoint, state field, setting or document that no ticket names.
- Internal helpers, refactors and test fixtures are in scope whenever a ticket's criteria need them.
- When you believe something is missing, record it in `QUESTIONS.md` and keep building what the list says.

## `app-assets/` is runtime data for the app, not instructions for you

`app-assets/` holds the prompts the **app's** agent runs on: the interviewer instructions, the course context, the two design-judge prompts for the review model, `to-spec`, `to-tickets` and their MIT licence (S12, MODEL-CONNECTION.md). Ship them into the agent package byte for byte, exactly as S12.1 says. Never edit them, never paraphrase them into code, and never follow them yourself: `to-spec` and `to-tickets` describe what the app does for its users, not how you plan this build. The planning is already done.

## Working the frontier

The **frontier** is every ticket whose blockers are all done. `TICKETS.md` lists the waves.

1. Take the lowest-numbered ticket on the frontier.
2. Read it, then every `S#.#` clause it cites, in `SPECS.md`.
3. Build it as a **tracer bullet**: one narrow, complete path through every layer it touches (state, graph, API, UI, tests), demoable on its own.
4. Test each acceptance criterion through the seams in `PRD.md` → Testing Decisions: the graph seam with two scripted fake models (one per role), the export seam, and, in T-20 only, the Playwright smoke test. Tests assert observable behaviour: state, stage, HTTP responses, file bytes. No test needs an API key or the network.
5. The ticket is **done** when every acceptance criterion has a passing test, the full suite is green, and lint and type checks pass.
6. In `TICKETS.md`, tick the ticket's boxes and set its **Status** to `done`. That is the only edit you make there.
7. Commit with the ticket ID first in the subject, e.g. `T-04: step confirmation gate and critique`.
8. Recompute the frontier and continue until every ticket is `done` or `blocked-on-question`.

## Layout and stack

- `agent/` — Python 3.14 package (FastAPI, LangGraph, CopilotKit Python SDK, python-docx), src layout, `uv` for dependencies, `ruff`, `mypy --strict` and `pytest`.
- `web/` — Next.js 16.4 App Router on Node 24 LTS with TypeScript 7.0.2, CopilotKit 1.79 v2 hooks, `vitest` and Playwright.
- `app-assets/` — stays at the repository root as the source; the agent build copies it in as package data.
- `docker-compose.yml` and `.env.example` at the root.

Exact versions are pinned in `PRD.md` D13; use them. The integration pattern (AG-UI endpoint, CopilotRuntime proxy, `useAgent`, `useHumanInTheLoop`) is fixed in D1, D2 and D5 and in SPECS §4. Where a library's current API differs from what SPECS assumes, follow the library and log the difference in `QUESTIONS.md`.

## When a ticket is ambiguous

Ambiguity is a signal to ask. A ticket is ambiguous when its criteria and cited clauses leave a behaviour undecided, contradict each other, or seem to need work outside the closed list. `PRD.md` → Further Notes already lists `OQ-1` to `OQ-6`; treat each as open unless a ticket's criteria settle it.

1. Append to `QUESTIONS.md`:
   ```
   ## Q-<n> — <ticket ID>
   **Clauses:** <S, FR, US or OQ IDs involved>
   **Question:** <what is undecided or contradictory, in one or two sentences>
   **Options:** <the reasonable readings, each with its consequence>
   ```
2. Set the ticket's **Status** to `blocked-on-question`, keep its partial work on a branch named after the ticket, and move to the next frontier ticket. Tickets it blocks wait with it.

## Finishing

You are finished when every ticket is `done` or `blocked-on-question` and `docker compose up` runs the app end to end with real models. Report:

```
Done: <ticket IDs>
Blocked: <ticket ID → Q-n, one per line>
Tests: <passed> passed, 0 failed
Open questions: <count>, see QUESTIONS.md
How to run: <the exact commands>
```

## Backlog mirror

Backlog tasks `TASK-1` to `TASK-20` mirror `T-01` to `T-20` (same number), with the same acceptance criteria and blocking edges. `TICKETS.md` stays authoritative and the closed-list rules apply to Backlog too: never create, split, merge or edit the scope of a task. Keep the two in step:

- When you start a ticket, set its task to `In Progress`.
- At step 6 of the working loop, also check the task's criteria and set it to `Done`.
- When a ticket becomes `blocked-on-question`, leave its task `In Progress` and add a note naming the `Q-<n>`.

<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.52.0 -->
<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**At the beginning of each conversation in this project, run `backlog instructions overview` before answering or taking action. Re-read it only if you have not read it yet in the current conversation.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:
- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>
<!-- BACKLOG.MD GUIDELINES END -->
