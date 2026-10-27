# PRD — Blueprint Studio

> **Source:** Synthesized with the `to-spec` method (mattpocock-skills 1.2.3, MIT, © 2026 Matt Pocock) from the planning conversation and the grill session that followed it (decisions locked 2026-10-14). No interview beyond those.
> **Status:** Approved scope.
> **ID scheme:** goals `G#`, features `F-#`, functional requirements `FR-#`, non-functional requirements `NFR-#`, user stories `US-#`, decisions `D#`, non-goals `NG#`, open questions `OQ-#`. IDs are stable; append, never renumber.

---

## Problem Statement

Engineers who design systems, whether for an interview or for a real product, work without a partner that enforces structure. They draw boxes before fixing requirements, pick tools out of habit instead of from workload numbers, and describe happy paths while ignoring security, efficiency and maintainability. The design survives only as scattered notes.

Turning that design into a signed-off PRD, user stories and implementable tickets is a second manual job that most people skip or do badly. When tickets do reach a tracker such as Jira, whoever creates them, a person or an agent, tends to add features, stories and tickets nobody agreed to. The delivered work then drifts from the design.

## Solution

Blueprint Studio is a web app in which a user designs a system together with an AI agent, built with CopilotKit and LangGraph (Python), that can run on any capable model.

1. **Interview.** The agent's instructions are the project's system-design interviewer instructions plus the course context (`sse_context.md`). It walks the user through the five framework steps: clarify requirements; data and API layer; high-level architecture; scale, bottlenecks and reliability; trade-offs and extensions. It records every answer as structured data on a live canvas. Each step closes only when the user confirms it.
2. **Design review.** A *separate review model* checks the whole design through three lenses (security, efficiency and maintainability) and produces a gap register. It flags gaps and never adds scope. The user resolves each gap or accepts it as an open risk.
3. **PRD v1.0.** The agent drafts a full PRD, covering problem, goals, users, features, functional and non-functional requirements, scope, and open gaps. The user signs it off.
4. **PRD v1.1.** The `to-spec` method adds the solution, user stories, implementation decisions and testing decisions. Signed-off sections are copied word for word. Any change to signed-off content is proposed, approved by the user, and produces v1.2.
5. **Tickets.** The `to-tickets` method breaks the work into tracer-bullet tickets with blocking edges, and loops with the user until the breakdown is approved.
6. **Downloads.** The finished session offers PRD v1.0.docx, PRD v1.1.docx (and v1.2.docx when changes were approved), Requirements.docx and UserStories.docx. It also offers **context.md**, a self-contained prompt that any agent can follow to create Jira issues using only the approved features, stories and tickets.

## Goals

- **G1** — Make a design session follow the five-step framework in order, with explicit confirmation at each step.
- **G2** — Make every output traceable: every story traces to a requirement and a feature, and every ticket to a story.
- **G3** — Eliminate scope creep after sign-off: nothing reaches the tickets or Jira that the user did not say or approve.
- **G4** — Surface security, efficiency and maintainability gaps before sign-off, judged by a model other than the one that ran the interview.
- **G5** — Teach while designing: feedback names the evaluation dimension it serves and quotes the evidence.

## Features

| ID | Feature | Functional requirements |
|---|---|---|
| F-1 | Sessions | FR-1 |
| F-2 | Guided interview | FR-2 to FR-10 |
| F-3 | Design review | FR-11 to FR-14 |
| F-4 | PRD drafting and sign-off | FR-15 to FR-17 |
| F-5 | Spec and ticket synthesis | FR-18 to FR-22 |
| F-6 | Documents and Jira hand-off | FR-23 to FR-29 |
| F-7 | Platform qualities | NFR-1 to NFR-13 |
| F-8 | Document import | FR-30 to FR-35 |

## Functional Requirements

| ID | Feature | Requirement |
|---|---|---|
| FR-1 | F-1 | The user can create, name, rename, list, resume and delete design sessions. |
| FR-2 | F-2 | The interviewer's system prompt is built from the vendored project instructions and course context. It runs the five framework steps in order and records no components, flows, endpoints or storage choices until Step 1 is confirmed. |
| FR-3 | F-2 | When the user names a technology, the interviewer asks for a justification based on read/write ratio, consistency need, latency or throughput before recording the choice as decided. |
| FR-4 | F-2 | In Steps 3 and 4 the interviewer asks at least one failure-mode question and records the answer. Step 3 cannot be confirmed without a failure mode; Step 4 cannot be confirmed while any SPOF lacks a mitigation. |
| FR-5 | F-2 | The session holds a structured design record: functional requirements, non-functional targets with units, out-of-scope items, capacity estimates with formulas, entities and relationships, API endpoints, storage choices with justifications, components, read and write flows, the CAP stance, cache policies, SPOFs, failure modes, observability signals, trade-offs and extensions. Every item has a stable ID. |
| FR-6 | F-2 | A canvas shows the design record live. The user can add, edit and delete any item, and the interviewer acknowledges those edits by ID on its next turn. |
| FR-7 | F-2 | Moving to the next step requires the user to confirm the current step in an approval card; rejecting it requires a reason, and the interviewer continues the step. |
| FR-8 | F-2 | The canvas renders an architecture diagram generated from the recorded components and flows. |
| FR-9 | F-2 | After each confirmed step the interviewer gives a three-part critique (🟢 Strengths & Alignment, ⚠️ Bottlenecks & Unaddressed Trade-Offs, ❓ Probing / Next-Step Questions). After Step 5 it gives a scorecard across the five evaluation dimensions, each score backed by quoted evidence. |
| FR-10 | F-2 | When the design matches a reference blueprint (media streaming, reservations, real-time messaging), the interviewer names the pattern and its technique as something to consider, not as an answer. |
| FR-11 | F-3 | After Step 5 is confirmed, three reviewers running on the review model check the whole design record in parallel, one each for security, efficiency and maintainability. A merge step on the review model combines their findings into one gap register. |
| FR-12 | F-3 | Each gap has an ID (`GAP-n`), a lens, the IDs of the design items it concerns, the risk, the decision needed, and a severity (high, medium or low). A gap that cites no existing item is discarded. The review never adds features, requirements or design items, and never recommends a solution. |
| FR-13 | F-3 | For each gap the user either answers it, and the interviewer records the answer as ordinary design items, or accepts it as an open risk with an optional note. PRD drafting waits until every gap is resolved or accepted. |
| FR-14 | F-3 | When the review model is configured to be the same model as the interview model, the review still runs, and the workspace shows a persistent warning that the cross-model check is not active. |
| FR-15 | F-4 | Once all gaps are settled, the agent drafts PRD v1.0 from the design record and gap register. It contains: problem statement, goals, users and stakeholders, features, functional requirements, non-functional requirements, scope and out-of-scope, and "Open gaps and accepted risks". |
| FR-16 | F-4 | Every functional requirement belongs to exactly one feature, and every feature groups at least one functional requirement. |
| FR-17 | F-4 | The user signs off PRD v1.0 in an approval card, or rejects it with a reason; the agent revises and re-presents until it is signed off. A signed-off version is frozen. |
| FR-18 | F-5 | The `to-spec` method produces PRD v1.1: the signed-off v1.0 sections copied word for word, plus a solution, a long list of user stories, implementation decisions, testing decisions and further notes. Open gaps appear verbatim in further notes. Every story traces to at least one FR or NFR and belongs to exactly one feature. |
| FR-19 | F-5 | If synthesis finds that signed-off content should change, it does not edit it. It lists each change under "Proposed changes", and the user approves or rejects each one. Approved changes produce PRD v1.2; rejected ones are dropped. |
| FR-20 | F-5 | Before PRD v1.1 is final, the user approves or edits the proposed test seams, following `to-spec`'s seam check. |
| FR-21 | F-5 | The `to-tickets` method produces vertical-slice tickets, each with a title, what to build, blocking edges, acceptance criteria and at least one story. Every story is covered by at least one ticket. No ticket is created from an open gap. |
| FR-22 | F-5 | The user approves the ticket breakdown, or asks to merge, split or re-edge tickets in plain words, and the breakdown is regenerated until approved. A breakdown with a dependency cycle is rejected and the cycle is named. |
| FR-23 | F-6 | PRD v1.0.docx is downloadable once signed off; PRD v1.1.docx once seams are approved; PRD v1.2.docx once proposed changes are approved. Every version stays downloadable. |
| FR-24 | F-6 | Requirements.docx lists the functional and non-functional requirements with their features and the stories that cover each one, plus an appendix of open gaps and accepted risks. |
| FR-25 | F-6 | UserStories.docx lists the stories grouped by feature, each with its tickets; then every ticket with acceptance criteria and blocking edges; then the build waves. |
| FR-26 | F-6 | context.md is a self-contained prompt that any agent can follow to create Jira issues. It opens with an editable mapping table whose default is: Feature → Epic; User story → Story under its feature's Epic; Ticket → Task under the Epic of its first story, with "relates to" links to every story it delivers and "is blocked by" links to its blockers. It embeds every feature, story and ticket. It instructs the agent to create exactly those issues, to add none, to paste each open gap into the description of the affected Epic as text, to stop and ask when anything is ambiguous, and to return a table mapping every F-, US- and T- ID to its Jira key. |
| FR-27 | F-6 | When the tickets are approved, the session shows a completion view listing every document, each downloadable alone or all together as one zip. |
| FR-28 | F-6 | Exports are deterministic: rendering the same state twice produces byte-identical files of every kind. |
| FR-29 | F-6 | Requirements.docx, UserStories.docx and context.md are rendered from session data, with no model call during export, so they cannot disagree with the PRD. |
| FR-30 | F-8 | In the interview stage the user can attach `.md`, `.txt`, `.pdf`, `.docx`, `.mmd`, `.drawio` and image files to a session, within the published limits; images only when the interview model can read them. |
| FR-31 | F-8 | The agent maps each attachment onto the design record as candidates, each quoting its source. A candidate that quotes text not in the file, or that does not fit its list's schema, is discarded. |
| FR-32 | F-8 | The user accepts, edits or rejects each candidate in an approval card before it is recorded; nothing from a file is recorded otherwise. |
| FR-33 | F-8 | Candidates for a step after the current one wait until that step opens; the scope-first rule of FR-2 applies to imported items. |
| FR-34 | F-8 | The interviewer asks about each weakness and document-level ambiguity, quoting the document, before the user confirms the step. |
| FR-35 | F-8 | Every recorded item that came from a file shows its source; PRD-level excerpts feed the PRD draft. |

## Non-Functional Requirements

Targets marked *(proposed)* are not yet agreed; see Open Questions.

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Latency | The first streamed token of an interviewer reply appears within 3 s at p95, measured at the client, excluding provider outages. *(proposed)* |
| NFR-2 | Latency | Generating all downloads for a session with up to 50 tickets takes at most 10 s at p95. *(proposed)* |
| NFR-3 | Durability | Session state survives a backend restart. No confirmed step, resolved gap, signed-off PRD version or approved breakdown is lost. |
| NFR-4 | Cost | Each session has a configurable token budget covering both models. The app warns at 80 % and blocks new model calls at 100 %. Default 2,000,000 tokens. *(proposed)* |
| NFR-5 | Resilience | Model-provider errors (HTTP 429, 5xx, timeouts) are retried with exponential backoff up to 3 times, then shown with a retry action. A failed call never leaves state half-written. |
| NFR-6 | Security | Provider API keys live only on the server. No secret appears in the client bundle, logs or any download. |
| NFR-7 | Accessibility | The canvas, approval cards, gap register and downloads view meet WCAG 2.1 AA and are fully keyboard-operable. |
| NFR-8 | Observability | Logs are structured JSON with session ID, graph node, model role and latency. Token use is recorded per node and per model role. LangSmith tracing can be switched on by environment variable. |
| NFR-9 | Portability | The whole system runs locally with one `docker compose up` and one `.env` file. |
| NFR-10 | Configurability | The app is model-agnostic. The interview model and the review model are configured separately (provider, model name, base URL, key). Any OpenAI-compatible Chat Completions endpoint works, and Anthropic is supported natively. Both models must support tool calling and structured output, and the app checks both at startup. |
| NFR-11 | Compatibility | Every .docx opens without a repair prompt in Microsoft Word 365, LibreOffice 24 or later, and Google Docs. |
| NFR-12 | Scale | Single-user, self-hosted. One instance supports at least 5 concurrent sessions. Multi-tenancy is not required. |
| NFR-13 | Licensing | Vendored third-party prompt text (`to-spec`, `to-tickets`) is used verbatim with its MIT licence and attribution, both in the repository and in documents derived from it. |

## User Stories

Actors: **engineer** (the person using the app), **candidate** (an engineer practising for an interview), **tech lead** (an engineer planning a real system for a team), **operator** (whoever self-hosts the app), **ticketing agent** (the agent that receives context.md).

**F-1 Sessions**
1. **US-1** — As an engineer, I want to start a new design session with a name, so that I can keep separate designs apart. *(FR-1)*
2. **US-2** — As an engineer, I want to see my sessions with their current stage, so that I can pick up where I left off. *(FR-1)*
3. **US-3** — As an engineer, I want to resume a session after closing the browser or a server restart, so that I never lose confirmed work. *(FR-1, NFR-3)*
4. **US-4** — As an engineer, I want to rename and delete sessions, so that my list stays useful. *(FR-1)*

**F-2 Guided interview**
5. **US-5** — As a candidate, I want the interviewer to refuse to draw architecture until my requirements are clear, so that I practise scoping first the way real interviews reward. *(FR-2)*
6. **US-6** — As a candidate, I want to be asked for users, read/write ratio, latency and availability targets, so that my design rests on numbers. *(FR-2, FR-5)*
7. **US-7** — As an engineer, I want to state what is out of scope and see it recorded, so that later stages do not drift into it. *(FR-5)*
8. **US-8** — As a candidate, I want to be asked to justify every technology I name, so that I learn to defend choices with workload facts. *(FR-3)*
9. **US-9** — As a candidate, I want failure-mode questions in the architecture and reliability steps, so that I practise thinking beyond the happy path. *(FR-4)*
10. **US-10** — As an engineer, I want capacity estimates recorded with their arithmetic, so that anyone can check them. *(FR-5)*
11. **US-11** — As an engineer, I want entities, relationships, endpoints and storage choices captured as structured data, so that the PRD states them exactly. *(FR-5)*
12. **US-12** — As an engineer, I want to watch the canvas update as I talk, so that I can verify the agent understood me. *(FR-6)*
13. **US-13** — As an engineer, I want to edit or delete any canvas item directly, and have the interviewer notice, so that chat and canvas never disagree. *(FR-6)*
14. **US-14** — As an engineer, I want an architecture diagram drawn from my components and flows, so that I see the system without drawing it by hand. *(FR-8)*
15. **US-15** — As an engineer, I want to confirm each step in an approval card, or reject it with a reason, so that the interview advances only when I agree. *(FR-7)*
16. **US-16** — As a candidate, I want a three-part critique after each step and a scorecard at the end, so that I know exactly where to improve. *(FR-9)*
17. **US-17** — As an engineer, I want the interviewer to name a matching reference blueprint, so that I learn the proven technique without being handed the answer. *(FR-10)*

**F-3 Design review**
18. **US-18** — As a tech lead, I want a second model to review the design for security, efficiency and maintainability, so that blind spots shared with the interviewer's model are caught. *(FR-11, G4)*
19. **US-19** — As a tech lead, I want every gap to name the affected design items, the risk and the decision needed, so that I can act on it without guessing. *(FR-12)*
20. **US-20** — As a tech lead, I want the review to flag gaps without inventing features or solutions, so that the plan stays mine. *(FR-12, G3)*
21. **US-21** — As an engineer, I want to answer a gap and see the answer recorded as design items, so that it flows into the PRD and tickets like everything else. *(FR-13)*
22. **US-22** — As an engineer, I want to accept a gap as an open risk with a note, so that I can move on knowingly. *(FR-13)*
23. **US-23** — As an operator, I want a visible warning when the review model is the same as the interview model, so that I know the cross-model check is not active. *(FR-14, NFR-10)*

**F-4 PRD drafting and sign-off**
24. **US-24** — As a tech lead, I want a full PRD drafted from the design and gap register, so that I have a document to sign off before any planning. *(FR-15)*
25. **US-25** — As a tech lead, I want requirements grouped into features, so that the plan and Jira have a clear top level. *(FR-15, FR-16)*
26. **US-26** — As a tech lead, I want to sign off or reject the PRD with a reason until it is right, so that the baseline is something I agreed to. *(FR-17)*
27. **US-27** — As a tech lead, I want open gaps and accepted risks listed in the PRD I sign, so that sign-off is informed. *(FR-15)*

**F-5 Spec and ticket synthesis**
28. **US-28** — As a tech lead, I want `to-spec` to extend the signed-off PRD without changing it, so that sign-off stays meaningful. *(FR-18)*
29. **US-29** — As a tech lead, I want every user story to name its requirements and its feature, so that coverage can be checked. *(FR-18, G2)*
30. **US-30** — As a tech lead, I want proposed changes to signed-off content listed for my approval one by one, so that nothing changes behind my back. *(FR-19, G3)*
31. **US-31** — As a tech lead, I want to approve or edit the test seams, so that testing is planned at the right level. *(FR-20)*
32. **US-32** — As a tech lead, I want tracer-bullet tickets with blocking edges and acceptance criteria, so that each ticket is demoable and the build order is clear. *(FR-21)*
33. **US-33** — As a tech lead, I want to merge, split or re-edge tickets in plain words and see the breakdown regenerated, so that the granularity fits my team. *(FR-22)*
34. **US-34** — As a tech lead, I want a cyclic breakdown rejected with the cycle named, so that the plan is always buildable. *(FR-22)*
35. **US-35** — As a tech lead, I want open gaps kept out of the tickets, so that unagreed work never reaches the board. *(FR-21, G3)*

**F-6 Documents and Jira hand-off**
36. **US-36** — As a tech lead, I want every PRD version as a Word document, so that I can circulate the exact version people signed. *(FR-23)*
37. **US-37** — As a stakeholder-facing engineer, I want a short requirements document with coverage and gaps, so that scope can be checked without reading the whole PRD. *(FR-24)*
38. **US-38** — As a tech lead, I want a user-stories document with tickets and acceptance criteria, so that delivery can be planned from one file. *(FR-25)*
39. **US-39** — As a tech lead, I want a context.md I can hand to any agent, so that Jira issues are created without me typing them. *(FR-26)*
40. **US-40** — As a tech lead, I want to edit the Jira mapping table before handing context.md over, so that it fits my Jira configuration. *(FR-26)*
41. **US-41** — As a ticketing agent, I want one closed list of features, stories and tickets with explicit rules, so that I create exactly what was approved and nothing else. *(FR-26, G3)*
42. **US-42** — As a ticketing agent, I want instructions for ambiguity and a required report format, so that I stop and ask instead of guessing, and the user can verify my work. *(FR-26)*
43. **US-43** — As an engineer, I want a completion view with every file and a zip of all of them, so that I can take the whole package in one step. *(FR-27)*
44. **US-44** — As an engineer, I want identical downloads when nothing has changed, so that version control shows only real changes. *(FR-28, FR-29)*

**F-7 Platform qualities**
45. **US-45** — As an engineer, I want replies to start within seconds and downloads to finish quickly, so that the tool keeps pace with me. *(NFR-1, NFR-2)*
46. **US-46** — As an engineer, I want to see token use for the session and be stopped before overspending, so that I control cost. *(NFR-4)*
47. **US-47** — As an engineer, I want a clear message and a retry button when a provider fails, so that an outage does not cost me my session. *(NFR-5)*
48. **US-48** — As an operator, I want keys kept out of the browser, logs and downloads, so that running the app cannot leak them. *(NFR-6)*
49. **US-49** — As an engineer using only a keyboard or a screen reader, I want every screen and card to work for me, so that the app is usable. *(NFR-7)*
50. **US-50** — As an operator, I want structured logs with per-node, per-model latency and tokens, so that I can diagnose slow or costly sessions. *(NFR-8)*
51. **US-51** — As an operator, I want to run everything locally with one command, so that I can self-host it. *(NFR-9)*
52. **US-52** — As an operator, I want to choose any capable model for each role, and be told at startup if one cannot call tools or return structured output, so that I am not locked to one vendor. *(NFR-10)*
53. **US-53** — As a tech lead, I want Word documents that open cleanly in Word, LibreOffice and Google Docs, so that reviewers can read them whatever they use. *(NFR-11)*
54. **US-54** — As an engineer, I want to run several sessions at once on one instance, so that I can compare alternative designs. *(NFR-12)*
55. **US-55** — As a maintainer, I want vendored prompt text kept verbatim with its licence and attribution, so that the project stays compliant. *(NFR-13)*

**F-8 Document import**
56. **US-56** — As a tech lead, I want to attach an existing PRD or spec, so that the interviewer starts from what I have already written instead of asking me again. *(FR-30, FR-31)*
57. **US-57** — As an engineer, I want to attach an architecture diagram as an image, a Mermaid file or a draw.io file, so that its components and flows reach the canvas without retyping. *(FR-30, FR-31)*
58. **US-58** — As an engineer, I want to see every item the agent pulled from a file, with the quote it came from, and accept, edit or reject each one, so that nothing reaches my design that I did not approve. *(FR-32, G3)*
59. **US-59** — As a candidate, I want material for later steps held until I reach that step, so that I still practise scoping first. *(FR-33, FR-2)*
60. **US-60** — As an engineer, I want the interviewer to ask about the parts of my document that are vague, unjustified or contradictory, quoting them, so that the design gets better rather than being copied as-is. *(FR-34)*
61. **US-61** — As an engineer, I want to see which file each recorded item came from, so that I can trace it back. *(FR-35)*
62. **US-62** — As an engineer, I want a clear reason when a file is refused (type, size, length, a model that cannot read images), so that I know what to change. *(FR-30)*

## Implementation Decisions

- **D1 — Agent backend.** Python with FastAPI and a LangGraph `StateGraph`, exposed over AG-UI with `add_langgraph_fastapi_endpoint` (package `ag-ui-langgraph`) wrapping `LangGraphAGUIAgent` (package `copilotkit`).
- **D2 — Frontend and runtime.** Next.js with CopilotKit's v2 React API (`@copilotkit/react-core/v2`: `CopilotKit`, `CopilotChat`, `useAgent`, `useHumanInTheLoop`). A Next.js route hosts `CopilotRuntime` (`@copilotkit/runtime/v2`) with an `HttpAgent` (`@ag-ui/client`) proxying to FastAPI. CopilotKit's documentation reports that pointing `runtimeUrl` directly at FastAPI fails with `runtime_info_fetch_failed`.
- **D3 — One state, one source of truth.** A single `DesignState`, extending `CopilotKitState`, holds the whole session: design record, gap register, PRD versions, spec, seams, tickets, approvals, budget. The frontend reads it through `useAgent().agent.state` and writes canvas edits through `agent.setState`.
- **D4 — Stage machine.** `interview → design_review → gap_resolution → prd_draft → prd_signoff → spec_synthesis → seam_gate → change_review → ticket_breakdown → ticket_gate → complete`. `change_review` is skipped when synthesis proposes no changes. Transitions depend only on state; routing is a pure function.
- **D5 — Approval gates are frontend tools.** Step confirmation, gap decisions, PRD sign-off, change review, seam approval and ticket review are tools rendered with `useHumanInTheLoop`, not LangGraph `interrupt()`. CopilotKit's documentation contradicts itself on Python interrupt support (OQ-1); frontend tools are documented as working.
- **D6 — Structured output.** Review findings, the merged gap register, PRD v1.0, the v1.1 additions, proposed changes and tickets are all produced with Pydantic output schemas, so documents are rendered from typed data, never parsed from prose.
- **D7 — Pure exports.** Every download is a pure function of session state. PRD versions are stored as immutable snapshots at the moment of approval, so a v1.0 download never changes after sign-off.
- **D8 — Vendored runtime prompts.** The app ships `app-assets/` as package data: the interviewer instructions, the course context, and `to-spec` and `to-tickets` verbatim from mattpocock-skills 1.2.3 with the MIT licence. They are runtime prompt data for the app's agent, not development skills. Deliberate deviations from the two methods: no issue-tracker publishing; `to-spec` writes into PRD v1.1 rather than a tracker issue; `to-spec`'s seam check and `to-tickets`' quiz become UI approval gates.
- **D9 — Two model roles.** One factory builds every chat model through LangChain's `init_chat_model`, with two independently configured roles: `interview` (interviewer, critic, PRD drafting, `to-spec`, `to-tickets`) and `review` (the three lens reviewers and the merge step). No other module imports a provider SDK.
- **D10 — Persistence.** `langgraph-checkpoint-postgres` stores graph state with the thread ID equal to the session ID. A `sessions` table holds name, timestamps and stage for listing.
- **D11 — Word and Markdown generation.** python-docx renders the Word files; Markdown is rendered from templates. Document timestamps come from approval times, never from the clock at export time, so FR-28 holds.
- **D12 — Diagram.** Mermaid source generated deterministically from components and flows, rendered in the browser.
- **D13 — Pinned baseline (2026-10-14).** Python 3.14 (3.15 shipped on 2026-10-09, but `ormsgpack`, required by LangGraph's checkpointer, has no cp315 wheel yet). Python packages: `langgraph` 1.2.15, `langchain` 1.4.6, `langchain-openai` 1.7.2, `langchain-anthropic` 1.7.6, `copilotkit` 0.1.96, `ag-ui-langgraph` 0.0.47, `langgraph-checkpoint-postgres` 3.1.3, `fastapi` 0.143.1, `python-docx` 1.2.0. Node 24 LTS with TypeScript 7.0.2 (supported in `next build` since Next.js 16.3), `next` 16.4.1, `@copilotkit/react-core`, `@copilotkit/react-ui` and `@copilotkit/runtime` 1.79.0, `@ag-ui/client` 1.0.2.
- **D14 — Published REST contract.** The session and download API is described by FastAPI's generated OpenAPI 3.1 document at `/openapi.json`; the frontend's REST types are generated from it.

- **D15 — Document import.** Files are read deterministically in the agent (no model) into quotable sections, stored in an `attachments` table outside the checkpoint, and mapped onto the design record by one structured call on the interview role. The table is the source of truth: each agent run starts by syncing it into state, so the browser never writes attachments.
- **D16 — Imports reuse the interview's tools.** Accepted candidates are recorded through the same upsert tools and Step 1 restriction as the interviewer's own writes, after a new `review_import` gate.

State shape (decision-rich parts only; full field list in SPECS.md §2):

```python
class DesignState(CopilotKitState):
    session_id: str
    stage: Stage                     # D4
    current_step: int                # 1-5 during interview
    confirmed_steps: list[int]
    design: Design                   # the design record (FR-5)
    gaps: list[Gap]                  # the gap register (FR-12)
    review_model_distinct: bool      # FR-14
    prd_versions: list[PrdVersion]   # immutable snapshots: v1.0, v1.1, v1.2
    proposed_changes: list[ProposedChange]
    seams: list[Seam]
    tickets: list[Ticket]
    tokens_used: dict[str, int]      # per model role
```

## Testing Decisions

- **What makes a good test.** A test drives the system through a public seam and asserts on observable results (state, stage, downloaded files). It never asserts on prompt wording, private helpers or the order of internal calls.
- **Seams (approved in planning):**
  1. **Graph seam (primary).** Compile the real graph with two scripted fake chat models, one per role, feed user messages and gate answers, and assert on the resulting `DesignState`. This one seam covers step order, the scope-first rule, the review and gap flow, PRD sign-off and versioning, proposed changes, cycle rejection and budget enforcement.
  2. **Export seam.** Feed approved-state fixtures to the export functions and assert on the files: Markdown and zip byte for byte; .docx read back and compared by content and checked for byte identity across renders.
  3. **One end-to-end smoke test.** Playwright drives a short session through the full stack with the fake models, from session creation to zip download.
- **Prior art:** none; this is a new project.

## Out of Scope

- **NG1** — Accounts, authentication, sharing and real-time collaboration.
- **NG2** — The app creating Jira issues itself. It produces context.md; a separate agent of the user's choice creates the issues.
- **NG3** — Generating a project skeleton or any application code for the designed system.
- **NG4** — Publishing tickets to any other tracker.
- **NG5** — Voice input, native mobile apps and billing.
- **NG6** — Importing an existing design from an image or a whiteboard photo. *Superseded by F-8 (2026-10-27).*

## Further Notes

Open questions. When the build reaches one of these, stop and ask rather than guess:

- **OQ-1** — CopilotKit's human-in-the-loop page says LangGraph Python does not support interrupts, while describing `useInterrupt` as built on LangGraph's `interrupt()`. D5 avoids the question; confirm before anyone switches gates to interrupts.
- **OQ-2** — CopilotKit documents frontend-tool forwarding through `CopilotKitMiddleware` for `create_agent`. Confirm that frontend tools reach nodes of a hand-built `StateGraph`, or run the interviewer as a `create_agent` subgraph inside it.
- **OQ-3** — Confirm the proposed targets in NFR-1, NFR-2 and NFR-4.
- **OQ-4** — Small local models (for example, 7-8B models served by Ollama) often call tools unreliably. The startup check catches total failure, not flakiness. Decide whether to publish a list of tested models in the README.
- **OQ-5** — Some OpenAI-compatible servers omit token usage in streamed responses. SPECS falls back to an estimate; confirm that is acceptable for budget enforcement.
- **OQ-6** — When the critic quotes the session as evidence (FR-9), may it quote assistant turns, or only the user's?
