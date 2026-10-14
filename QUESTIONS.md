# QUESTIONS — Blueprint Studio build

Conflicts between sources and open questions found during the build. Per `CLAUDE.md`, a conflict between two sources is settled by the higher source and recorded here; a genuine ambiguity blocks its ticket. Each entry says which applies.

Versions were checked against PyPI and npm on 2026-10-14. Every version pinned in `PRD.md` D13 exists. The entries below record where a pinned library's current API, or a higher-authority source, differs from what SPECS or PRD assume.

## Q-1 — T-01
**Clauses:** PRD D9, D13 (`langchain-anthropic` 1.7.6), SPECS S1.6, MODEL-CONNECTION "One protocol, any model"
**Question:** D13 pins `langchain-anthropic`, which exists only for SPECS' native Anthropic option. MODEL-CONNECTION forbids provider-specific code, SDKs and settings, and builds every model with `init_chat_model(model_provider="openai", ...)`.
**Options:** (a) Install `langchain-anthropic` unused: a provider SDK sits in the dependency tree for no reason. (b) Omit it: every model goes through `langchain-openai`, and Anthropic is reached through its OpenAI-compatible endpoint.
**Resolution (conflict, settled by authority):** (b). MODEL-CONNECTION outranks PRD. `langchain-anthropic` is not a dependency.

## Q-2 — T-01
**Clauses:** T-01 AC 1, SPECS S1.2, S1.3, S1.4, MODEL-CONNECTION "Configuration"
**Question:** T-01 asks for `.env.example` to document "every S1.3 variable with an OpenAI-compatible block and an Anthropic block". MODEL-CONNECTION removes `MODEL_PROVIDER` and `REVIEW_MODEL_PROVIDER`, makes the base URL required, and allows no native Anthropic option. S1.4's "a provider value is unsupported" condition no longer exists.
**Options:** (a) Keep the provider variables: contradicts MODEL-CONNECTION. (b) Write the Anthropic block as an OpenAI-compatible configuration (`https://api.anthropic.com/v1/` plus a Claude model name) using only the three variables per role.
**Resolution (conflict, settled by authority):** (b). It satisfies T-01's wording and MODEL-CONNECTION's rules. The agent refuses to start, naming the variable, when `MODEL_BASE_URL`, `MODEL_NAME`, `REVIEW_MODEL_BASE_URL`, `REVIEW_MODEL_NAME` or `DATABASE_URL` is missing or blank, or when `SESSION_TOKEN_BUDGET`, `PORT`, `LANGSMITH_TRACING` or `SKIP_MODEL_CHECK` cannot be parsed. The API keys may be blank.

## Q-3 — T-01
**Clauses:** T-01 AC 5, SPECS S1.7, S1.8, MODEL-CONNECTION "Capability differences", "Building models"
**Question:** T-01 and S1.7 say a failed startup check names "the role, capability, provider and model". MODEL-CONNECTION says "the role, the capability, the base URL and the model". S1.8 compares a (provider, model name, base URL) triple, while MODEL-CONNECTION compares a (base URL, model name) pair.
**Options:** (a) Invent a provider label: there is no provider setting to read it from. (b) Treat the base URL as the provider identity in both places.
**Resolution (conflict, settled by authority):** (b). The refusal names role, capability, base URL and model. `review_model_distinct` compares (base URL with any trailing `/` removed, model name).

## Q-4 — T-01
**Clauses:** T-01 AC 7, SPECS S12.1, S12.2, MODEL-CONNECTION "Design judge prompts"
**Question:** S12.1, which T-01 cites, lists five files. MODEL-CONNECTION adds `design-judge-reviewer.md` and `design-judge-merge.md`, which "ship with the other `app-assets/` files, verbatim (S12)".
**Options:** (a) Ship and check only the five S12.1 files: the review nodes in T-10 would have no prompt. (b) Ship all seven files and refuse to start if any of them is missing or empty.
**Resolution (conflict, settled by authority):** (b). MODEL-CONNECTION outranks SPECS, and (b) still meets T-01's criterion for the five files it names.

## Q-5 — T-01
**Clauses:** SPECS S4.3, S4.4, PRD D2, D13 (`@copilotkit/react-ui` 1.79.0)
**Question:** The CopilotKit 1.79 v2 API differs from what SPECS assumes in three places. (1) The v2 provider (`CopilotKit` from `@copilotkit/react-core/v2`) takes `agentId`, not `agent`, and has no thread prop; the thread is set with `threadId` on `useAgent` and `CopilotChat`. (2) `@copilotkit/runtime/v2` serves the runtime through `createCopilotRuntimeHandler({ runtime, basePath })`, a fetch handler mounted on a Next.js catch-all route. (3) The v2 `CopilotChat` ships in `@copilotkit/react-core/v2`, so `@copilotkit/react-ui` is not used.
**Options:** Follow the library, as `CLAUDE.md` directs.
**Resolution (library differs from SPECS):** `agentId="blueprint"` on the provider; the session ID goes to `threadId` on `CopilotChat` and `useAgent` (from T-02, when sessions exist); the runtime is served at `/api/copilotkit/[[...slug]]`; `@copilotkit/react-ui` is not installed.

## Q-6 — T-01
**Clauses:** PRD OQ-2, D5, SPECS S5.1, S5.6, S11.4
**Question:** OQ-2 asks whether CopilotKit frontend tools reach nodes of a hand-built `StateGraph`, or whether the interviewer must run as a `create_agent` subgraph.
**Options:** (a) Hand-built `StateGraph`, with frontend tools read from state. (b) A `create_agent` subgraph wrapped by `CopilotKitMiddleware`.
**Resolution (settled by evidence, recorded for review):** (a). In `ag-ui-langgraph` 0.0.47, `LangGraphAgent` writes the run's frontend tools into `state["tools"]` and `state["copilotkit"]["actions"]` for any compiled graph. `CopilotKitMiddleware` is only the `create_agent` route to the same data. T-01's AG-UI endpoint test proves three things through the real `/agent` route: a node of the hand-built graph sees a frontend tool's schema; a call to that tool streams to the client as `TOOL_CALL_*` events and the run ends without executing it; and the next run's tool result reaches the node. `copilotkit_customize_config(config, emit_tool_calls=...)` lets a node hold back tool-call streaming, which S5.6 needs so that blockers are checked before a card opens.
