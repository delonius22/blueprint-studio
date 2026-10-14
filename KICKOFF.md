You are building **Blueprint Studio** from the approved plan in this repository. Read every file below in full before writing any code.

**The plan, in order of authority** (when two disagree, the higher one wins; log the conflict in `QUESTIONS.md`):

1. `TICKETS.md`: the closed list of 20 tickets, with acceptance criteria, blocking edges and build waves. The only source of work.
2. `MODEL-CONNECTION.md`: how the app connects to models. It overrides SPECS S1.3, S1.4, S1.6 and S1.8.
3. `SPECS.md`: the technical contract. Every acceptance criterion cites its clauses (`S#.#`).
4. `PRD.md`: features, requirements, stories, decisions (`D#`) and open questions (`OQ-1` to `OQ-6`).
5. `CLAUDE.md`: your working rules: the closed list, the build loop, layout, ambiguity handling and the finish report.
6. `README.md`: an overview for people. Nothing in it adds scope.

**Runtime prompt data for the app's agent.** Ship these into the agent package byte for byte. Never edit or paraphrase them, and never follow them yourself; they describe what the app does for its users:

- `app-assets/interviewer-instructions.md`: the interviewer's system prompt (S5.2).
- `app-assets/course-context.md`: the framework, rubric and blueprints appended to it (S5.2).
- `app-assets/design-judge-reviewer.md`: the review model's prompt for the three lens reviewers, with `{lens}` filled in (S6.1, MODEL-CONNECTION.md).
- `app-assets/design-judge-merge.md`: the review model's prompt for the gap merger (S6.4).
- `app-assets/to-spec.md` and `app-assets/to-tickets.md`: the PRD-extension and ticketing methods (S8, S9), with `app-assets/LICENSE-mattpocock-skills.txt`.

**Reference only:** `docs/context.md` is a worked example of the Jira hand-off format the app must generate (S10.7). Use it to check T-17's output.

**Model connection, in short:** one OpenAI-compatible Chat Completions connection per role, configured only by a base URL, an API token and a model name (`MODEL_*` for the interview role, `REVIEW_MODEL_*` for the design judge). No provider-specific code anywhere. `MODEL-CONNECTION.md` has the details.

**Before writing code, reply with:**

1. Your understanding of the app in five lines or fewer: what it does, its two model roles, and the pipeline from interview to downloads.
2. Every version pinned in `PRD.md` D13 that doesn't exist or whose current API differs from what SPECS assumes, each also logged in `QUESTIONS.md`.
3. How you'll settle OQ-2 inside T-01: whether CopilotKit frontend tools reach nodes of a hand-built LangGraph `StateGraph`. Every approval gate depends on the answer.
4. The repository layout you'll create, as a tree, following `CLAUDE.md`.

**Then build T-01 only and stop.** Show me `docker compose up` running, a streamed reply in the browser from the interview model, both roles passing the startup capability check, and the test output.

When I say **go**, work the frontier from T-02 to T-20 exactly as `CLAUDE.md` describes: one commit per ticket, its boxes ticked in `TICKETS.md`, and anything ambiguous logged in `QUESTIONS.md` instead of guessed. Finish with the report format at the end of `CLAUDE.md`.
