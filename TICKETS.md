# TICKETS — Blueprint Studio

> **Method:** `to-tickets` (mattpocock-skills 1.2.3, MIT, © 2026 Matt Pocock). Tracer-bullet vertical slices with blocking edges.
> **Deviation from the method, by user requirement:** all tickets live in this one file instead of one file per ticket.
> **Approved:** 2026-10-14. **Ticket count:** 20. **Sources:** `PRD.md` (F, FR, NFR, US, D IDs), `SPECS.md` (S IDs).
> **This list is closed.** `CLAUDE.md` sets the rules for working it.

**Frontier at start:** T-01. Tickets in the same wave can run in parallel once their blockers are done.

| Wave | Tickets | Blocked by |
|---|---|---|
| 1 | T-01 | — |
| 2 | T-02 | T-01 |
| 3 | T-03 | T-02 |
| 4 | T-04 | T-03 |
| 5 | T-05, T-19 | T-04 (each) |
| 6 | T-06 | T-05 |
| 7 | T-07 | T-06 |
| 8 | T-08 | T-07 |
| 9 | T-09, T-10 | T-08 (each) |
| 10 | T-11 | T-10 |
| 11 | T-12 | T-11 |
| 12 | T-13 | T-12 |
| 13 | T-14, T-15 | T-13 (each) |
| 14 | T-16, T-17 | T-15 (each) |
| 15 | T-18 | T-14, T-16, T-17 |
| 16 | T-20 | T-09, T-18, T-19 |

---

# T-01: Walking skeleton with two model roles

**What to build:** One command starts the web app, the agent service and the database. The user opens the app, types a message and sees a streamed reply through the full path: browser → CopilotKit runtime route → FastAPI AG-UI endpoint → LangGraph graph → interview model. Both model roles are configured from the environment and checked at startup, and the vendored runtime assets are loaded.

**Blocked by:** None (can start immediately).

**Delivers stories:** US-51, US-52, US-55

**Status:** done

- [x] `docker compose up` with one `.env` starts `web`, `agent` and `db`; `.env.example` documents every S1.3 variable with an OpenAI-compatible block and an Anthropic block (S1.1, S1.2, S1.3).
- [x] A chat message produces a streamed reply through the runtime proxy, never a direct browser call to FastAPI (S4.1, S4.3, S4.4).
- [x] The agent refuses to start, naming the variable, for each condition in S1.4.
- [x] Every chat model comes from the one two-role factory; no other module imports a provider SDK (S1.6).
- [x] The startup check runs for both roles and refuses to start naming the role, capability, provider and model; `SKIP_MODEL_CHECK=true` skips it (S1.7).
- [x] `review_model_distinct` is computed at startup as S1.8 defines.
- [x] `app-assets/` ships as package data with the five files of S12.1, copied verbatim from this repository's `app-assets/`; the agent refuses to start, naming the file, if any is missing or empty (S12.1, S12.2).
- [x] A graph-seam test with two scripted fake models passes, proving the seam before any feature exists.

---

# T-02: Sessions — create, list, resume, rename, delete

**What to build:** The user lands on a session list, creates a named session, works in it, closes the browser or restarts the stack, and finds the session exactly as left. Sessions can be renamed and deleted. The REST API is fully described by the generated OpenAPI document.

**Blocked by:** T-01

**Delivers stories:** US-1, US-2, US-3, US-4

**Status:** done

- [x] Session routes behave as S3.1–S3.5, including `422`, `404` and idempotent delete; every error uses the S3.6 shape.
- [x] `DesignState` extends `CopilotKitState` with the stages of S2.3; a new session's state has every S2.2 field with the initial values of S3.1 (S2.1).
- [x] The list page shows sessions newest first with name and stage, paginated by keyset cursor (S3.2, S11.1).
- [x] State is checkpointed in Postgres with thread ID equal to session ID and survives an `agent` restart (S4.2, NFR-3).
- [x] `/openapi.json` describes every route with typed models and error shapes; the frontend's REST types are generated from it (S3.7).

---

# T-03: Step 1 — clarify requirements, live on the canvas

**What to build:** The interviewer, prompted from the vendored instructions and course context, runs Step 1. It asks for users, use cases, read/write ratio, latency, availability and out-of-scope items, and records each answer as a structured item that appears on the canvas during the conversation. During Step 1 it cannot record architecture, even if asked.

**Blocked by:** T-02

**Delivers stories:** US-5, US-6, US-7, US-10, US-12

**Status:** ready-for-agent

- [ ] The design record and its Step 1 item types exist as S2.4, S2.5, S2.6, S2.7 and S2.15 define.
- [ ] The interviewer's system prompt is assembled as S5.2 defines, from `app-assets/` files.
- [ ] Backend tools record requirements, NFR targets, out-of-scope notes and estimates with IDs that are never reused, executed by the `design_tools` node (S5.1, S5.3).
- [ ] A graph-seam test shows that asking to "add a Redis cache" during Step 1 records nothing architectural (S5.4).
- [ ] Estimates keep their formula as well as their result (S2.7).
- [ ] The canvas shows Step 1 panels with item IDs, updating live (S11.2, S11.3).

---

# T-04: Step confirmation gate and per-step critique

**What to build:** When the interviewer thinks a step is complete, an approval card appears summarizing it. Approving advances the session and produces a three-part critique; rejecting with a reason keeps the session on the step. A stage tracker in the header shows progress.

**Blocked by:** T-03

**Delivers stories:** US-15, US-16

**Status:** ready-for-agent

- [ ] `confirm_step` is a frontend tool rendered with `useHumanInTheLoop`; rejection requires text (S5.7, S11.4).
- [ ] Approval and rejection update state exactly as S5.7 defines.
- [ ] After each approval the `critic` stores one critique with strengths, bottlenecks and questions (S5.8, S2.8).
- [ ] Routing is a pure function of state and ends the run while a gate call is unanswered (S5.1), verified through the graph seam.
- [ ] The header shows the stage tracker with current and confirmed steps (S11.2).

---

# T-05: Step 2 — data model, API contracts and storage choices

**What to build:** In Step 2 the interviewer captures entities, relationships, keys, endpoints and storage choices on the canvas. Every storage choice starts as "proposed" and becomes "decided" only after the user justifies it with workload facts.

**Blocked by:** T-04

**Delivers stories:** US-8, US-11

**Status:** ready-for-agent

- [ ] Entity, relationship, endpoint and storage-choice types and tools exist as S2.7 and S5.3 define.
- [ ] A graph-seam test shows "I'll use Cassandra" alone leaves the choice `proposed` and prompts a justification question; a justification naming a valid basis makes it `decided` (S5.5).
- [ ] Rejected alternatives are recorded with the choice (S2.7).
- [ ] The canvas shows Step 2 panels with item IDs (S11.3).

---

# T-06: Step 3a — components, data flows and the architecture diagram

**What to build:** In Step 3 the interviewer records components and read/write flows, and the canvas draws an architecture diagram that updates as the design changes. When the problem matches a reference blueprint, the interviewer names the pattern and its key technique as something to consider.

**Blocked by:** T-05

**Delivers stories:** US-14, US-17

**Status:** ready-for-agent

- [ ] Component and flow types and tools exist (S2.7, S5.3).
- [ ] A pure function produces Mermaid source as S11.3 defines; the same input gives the same output.
- [ ] The diagram panel renders it and shows the source in a collapsible block (S11.3).
- [ ] The course context in the interviewer prompt carries the three blueprints, and the interviewer frames them as patterns to consider (S5.2, FR-10).

---

# T-07: Step 3b — CAP stance, cache policies and the failure-mode gate

**What to build:** Still in Step 3, the interviewer records the CAP stance and cache policies and asks at least one failure-mode question. Step 3 cannot be confirmed until a failure mode exists; the attempt explains what is missing instead of opening the card.

**Blocked by:** T-06

**Delivers stories:** US-9

**Status:** ready-for-agent

- [ ] CAP stance, cache-policy and failure-mode types and tools exist (S2.7, S5.3).
- [ ] Confirming Step 3 with no failure mode returns the blocker as a tool result and opens no card (S5.6).
- [ ] The canvas shows the CAP, cache and failure-mode panels (S11.3).

---

# T-08: Steps 4–5 and the final scorecard

**What to build:** Step 4 captures SPOFs with mitigations and observability signals; Step 5 captures trade-offs and extensions. Step 4 cannot be confirmed while any SPOF lacks a mitigation. When Step 5 is confirmed, the user gets a scorecard across the five evaluation dimensions, and the session moves to design review.

**Blocked by:** T-07

**Delivers stories:** US-16

**Status:** ready-for-agent

- [ ] SPOF, signal, trade-off and extension types and tools exist (S2.7, S5.3).
- [ ] Confirming Step 4 with no SPOF, or an unmitigated SPOF, returns the blocker and opens no card (S5.6).
- [ ] After Step 5 approval the critic stores a scorecard with five dimension scores, quoted evidence and advice, and sets `stage` to `design_review` (S5.8, S2.8).
- [ ] The scorecard is shown in the workspace.

---

# T-09: Direct canvas edits the interviewer notices

**What to build:** The user can add, edit and delete any item on any canvas panel. Invalid edits are rejected with a visible reason and the old value is kept. On its next turn the interviewer acknowledges the edits by item ID.

**Blocked by:** T-08

**Delivers stories:** US-13

**Status:** ready-for-agent

- [ ] Every canvas panel supports add, edit and delete through `agent.setState` (S11.3).
- [ ] Writes are validated as S2.15 defines; an invalid write keeps the old state and sets `last_error`.
- [ ] New items get IDs per S2.5; deleted IDs are never reused.
- [ ] A graph-seam test shows the next interviewer call receives a note naming the edited IDs, and that `agent_design` tracks the interviewer's own writes (S5.9).

---

# T-10: Design review on the review model

**What to build:** After Step 5, three reviewers on the separate review model check the design in parallel for security, efficiency and maintainability. A merge step produces the gap register, shown in its own panel with each gap's lens, severity, affected items, risk and decision needed. When the review model equals the interview model, a persistent warning says the cross-model check is not active.

**Blocked by:** T-08

**Delivers stories:** US-18, US-19, US-20, US-23

**Status:** ready-for-agent

- [ ] The `Gap` type exists as S2.9 defines.
- [ ] The three reviewer nodes run in parallel on the review-role model with the inputs of S6.1, the checklists of S6.2 and the rules and severity definitions of S6.3.
- [ ] The `gap_merger` drops findings that cite no existing item, combines duplicates keeping the higher severity, and issues `GAP` IDs (S6.4).
- [ ] A graph-seam test with a scripted review model shows a finding that proposes a new component produces no design item and no requirement (S6.3, G3).
- [ ] Zero gaps sends the session to `prd_draft`; otherwise to `gap_resolution` (S6.4).
- [ ] Tokens are counted under the `review` role (S13.3).
- [ ] The gap register panel and the same-model warning render as S11.2 and S6.6 define.

---

# T-11: Gap resolution — answer or accept

**What to build:** The user goes through the gap register in a card, answering gaps or accepting them as open risks, or accepting all at once. Answers go to the interviewer, which records them as ordinary design items and marks each gap resolved. When no gap is open, the session moves to PRD drafting.

**Blocked by:** T-10

**Delivers stories:** US-21, US-22

**Status:** ready-for-agent

- [ ] `decide_gaps` is a frontend tool with per-gap decisions and "accept all"; answers and acceptances require text where S11.4 says so.
- [ ] Accepted gaps get `status` `accepted` and the note; answered gaps are recorded through design tools and closed with `resolve_gap`, filling `resolved_by` (S6.5, S5.3).
- [ ] The review does not re-run; `stage` becomes `prd_draft` when no gap is open (S6.5).

---

# T-12: PRD v1.0 — draft, sign-off and first download

**What to build:** The agent drafts a full PRD from the design record and gap register: problem, goals, users, features grouping the requirements, requirements copied verbatim, scope, and open gaps with their features. The user reviews it in a PRD viewer and signs it off, or rejects it with a reason until it is right. Once signed off, v1.0 is frozen and downloadable as Word.

**Blocked by:** T-11

**Delivers stories:** US-24, US-25, US-26, US-27, US-36

**Status:** ready-for-agent

- [ ] `PrdDoc`, `Feature`, `PrdRequirement`, `PrdNfr` and `PrdVersion` exist as S2.10 and S2.12 define.
- [ ] The `prd_drafter` behaves as S7.1 defines; a graph-seam test shows FR and NFR statements in the draft are byte-identical to the design record.
- [ ] Validation and its one retry behave as S7.2 defines.
- [ ] `sign_off_prd` approval and rejection behave as S7.3 and S7.4 define; a signed-off version is never modified.
- [ ] The PRD viewer shows the draft and every version with a version switcher (S11.2).
- [ ] The download listing and file routes of S10.3 exist, backed by pure renderers (S10.1); `prd-v1.0.docx` renders as S10.4 defines and is `409` before sign-off.
- [ ] The file opens without a repair prompt in Word 365, LibreOffice 24+ and Google Docs (NFR-11).

---

# T-13: PRD v1.1 with `to-spec`, and seam approval

**What to build:** After sign-off, the `to-spec` method extends the PRD with a solution, user stories traced to requirements and features, implementation decisions and further notes, without touching signed-off sections. The agent proposes test seams; once the user approves them, v1.1 is frozen and downloadable.

**Blocked by:** T-12

**Delivers stories:** US-28, US-29, US-31, US-36

**Status:** ready-for-agent

- [ ] The `spec_synthesizer` prompt and output behave as S8.1 defines, using `app-assets/to-spec.md` verbatim.
- [ ] A graph-seam test shows the signed-off sections of `prd_draft` are byte-identical to v1.0 after synthesis, and every open gap appears in further notes with its ID (S8.1).
- [ ] `UserStory` exists as S2.11 defines; validation and its one retry behave as S8.2 defines, including that every FR is covered by a story.
- [ ] `approve_seams` approve, edit and reject behave as S8.3; approval appends v1.1 and routes as S8.4 defines.
- [ ] `prd-v1.1.docx` renders as S10.4 defines and ends with the attribution line of S12.3.

---

# T-14: Proposed changes and PRD v1.2

**What to build:** When synthesis proposed changes to signed-off content, the user reviews each one in a card, approving or rejecting it, or accepting all. Approved changes produce PRD v1.2, with a table of what changed; rejected ones are dropped. With no proposals, this stage is skipped.

**Blocked by:** T-13

**Delivers stories:** US-30, US-36

**Status:** ready-for-agent

- [ ] `ProposedChange` exists as S2.13 defines.
- [ ] `review_changes` and the `change_applier` behave as S8.5 defines; no v1.2 is created when every change is rejected.
- [ ] A graph-seam test shows v1.0 and v1.1 are unchanged after v1.2 is created, and later stages read v1.2 as the current PRD (S2.12, S8.6).
- [ ] `prd-v1.2.docx` renders with its "Changes from v1.1" table (S10.4).

---

# T-15: Tickets with `to-tickets` and the review loop

**What to build:** The `to-tickets` method breaks the current PRD into tracer-bullet tickets with blocking edges and acceptance criteria, with open gaps kept out of its input. The user approves the breakdown or asks for changes in plain words until it is right. A cyclic breakdown is never shown as valid.

**Blocked by:** T-13

**Delivers stories:** US-32, US-33, US-34, US-35

**Status:** ready-for-agent

- [ ] The `ticket_planner` prompt is built as S9.1 defines, using `app-assets/to-tickets.md` verbatim; a graph-seam test shows the planner's input contains no gap text.
- [ ] `Ticket` exists as S2.14 defines; validation and its one retry behave as S9.2 defines.
- [ ] The `dag_validator` rejects unknown blockers, duplicates and cycles, naming the cycle, and renumbers valid tickets topologically (S9.3).
- [ ] `review_tickets` approve and revise behave as S9.4 defines; approval sets `tickets_approved_at` and `stage` `complete`.
- [ ] The ticket view shows the breakdown with blocking edges (S11.2).

---

# T-16: Requirements.docx and UserStories.docx

**What to build:** Once tickets are approved, the user can download a requirements document with coverage and a gap appendix, and a user-stories document with stories by feature, tickets with acceptance criteria, and build waves.

**Blocked by:** T-15

**Delivers stories:** US-37, US-38, US-53

**Status:** ready-for-agent

- [ ] `requirements.docx` renders as S10.5 defines from the current PRD.
- [ ] `user-stories.docx` renders as S10.6 defines, with build waves computed from the blocking edges.
- [ ] Both are `409` before `stage` is `complete` (S10.3).
- [ ] Both open without repair prompts in Word 365, LibreOffice 24+ and Google Docs (NFR-11).

---

# T-17: The Jira hand-off — context.md

**What to build:** Once tickets are approved, the user can download context.md: a self-contained prompt any agent can follow to create the Jira issues, with an editable mapping table, hard rules against adding anything, the embedded features, stories, tickets and open gaps, and a required report format.

**Blocked by:** T-15

**Delivers stories:** US-39, US-40, US-41, US-42

**Status:** ready-for-agent

- [ ] `context.md` follows the six-part template of S10.7 in order, with the default mapping rows exactly as listed.
- [ ] Every feature, story and ticket of the current PRD and breakdown appears with every field; every open gap appears under its feature (S10.7, S7.1).
- [ ] The rules include every stop-and-ask condition in S10.7, including the existing-issue check.
- [ ] The file ends with the attribution line of S12.3.
- [ ] An export-seam test compares a rendered context.md for a fixture session against a checked-in expected file, byte for byte.

---

# T-18: Completion view, zip and deterministic downloads

**What to build:** When the session completes, a completion view lists every document with a "Download all (.zip)" action. Every download is byte-identical across renders of the same state, and generating all of them is fast.

**Blocked by:** T-14, T-16, T-17

**Delivers stories:** US-43, US-44, US-45

**Status:** ready-for-agent

- [ ] The completion view renders from the S10.3 listing (S11.5), and the `completer` posts the downloads message (S9.4).
- [ ] `bundle.zip` contains every available kind except itself, with the file names of S10.2 (S10.8).
- [ ] Rendering every kind twice from the same state yields byte-identical files, Word documents and zip included (S10.9, FR-28).
- [ ] With a 50-ticket fixture, generating `bundle.zip` takes at most 10 s at p95 over 20 runs, and each download logs `export_ms` (NFR-2, S13.5).

---

# T-19: Resilience, token budget and structured logs

**What to build:** When a provider throttles, errors or times out, the app retries quietly; only if retries fail does the user see an alert with a retry button, and state is never half-written. A token meter shows use per model role and warns at 80 %; at 100 % no further model calls are made. Logs are structured JSON with per-node, per-role latency and tokens, and never contain secrets.

**Blocked by:** T-04

**Delivers stories:** US-45, US-46, US-47, US-48, US-50

**Status:** ready-for-agent

- [ ] Model calls retry as S13.1 defines; after exhausted retries only `last_error` changes (S13.2), proven through the graph seam with a failing fake model.
- [ ] Token accounting per role, the budget stop and the usage estimate behave as S13.3 defines.
- [ ] Structured output falls back from JSON-schema mode to tool calling as S13.4 defines.
- [ ] The error alert, Retry action and per-role token meter behave as S11.6 defines.
- [ ] Logs follow S13.5, including `role`, `ttft_ms` and `export_ms`; LangSmith tracing toggles by variable.
- [ ] A test scans log output, the web bundle and every download kind for both configured key values and finds none (S1.5, NFR-6).

---

# T-20: Accessibility audit and end-to-end smoke test

**What to build:** Every screen, panel and card is usable by keyboard and screen reader and meets WCAG 2.1 AA. One Playwright test drives a short session through the full stack with scripted fake models, from creating a session to downloading the zip, and five sessions run concurrently with independent state.

**Blocked by:** T-09, T-18, T-19

**Delivers stories:** US-49, US-54

**Status:** ready-for-agent

- [ ] Every interactive element is keyboard-operable with an accessible name and meets AA contrast in both themes (S11.7).
- [ ] An automated accessibility scan of the session list, the workspace in each stage panel, every gate card and the completion view reports no AA violations.
- [ ] The Playwright smoke test passes end to end and downloads a zip containing every available kind (S10.8).
- [ ] Five sessions driven concurrently with the fake models all complete with correct, independent state (NFR-12).
