# MODEL-CONNECTION — how the app talks to models

> This file **supersedes** SPECS.md S1.3, S1.4, S1.6 and S1.8 wherever they mention `MODEL_PROVIDER`, `REVIEW_MODEL_PROVIDER`, a native Anthropic option or LangChain's `init_chat_model`. Every other clause stands.

## One protocol, any model

- The app speaks exactly one protocol: the **OpenAI-compatible Chat Completions API**. Any model that exposes it works: a hosted vendor, a gateway or router, or a local server.
- The only SDK is OpenAI's own Python SDK (`openai`), used in one module. There is no other provider-specific code, SDK, header or setting anywhere in the app.
- A model with no OpenAI-compatible endpoint is connected through a gateway placed in front of it (for example LiteLLM, or Ollama for local models), with the base URL pointed at the gateway.

## Configuration

Each of the two roles is configured by exactly three variables:

| Interview role | Review role (design judge) | Meaning |
|---|---|---|
| `MODEL_BASE_URL` | `REVIEW_MODEL_BASE_URL` | The Chat Completions base URL |
| `MODEL_API_KEY` | `REVIEW_MODEL_API_KEY` | Sent as a Bearer token; may be blank for keyless local servers |
| `MODEL_NAME` | `REVIEW_MODEL_NAME` | The model identifier the endpoint expects |

- The agent refuses to start, naming the variable, if either base URL or model name is missing.
- `.env.example` documents both roles with placeholder values only.

## Connecting and calling

- `agent/src/blueprint/models.py` is the only module that imports the `openai` SDK.
  - **Clients:** it builds one `openai.AsyncOpenAI` client per role from that role's base URL and key. Each client has a 120 s timeout and the SDK's own retries switched off, so S13.1 is the only retry policy.
  - **Calls:** it makes every call with `client.chat.completions.create`. A chat reply streams, with `stream_options.include_usage`. Structured output is either `response_format` with a strict JSON schema or one forced tool call (S13.4).
  - **Messages:** the graph keeps its conversation as LangChain messages, because LangGraph and CopilotKit need that format. The module converts them to Chat Completions messages on the way out and turns replies back into `AIMessage` objects on the way in.
- A reply's message ID is never the provider's completion ID. Some OpenAI-compatible servers reuse one completion ID, and two messages with the same ID would replace each other in state.
- `agent/src/blueprint/llm.py` (the gateway) reports each call to LangGraph's callbacks the way a LangChain chat model reports itself. That is how the AG-UI bridge streams the interviewer's reply to the browser, and how `LANGSMITH_TRACING` traces model calls.
- The review model is **distinct** when its (base URL, model name) pair differs from the interview model's. When it is not distinct, the review still runs and the workspace shows the warning in S6.6.

## Capability differences

Support for tool calling and structured output varies by model.

- Structured output requests JSON-schema mode first and falls back once to tool calling (S13.4).
- The startup check (S1.7) runs for both roles and, on failure, names the role, the capability, the base URL and the model.

## Design judge prompts

- `app-assets/design-judge-reviewer.md` is the system prompt for the three reviewer nodes (S6.1), with `{lens}` replaced by `security`, `efficiency` or `maintainability`.
- `app-assets/design-judge-merge.md` is the system prompt for the `gap_merger` (S6.4).
- Both run on the review role and ship with the other `app-assets/` files, verbatim (S12). They replace the reviewer instructions S6.2 and S6.3 describe, and say the same thing.
