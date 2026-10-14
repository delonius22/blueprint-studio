# Blueprint Studio — planning package

Everything Claude Code needs to build Blueprint Studio, plus the same plan as Word documents for people.

**Blueprint Studio** is a web app where an AI agent, built with CopilotKit and LangGraph (Python) and runnable on any capable model, guides a user through the five-step system-design framework. A second model then reviews the design for security, efficiency and maintainability gaps. The app drafts a PRD the user signs off, extends it with `to-spec`, breaks it into tickets with `to-tickets`, and hands back Word documents plus a `context.md` that any agent can follow to create the Jira issues.

## How to start the build

1. Open this folder in Claude Code.
2. Paste the contents of `KICKOFF.md` as your first message.
3. Claude Code reports its understanding, checks versions, builds T-01 and stops for your review. Say "go" and it works through T-02 to T-20.

Have your `.env` ready: a base URL, API token and model name for each role (`MODEL_*` for the interview model, `REVIEW_MODEL_*` for the design judge), plus a `DATABASE_URL`. Any OpenAI-compatible endpoint works; see `MODEL-CONNECTION.md`.

## What's here

| File | For | What it is |
|---|---|---|
| `KICKOFF.md` | You → Claude Code | The first prompt to paste |
| `CLAUDE.md` | Claude Code | The build brief, loaded automatically: closed ticket list, working loop, layout, how to handle ambiguity |
| `PRD.md` | Both | Problem, solution, 7 features, 29 functional and 13 non-functional requirements, 55 user stories, decisions, open questions |
| `SPECS.md` | Claude Code | 87 numbered technical clauses (`S#.#`) that every ticket cites |
| `MODEL-CONNECTION.md` | Claude Code | One OpenAI-compatible connection per model role (base URL, token, model name); overrides SPECS §1 where they differ |
| `TICKETS.md` | Both | The 20 approved tickets with acceptance criteria, blocking edges and build waves |
| `app-assets/` | The app's agent | Runtime prompts shipped inside the app, verbatim: interviewer instructions, course context, design-judge reviewer and merge prompts, `to-spec`, `to-tickets`, MIT licence |
| `docs/PRD.docx` | People | The PRD as a Word document |
| `docs/Requirements.docx` | People | Requirements with features and story coverage |
| `docs/UserStories.docx` | People | Stories by feature, tickets with acceptance criteria, build waves |
| `docs/context.md` | Any agent | This project's own Jira hand-off. Fill in the site and project key, then give it to an agent to create the epics, stories and tasks. It is also the reference example for the format the app generates. |

## Decisions worth knowing before you read

- **No skeleton stage, no code generation** for designed systems. The app stops at documents and the Jira hand-off.
- **Two model roles** (interview and review), configured separately. The app warns when both are the same model.
- **Sign-off is binding.** PRD v1.0 is frozen once signed. `to-spec` extends it into v1.1 without changing it, and any change goes through per-item approval into v1.2.
- **Nothing unapproved reaches Jira.** Open gaps never become tickets; `context.md` forbids the receiving agent from adding anything.
- **Python 3.14, not 3.15.** 3.15 shipped on 9 October 2026, but LangGraph's checkpointer depends on `ormsgpack`, which has no 3.15 wheel yet.
