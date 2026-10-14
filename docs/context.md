# Jira hand-off — Blueprint Studio

## 1. Your role

You are creating Jira issues for **Blueprint Studio**. This file is your only source: every issue you create comes from it, and nothing else does. Work through the sections below in order, follow the mapping table exactly as the user has left it, and stop and ask whenever this file does not settle a question.

## 2. Jira project

- Site: 
- Project key: 

If either line is blank when you start, ask the user for it before doing anything else.

## 3. Mapping table — edit this table to match your Jira, then follow it exactly

| Concept | Jira issue type | Parent | Links |
|---|---|---|---|
| Feature (`F-n`) | Epic | — | — |
| User story (`US-n`) | Story | The Epic of its feature | — |
| Ticket (`T-nn`) | Task | The Epic of its first delivered story | "relates to" each delivered story; "is blocked by" each blocking ticket |

## 4. Rules

- Create exactly one issue per ID listed in sections 5 to 7, and nothing else: no extra issues, sub-tasks, features, stories or tickets.
- Use each item's **Summary** line as the issue summary and its remaining fields as the description, as given. Format them for Jira; do not reword them.
- Create in this order: features, then stories, then tickets in ID order, so every parent and link target exists when you need it.
- Paste each open gap (section 8) into the description of its feature's Epic, under the heading "Open gaps and accepted risks". Never create an issue for a gap.
- Before creating anything, search the project for issues whose summary starts with any ID in this file. If one exists, stop and ask.
- If an issue type or link type named in the mapping table does not exist in the project, stop and ask.
- If anything else is ambiguous, stop and ask. Never guess and never fill a gap with your own content.

## 5. Features

### F-1: Sessions

- **Summary:** F-1: Sessions
- **Requirements:**
  - FR-1: The user can create, name, rename, list, resume and delete design sessions.

### F-2: Guided interview

- **Summary:** F-2: Guided interview
- **Requirements:**
  - FR-2: The interviewer's system prompt is built from the vendored project instructions and course context. It runs the five framework steps in order and records no components, flows, endpoints or storage choices until Step 1 is confirmed.
  - FR-3: When the user names a technology, the interviewer asks for a justification based on read/write ratio, consistency need, latency or throughput before recording the choice as decided.
  - FR-4: In Steps 3 and 4 the interviewer asks at least one failure-mode question and records the answer. Step 3 cannot be confirmed without a failure mode; Step 4 cannot be confirmed while any SPOF lacks a mitigation.
  - FR-5: The session holds a structured design record: functional requirements, non-functional targets with units, out-of-scope items, capacity estimates with formulas, entities and relationships, API endpoints, storage choices with justifications, components, read and write flows, the CAP stance, cache policies, SPOFs, failure modes, observability signals, trade-offs and extensions. Every item has a stable ID.
  - FR-6: A canvas shows the design record live. The user can add, edit and delete any item, and the interviewer acknowledges those edits by ID on its next turn.
  - FR-7: Moving to the next step requires the user to confirm the current step in an approval card; rejecting it requires a reason, and the interviewer continues the step.
  - FR-8: The canvas renders an architecture diagram generated from the recorded components and flows.
  - FR-9: After each confirmed step the interviewer gives a three-part critique (🟢 Strengths & Alignment, ⚠️ Bottlenecks & Unaddressed Trade-Offs, ❓ Probing / Next-Step Questions). After Step 5 it gives a scorecard across the five evaluation dimensions, each score backed by quoted evidence.
  - FR-10: When the design matches a reference blueprint (media streaming, reservations, real-time messaging), the interviewer names the pattern and its technique as something to consider, not as an answer.

### F-3: Design review

- **Summary:** F-3: Design review
- **Requirements:**
  - FR-11: After Step 5 is confirmed, three reviewers running on the review model check the whole design record in parallel, one each for security, efficiency and maintainability. A merge step on the review model combines their findings into one gap register.
  - FR-12: Each gap has an ID (`GAP-n`), a lens, the IDs of the design items it concerns, the risk, the decision needed, and a severity (high, medium or low). A gap that cites no existing item is discarded. The review never adds features, requirements or design items, and never recommends a solution.
  - FR-13: For each gap the user either answers it, and the interviewer records the answer as ordinary design items, or accepts it as an open risk with an optional note. PRD drafting waits until every gap is resolved or accepted.
  - FR-14: When the review model is configured to be the same model as the interview model, the review still runs, and the workspace shows a persistent warning that the cross-model check is not active.

### F-4: PRD drafting and sign-off

- **Summary:** F-4: PRD drafting and sign-off
- **Requirements:**
  - FR-15: Once all gaps are settled, the agent drafts PRD v1.0 from the design record and gap register. It contains: problem statement, goals, users and stakeholders, features, functional requirements, non-functional requirements, scope and out-of-scope, and "Open gaps and accepted risks".
  - FR-16: Every functional requirement belongs to exactly one feature, and every feature groups at least one functional requirement.
  - FR-17: The user signs off PRD v1.0 in an approval card, or rejects it with a reason; the agent revises and re-presents until it is signed off. A signed-off version is frozen.

### F-5: Spec and ticket synthesis

- **Summary:** F-5: Spec and ticket synthesis
- **Requirements:**
  - FR-18: The `to-spec` method produces PRD v1.1: the signed-off v1.0 sections copied word for word, plus a solution, a long list of user stories, implementation decisions, testing decisions and further notes. Open gaps appear verbatim in further notes. Every story traces to at least one FR or NFR and belongs to exactly one feature.
  - FR-19: If synthesis finds that signed-off content should change, it does not edit it. It lists each change under "Proposed changes", and the user approves or rejects each one. Approved changes produce PRD v1.2; rejected ones are dropped.
  - FR-20: Before PRD v1.1 is final, the user approves or edits the proposed test seams, following `to-spec`'s seam check.
  - FR-21: The `to-tickets` method produces vertical-slice tickets, each with a title, what to build, blocking edges, acceptance criteria and at least one story. Every story is covered by at least one ticket. No ticket is created from an open gap.
  - FR-22: The user approves the ticket breakdown, or asks to merge, split or re-edge tickets in plain words, and the breakdown is regenerated until approved. A breakdown with a dependency cycle is rejected and the cycle is named.

### F-6: Documents and Jira hand-off

- **Summary:** F-6: Documents and Jira hand-off
- **Requirements:**
  - FR-23: PRD v1.0.docx is downloadable once signed off; PRD v1.1.docx once seams are approved; PRD v1.2.docx once proposed changes are approved. Every version stays downloadable.
  - FR-24: Requirements.docx lists the functional and non-functional requirements with their features and the stories that cover each one, plus an appendix of open gaps and accepted risks.
  - FR-25: UserStories.docx lists the stories grouped by feature, each with its tickets; then every ticket with acceptance criteria and blocking edges; then the build waves.
  - FR-26: context.md is a self-contained prompt that any agent can follow to create Jira issues. It opens with an editable mapping table whose default is: Feature → Epic; User story → Story under its feature's Epic; Ticket → Task under the Epic of its first story, with "relates to" links to every story it delivers and "is blocked by" links to its blockers. It embeds every feature, story and ticket. It instructs the agent to create exactly those issues, to add none, to paste each open gap into the description of the affected Epic as text, to stop and ask when anything is ambiguous, and to return a table mapping every F-, US- and T- ID to its Jira key.
  - FR-27: When the tickets are approved, the session shows a completion view listing every document, each downloadable alone or all together as one zip.
  - FR-28: Exports are deterministic: rendering the same state twice produces byte-identical files of every kind.
  - FR-29: Requirements.docx, UserStories.docx and context.md are rendered from session data, with no model call during export, so they cannot disagree with the PRD.

### F-7: Platform qualities

- **Summary:** F-7: Platform qualities
- **Requirements:**
  - NFR-1: The first streamed token of an interviewer reply appears within 3 s at p95, measured at the client, excluding provider outages. *(proposed)*
  - NFR-2: Generating all downloads for a session with up to 50 tickets takes at most 10 s at p95. *(proposed)*
  - NFR-3: Session state survives a backend restart. No confirmed step, resolved gap, signed-off PRD version or approved breakdown is lost.
  - NFR-4: Each session has a configurable token budget covering both models. The app warns at 80 % and blocks new model calls at 100 %. Default 2,000,000 tokens. *(proposed)*
  - NFR-5: Model-provider errors (HTTP 429, 5xx, timeouts) are retried with exponential backoff up to 3 times, then shown with a retry action. A failed call never leaves state half-written.
  - NFR-6: Provider API keys live only on the server. No secret appears in the client bundle, logs or any download.
  - NFR-7: The canvas, approval cards, gap register and downloads view meet WCAG 2.1 AA and are fully keyboard-operable.
  - NFR-8: Logs are structured JSON with session ID, graph node, model role and latency. Token use is recorded per node and per model role. LangSmith tracing can be switched on by environment variable.
  - NFR-9: The whole system runs locally with one `docker compose up` and one `.env` file.
  - NFR-10: The app is model-agnostic. The interview model and the review model are configured separately (provider, model name, base URL, key). Any OpenAI-compatible Chat Completions endpoint works, and Anthropic is supported natively. Both models must support tool calling and structured output, and the app checks both at startup.
  - NFR-11: Every .docx opens without a repair prompt in Microsoft Word 365, LibreOffice 24 or later, and Google Docs.
  - NFR-12: Single-user, self-hosted. One instance supports at least 5 concurrent sessions. Multi-tenancy is not required.
  - NFR-13: Vendored third-party prompt text (`to-spec`, `to-tickets`) is used verbatim with its MIT licence and attribution, both in the repository and in documents derived from it.

## 6. User stories

### US-1

- **Summary:** US-1: To start a new design session with a name
- **Feature:** F-1
- **Story:** As an engineer, I want to start a new design session with a name, so that I can keep separate designs apart.
- **Requirements:** FR-1
- **Delivered by:** T-02

### US-2

- **Summary:** US-2: To see my sessions with their current stage
- **Feature:** F-1
- **Story:** As an engineer, I want to see my sessions with their current stage, so that I can pick up where I left off.
- **Requirements:** FR-1
- **Delivered by:** T-02

### US-3

- **Summary:** US-3: To resume a session after closing the browser or a server restart
- **Feature:** F-1
- **Story:** As an engineer, I want to resume a session after closing the browser or a server restart, so that I never lose confirmed work.
- **Requirements:** FR-1, NFR-3
- **Delivered by:** T-02

### US-4

- **Summary:** US-4: To rename and delete sessions
- **Feature:** F-1
- **Story:** As an engineer, I want to rename and delete sessions, so that my list stays useful.
- **Requirements:** FR-1
- **Delivered by:** T-02

### US-5

- **Summary:** US-5: The interviewer to refuse to draw architecture until my requirements are clear
- **Feature:** F-2
- **Story:** As a candidate, I want the interviewer to refuse to draw architecture until my requirements are clear, so that I practise scoping first the way real interviews reward.
- **Requirements:** FR-2
- **Delivered by:** T-03

### US-6

- **Summary:** US-6: To be asked for users, read/write ratio, latency and availability targets
- **Feature:** F-2
- **Story:** As a candidate, I want to be asked for users, read/write ratio, latency and availability targets, so that my design rests on numbers.
- **Requirements:** FR-2, FR-5
- **Delivered by:** T-03

### US-7

- **Summary:** US-7: To state what is out of scope and see it recorded
- **Feature:** F-2
- **Story:** As an engineer, I want to state what is out of scope and see it recorded, so that later stages do not drift into it.
- **Requirements:** FR-5
- **Delivered by:** T-03

### US-8

- **Summary:** US-8: To be asked to justify every technology I name
- **Feature:** F-2
- **Story:** As a candidate, I want to be asked to justify every technology I name, so that I learn to defend choices with workload facts.
- **Requirements:** FR-3
- **Delivered by:** T-05

### US-9

- **Summary:** US-9: Failure-mode questions in the architecture and reliability steps
- **Feature:** F-2
- **Story:** As a candidate, I want failure-mode questions in the architecture and reliability steps, so that I practise thinking beyond the happy path.
- **Requirements:** FR-4
- **Delivered by:** T-07

### US-10

- **Summary:** US-10: Capacity estimates recorded with their arithmetic
- **Feature:** F-2
- **Story:** As an engineer, I want capacity estimates recorded with their arithmetic, so that anyone can check them.
- **Requirements:** FR-5
- **Delivered by:** T-03

### US-11

- **Summary:** US-11: Entities, relationships, endpoints and storage choices captured as structured data
- **Feature:** F-2
- **Story:** As an engineer, I want entities, relationships, endpoints and storage choices captured as structured data, so that the PRD states them exactly.
- **Requirements:** FR-5
- **Delivered by:** T-05

### US-12

- **Summary:** US-12: To watch the canvas update as I talk
- **Feature:** F-2
- **Story:** As an engineer, I want to watch the canvas update as I talk, so that I can verify the agent understood me.
- **Requirements:** FR-6
- **Delivered by:** T-03

### US-13

- **Summary:** US-13: To edit or delete any canvas item directly, and have the interviewer notice
- **Feature:** F-2
- **Story:** As an engineer, I want to edit or delete any canvas item directly, and have the interviewer notice, so that chat and canvas never disagree.
- **Requirements:** FR-6
- **Delivered by:** T-09

### US-14

- **Summary:** US-14: An architecture diagram drawn from my components and flows
- **Feature:** F-2
- **Story:** As an engineer, I want an architecture diagram drawn from my components and flows, so that I see the system without drawing it by hand.
- **Requirements:** FR-8
- **Delivered by:** T-06

### US-15

- **Summary:** US-15: To confirm each step in an approval card, or reject it with a reason
- **Feature:** F-2
- **Story:** As an engineer, I want to confirm each step in an approval card, or reject it with a reason, so that the interview advances only when I agree.
- **Requirements:** FR-7
- **Delivered by:** T-04

### US-16

- **Summary:** US-16: A three-part critique after each step and a scorecard at the end
- **Feature:** F-2
- **Story:** As a candidate, I want a three-part critique after each step and a scorecard at the end, so that I know exactly where to improve.
- **Requirements:** FR-9
- **Delivered by:** T-04, T-08

### US-17

- **Summary:** US-17: The interviewer to name a matching reference blueprint
- **Feature:** F-2
- **Story:** As an engineer, I want the interviewer to name a matching reference blueprint, so that I learn the proven technique without being handed the answer.
- **Requirements:** FR-10
- **Delivered by:** T-06

### US-18

- **Summary:** US-18: A second model to review the design for security, efficiency and maintainability
- **Feature:** F-3
- **Story:** As a tech lead, I want a second model to review the design for security, efficiency and maintainability, so that blind spots shared with the interviewer's model are caught.
- **Requirements:** FR-11, G4
- **Delivered by:** T-10

### US-19

- **Summary:** US-19: Every gap to name the affected design items, the risk and the decision needed
- **Feature:** F-3
- **Story:** As a tech lead, I want every gap to name the affected design items, the risk and the decision needed, so that I can act on it without guessing.
- **Requirements:** FR-12
- **Delivered by:** T-10

### US-20

- **Summary:** US-20: The review to flag gaps without inventing features or solutions
- **Feature:** F-3
- **Story:** As a tech lead, I want the review to flag gaps without inventing features or solutions, so that the plan stays mine.
- **Requirements:** FR-12, G3
- **Delivered by:** T-10

### US-21

- **Summary:** US-21: To answer a gap and see the answer recorded as design items
- **Feature:** F-3
- **Story:** As an engineer, I want to answer a gap and see the answer recorded as design items, so that it flows into the PRD and tickets like everything else.
- **Requirements:** FR-13
- **Delivered by:** T-11

### US-22

- **Summary:** US-22: To accept a gap as an open risk with a note
- **Feature:** F-3
- **Story:** As an engineer, I want to accept a gap as an open risk with a note, so that I can move on knowingly.
- **Requirements:** FR-13
- **Delivered by:** T-11

### US-23

- **Summary:** US-23: A visible warning when the review model is the same as the interview model
- **Feature:** F-3
- **Story:** As an operator, I want a visible warning when the review model is the same as the interview model, so that I know the cross-model check is not active.
- **Requirements:** FR-14, NFR-10
- **Delivered by:** T-10

### US-24

- **Summary:** US-24: A full PRD drafted from the design and gap register
- **Feature:** F-4
- **Story:** As a tech lead, I want a full PRD drafted from the design and gap register, so that I have a document to sign off before any planning.
- **Requirements:** FR-15
- **Delivered by:** T-12

### US-25

- **Summary:** US-25: Requirements grouped into features
- **Feature:** F-4
- **Story:** As a tech lead, I want requirements grouped into features, so that the plan and Jira have a clear top level.
- **Requirements:** FR-15, FR-16
- **Delivered by:** T-12

### US-26

- **Summary:** US-26: To sign off or reject the PRD with a reason until it is right
- **Feature:** F-4
- **Story:** As a tech lead, I want to sign off or reject the PRD with a reason until it is right, so that the baseline is something I agreed to.
- **Requirements:** FR-17
- **Delivered by:** T-12

### US-27

- **Summary:** US-27: Open gaps and accepted risks listed in the PRD I sign
- **Feature:** F-4
- **Story:** As a tech lead, I want open gaps and accepted risks listed in the PRD I sign, so that sign-off is informed.
- **Requirements:** FR-15
- **Delivered by:** T-12

### US-28

- **Summary:** US-28: `to-spec` to extend the signed-off PRD without changing it
- **Feature:** F-5
- **Story:** As a tech lead, I want `to-spec` to extend the signed-off PRD without changing it, so that sign-off stays meaningful.
- **Requirements:** FR-18
- **Delivered by:** T-13

### US-29

- **Summary:** US-29: Every user story to name its requirements and its feature
- **Feature:** F-5
- **Story:** As a tech lead, I want every user story to name its requirements and its feature, so that coverage can be checked.
- **Requirements:** FR-18, G2
- **Delivered by:** T-13

### US-30

- **Summary:** US-30: Proposed changes to signed-off content listed for my approval one by one
- **Feature:** F-5
- **Story:** As a tech lead, I want proposed changes to signed-off content listed for my approval one by one, so that nothing changes behind my back.
- **Requirements:** FR-19, G3
- **Delivered by:** T-14

### US-31

- **Summary:** US-31: To approve or edit the test seams
- **Feature:** F-5
- **Story:** As a tech lead, I want to approve or edit the test seams, so that testing is planned at the right level.
- **Requirements:** FR-20
- **Delivered by:** T-13

### US-32

- **Summary:** US-32: Tracer-bullet tickets with blocking edges and acceptance criteria
- **Feature:** F-5
- **Story:** As a tech lead, I want tracer-bullet tickets with blocking edges and acceptance criteria, so that each ticket is demoable and the build order is clear.
- **Requirements:** FR-21
- **Delivered by:** T-15

### US-33

- **Summary:** US-33: To merge, split or re-edge tickets in plain words and see the breakdown regenerated
- **Feature:** F-5
- **Story:** As a tech lead, I want to merge, split or re-edge tickets in plain words and see the breakdown regenerated, so that the granularity fits my team.
- **Requirements:** FR-22
- **Delivered by:** T-15

### US-34

- **Summary:** US-34: A cyclic breakdown rejected with the cycle named
- **Feature:** F-5
- **Story:** As a tech lead, I want a cyclic breakdown rejected with the cycle named, so that the plan is always buildable.
- **Requirements:** FR-22
- **Delivered by:** T-15

### US-35

- **Summary:** US-35: Open gaps kept out of the tickets
- **Feature:** F-5
- **Story:** As a tech lead, I want open gaps kept out of the tickets, so that unagreed work never reaches the board.
- **Requirements:** FR-21, G3
- **Delivered by:** T-15

### US-36

- **Summary:** US-36: Every PRD version as a Word document
- **Feature:** F-6
- **Story:** As a tech lead, I want every PRD version as a Word document, so that I can circulate the exact version people signed.
- **Requirements:** FR-23
- **Delivered by:** T-12, T-13, T-14

### US-37

- **Summary:** US-37: A short requirements document with coverage and gaps
- **Feature:** F-6
- **Story:** As a stakeholder-facing engineer, I want a short requirements document with coverage and gaps, so that scope can be checked without reading the whole PRD.
- **Requirements:** FR-24
- **Delivered by:** T-16

### US-38

- **Summary:** US-38: A user-stories document with tickets and acceptance criteria
- **Feature:** F-6
- **Story:** As a tech lead, I want a user-stories document with tickets and acceptance criteria, so that delivery can be planned from one file.
- **Requirements:** FR-25
- **Delivered by:** T-16

### US-39

- **Summary:** US-39: A context.md I can hand to any agent
- **Feature:** F-6
- **Story:** As a tech lead, I want a context.md I can hand to any agent, so that Jira issues are created without me typing them.
- **Requirements:** FR-26
- **Delivered by:** T-17

### US-40

- **Summary:** US-40: To edit the Jira mapping table before handing context.md over
- **Feature:** F-6
- **Story:** As a tech lead, I want to edit the Jira mapping table before handing context.md over, so that it fits my Jira configuration.
- **Requirements:** FR-26
- **Delivered by:** T-17

### US-41

- **Summary:** US-41: One closed list of features, stories and tickets with explicit rules
- **Feature:** F-6
- **Story:** As a ticketing agent, I want one closed list of features, stories and tickets with explicit rules, so that I create exactly what was approved and nothing else.
- **Requirements:** FR-26, G3
- **Delivered by:** T-17

### US-42

- **Summary:** US-42: Instructions for ambiguity and a required report format
- **Feature:** F-6
- **Story:** As a ticketing agent, I want instructions for ambiguity and a required report format, so that I stop and ask instead of guessing, and the user can verify my work.
- **Requirements:** FR-26
- **Delivered by:** T-17

### US-43

- **Summary:** US-43: A completion view with every file and a zip of all of them
- **Feature:** F-6
- **Story:** As an engineer, I want a completion view with every file and a zip of all of them, so that I can take the whole package in one step.
- **Requirements:** FR-27
- **Delivered by:** T-18

### US-44

- **Summary:** US-44: Identical downloads when nothing has changed
- **Feature:** F-6
- **Story:** As an engineer, I want identical downloads when nothing has changed, so that version control shows only real changes.
- **Requirements:** FR-28, FR-29
- **Delivered by:** T-18

### US-45

- **Summary:** US-45: Replies to start within seconds and downloads to finish quickly
- **Feature:** F-7
- **Story:** As an engineer, I want replies to start within seconds and downloads to finish quickly, so that the tool keeps pace with me.
- **Requirements:** NFR-1, NFR-2
- **Delivered by:** T-18, T-19

### US-46

- **Summary:** US-46: To see token use for the session and be stopped before overspending
- **Feature:** F-7
- **Story:** As an engineer, I want to see token use for the session and be stopped before overspending, so that I control cost.
- **Requirements:** NFR-4
- **Delivered by:** T-19

### US-47

- **Summary:** US-47: A clear message and a retry button when a provider fails
- **Feature:** F-7
- **Story:** As an engineer, I want a clear message and a retry button when a provider fails, so that an outage does not cost me my session.
- **Requirements:** NFR-5
- **Delivered by:** T-19

### US-48

- **Summary:** US-48: Keys kept out of the browser, logs and downloads
- **Feature:** F-7
- **Story:** As an operator, I want keys kept out of the browser, logs and downloads, so that running the app cannot leak them.
- **Requirements:** NFR-6
- **Delivered by:** T-19

### US-49

- **Summary:** US-49: Every screen and card to work for me
- **Feature:** F-7
- **Story:** As an engineer using only a keyboard or a screen reader, I want every screen and card to work for me, so that the app is usable.
- **Requirements:** NFR-7
- **Delivered by:** T-20

### US-50

- **Summary:** US-50: Structured logs with per-node, per-model latency and tokens
- **Feature:** F-7
- **Story:** As an operator, I want structured logs with per-node, per-model latency and tokens, so that I can diagnose slow or costly sessions.
- **Requirements:** NFR-8
- **Delivered by:** T-19

### US-51

- **Summary:** US-51: To run everything locally with one command
- **Feature:** F-7
- **Story:** As an operator, I want to run everything locally with one command, so that I can self-host it.
- **Requirements:** NFR-9
- **Delivered by:** T-01

### US-52

- **Summary:** US-52: To choose any capable model for each role, and be told at startup if one cannot call tools or return structured output
- **Feature:** F-7
- **Story:** As an operator, I want to choose any capable model for each role, and be told at startup if one cannot call tools or return structured output, so that I am not locked to one vendor.
- **Requirements:** NFR-10
- **Delivered by:** T-01

### US-53

- **Summary:** US-53: Word documents that open cleanly in Word, LibreOffice and Google Docs
- **Feature:** F-7
- **Story:** As a tech lead, I want Word documents that open cleanly in Word, LibreOffice and Google Docs, so that reviewers can read them whatever they use.
- **Requirements:** NFR-11
- **Delivered by:** T-16

### US-54

- **Summary:** US-54: To run several sessions at once on one instance
- **Feature:** F-7
- **Story:** As an engineer, I want to run several sessions at once on one instance, so that I can compare alternative designs.
- **Requirements:** NFR-12
- **Delivered by:** T-20

### US-55

- **Summary:** US-55: Vendored prompt text kept verbatim with its licence and attribution
- **Feature:** F-7
- **Story:** As a maintainer, I want vendored prompt text kept verbatim with its licence and attribution, so that the project stays compliant.
- **Requirements:** NFR-13
- **Delivered by:** T-01

## 7. Tickets

### T-01: Walking skeleton with two model roles

- **Summary:** T-01: Walking skeleton with two model roles
- **Parent feature:** F-7 (from US-51)
- **Delivers stories:** US-51, US-52, US-55
- **Blocked by:** None
- **What to build:** One command starts the web app, the agent service and the database. The user opens the app, types a message and sees a streamed reply through the full path: browser → CopilotKit runtime route → FastAPI AG-UI endpoint → LangGraph graph → interview model. Both model roles are configured from the environment and checked at startup, and the vendored runtime assets are loaded.
- **Acceptance criteria:**
  - [ ] `docker compose up` with one `.env` starts `web`, `agent` and `db`; `.env.example` documents every S1.3 variable with an OpenAI-compatible block and an Anthropic block (S1.1, S1.2, S1.3).
  - [ ] A chat message produces a streamed reply through the runtime proxy, never a direct browser call to FastAPI (S4.1, S4.3, S4.4).
  - [ ] The agent refuses to start, naming the variable, for each condition in S1.4.
  - [ ] Every chat model comes from the one two-role factory; no other module imports a provider SDK (S1.6).
  - [ ] The startup check runs for both roles and refuses to start naming the role, capability, provider and model; `SKIP_MODEL_CHECK=true` skips it (S1.7).
  - [ ] `review_model_distinct` is computed at startup as S1.8 defines.
  - [ ] `app-assets/` ships as package data with the five files of S12.1, copied verbatim from this repository's `app-assets/`; the agent refuses to start, naming the file, if any is missing or empty (S12.1, S12.2).
  - [ ] A graph-seam test with two scripted fake models passes, proving the seam before any feature exists.

### T-02: Sessions — create, list, resume, rename, delete

- **Summary:** T-02: Sessions — create, list, resume, rename, delete
- **Parent feature:** F-1 (from US-1)
- **Delivers stories:** US-1, US-2, US-3, US-4
- **Blocked by:** T-01
- **What to build:** The user lands on a session list, creates a named session, works in it, closes the browser or restarts the stack, and finds the session exactly as left. Sessions can be renamed and deleted. The REST API is fully described by the generated OpenAPI document.
- **Acceptance criteria:**
  - [ ] Session routes behave as S3.1–S3.5, including `422`, `404` and idempotent delete; every error uses the S3.6 shape.
  - [ ] `DesignState` extends `CopilotKitState` with the stages of S2.3; a new session's state has every S2.2 field with the initial values of S3.1 (S2.1).
  - [ ] The list page shows sessions newest first with name and stage, paginated by keyset cursor (S3.2, S11.1).
  - [ ] State is checkpointed in Postgres with thread ID equal to session ID and survives an `agent` restart (S4.2, NFR-3).
  - [ ] `/openapi.json` describes every route with typed models and error shapes; the frontend's REST types are generated from it (S3.7).

### T-03: Step 1 — clarify requirements, live on the canvas

- **Summary:** T-03: Step 1 — clarify requirements, live on the canvas
- **Parent feature:** F-2 (from US-5)
- **Delivers stories:** US-5, US-6, US-7, US-10, US-12
- **Blocked by:** T-02
- **What to build:** The interviewer, prompted from the vendored instructions and course context, runs Step 1. It asks for users, use cases, read/write ratio, latency, availability and out-of-scope items, and records each answer as a structured item that appears on the canvas during the conversation. During Step 1 it cannot record architecture, even if asked.
- **Acceptance criteria:**
  - [ ] The design record and its Step 1 item types exist as S2.4, S2.5, S2.6, S2.7 and S2.15 define.
  - [ ] The interviewer's system prompt is assembled as S5.2 defines, from `app-assets/` files.
  - [ ] Backend tools record requirements, NFR targets, out-of-scope notes and estimates with IDs that are never reused, executed by the `design_tools` node (S5.1, S5.3).
  - [ ] A graph-seam test shows that asking to "add a Redis cache" during Step 1 records nothing architectural (S5.4).
  - [ ] Estimates keep their formula as well as their result (S2.7).
  - [ ] The canvas shows Step 1 panels with item IDs, updating live (S11.2, S11.3).

### T-04: Step confirmation gate and per-step critique

- **Summary:** T-04: Step confirmation gate and per-step critique
- **Parent feature:** F-2 (from US-15)
- **Delivers stories:** US-15, US-16
- **Blocked by:** T-03
- **What to build:** When the interviewer thinks a step is complete, an approval card appears summarizing it. Approving advances the session and produces a three-part critique; rejecting with a reason keeps the session on the step. A stage tracker in the header shows progress.
- **Acceptance criteria:**
  - [ ] `confirm_step` is a frontend tool rendered with `useHumanInTheLoop`; rejection requires text (S5.7, S11.4).
  - [ ] Approval and rejection update state exactly as S5.7 defines.
  - [ ] After each approval the `critic` stores one critique with strengths, bottlenecks and questions (S5.8, S2.8).
  - [ ] Routing is a pure function of state and ends the run while a gate call is unanswered (S5.1), verified through the graph seam.
  - [ ] The header shows the stage tracker with current and confirmed steps (S11.2).

### T-05: Step 2 — data model, API contracts and storage choices

- **Summary:** T-05: Step 2 — data model, API contracts and storage choices
- **Parent feature:** F-2 (from US-8)
- **Delivers stories:** US-8, US-11
- **Blocked by:** T-04
- **What to build:** In Step 2 the interviewer captures entities, relationships, keys, endpoints and storage choices on the canvas. Every storage choice starts as "proposed" and becomes "decided" only after the user justifies it with workload facts.
- **Acceptance criteria:**
  - [ ] Entity, relationship, endpoint and storage-choice types and tools exist as S2.7 and S5.3 define.
  - [ ] A graph-seam test shows "I'll use Cassandra" alone leaves the choice `proposed` and prompts a justification question; a justification naming a valid basis makes it `decided` (S5.5).
  - [ ] Rejected alternatives are recorded with the choice (S2.7).
  - [ ] The canvas shows Step 2 panels with item IDs (S11.3).

### T-06: Step 3a — components, data flows and the architecture diagram

- **Summary:** T-06: Step 3a — components, data flows and the architecture diagram
- **Parent feature:** F-2 (from US-14)
- **Delivers stories:** US-14, US-17
- **Blocked by:** T-05
- **What to build:** In Step 3 the interviewer records components and read/write flows, and the canvas draws an architecture diagram that updates as the design changes. When the problem matches a reference blueprint, the interviewer names the pattern and its key technique as something to consider.
- **Acceptance criteria:**
  - [ ] Component and flow types and tools exist (S2.7, S5.3).
  - [ ] A pure function produces Mermaid source as S11.3 defines; the same input gives the same output.
  - [ ] The diagram panel renders it and shows the source in a collapsible block (S11.3).
  - [ ] The course context in the interviewer prompt carries the three blueprints, and the interviewer frames them as patterns to consider (S5.2, FR-10).

### T-07: Step 3b — CAP stance, cache policies and the failure-mode gate

- **Summary:** T-07: Step 3b — CAP stance, cache policies and the failure-mode gate
- **Parent feature:** F-2 (from US-9)
- **Delivers stories:** US-9
- **Blocked by:** T-06
- **What to build:** Still in Step 3, the interviewer records the CAP stance and cache policies and asks at least one failure-mode question. Step 3 cannot be confirmed until a failure mode exists; the attempt explains what is missing instead of opening the card.
- **Acceptance criteria:**
  - [ ] CAP stance, cache-policy and failure-mode types and tools exist (S2.7, S5.3).
  - [ ] Confirming Step 3 with no failure mode returns the blocker as a tool result and opens no card (S5.6).
  - [ ] The canvas shows the CAP, cache and failure-mode panels (S11.3).

### T-08: Steps 4–5 and the final scorecard

- **Summary:** T-08: Steps 4–5 and the final scorecard
- **Parent feature:** F-2 (from US-16)
- **Delivers stories:** US-16
- **Blocked by:** T-07
- **What to build:** Step 4 captures SPOFs with mitigations and observability signals; Step 5 captures trade-offs and extensions. Step 4 cannot be confirmed while any SPOF lacks a mitigation. When Step 5 is confirmed, the user gets a scorecard across the five evaluation dimensions, and the session moves to design review.
- **Acceptance criteria:**
  - [ ] SPOF, signal, trade-off and extension types and tools exist (S2.7, S5.3).
  - [ ] Confirming Step 4 with no SPOF, or an unmitigated SPOF, returns the blocker and opens no card (S5.6).
  - [ ] After Step 5 approval the critic stores a scorecard with five dimension scores, quoted evidence and advice, and sets `stage` to `design_review` (S5.8, S2.8).
  - [ ] The scorecard is shown in the workspace.

### T-09: Direct canvas edits the interviewer notices

- **Summary:** T-09: Direct canvas edits the interviewer notices
- **Parent feature:** F-2 (from US-13)
- **Delivers stories:** US-13
- **Blocked by:** T-08
- **What to build:** The user can add, edit and delete any item on any canvas panel. Invalid edits are rejected with a visible reason and the old value is kept. On its next turn the interviewer acknowledges the edits by item ID.
- **Acceptance criteria:**
  - [ ] Every canvas panel supports add, edit and delete through `agent.setState` (S11.3).
  - [ ] Writes are validated as S2.15 defines; an invalid write keeps the old state and sets `last_error`.
  - [ ] New items get IDs per S2.5; deleted IDs are never reused.
  - [ ] A graph-seam test shows the next interviewer call receives a note naming the edited IDs, and that `agent_design` tracks the interviewer's own writes (S5.9).

### T-10: Design review on the review model

- **Summary:** T-10: Design review on the review model
- **Parent feature:** F-3 (from US-18)
- **Delivers stories:** US-18, US-19, US-20, US-23
- **Blocked by:** T-08
- **What to build:** After Step 5, three reviewers on the separate review model check the design in parallel for security, efficiency and maintainability. A merge step produces the gap register, shown in its own panel with each gap's lens, severity, affected items, risk and decision needed. When the review model equals the interview model, a persistent warning says the cross-model check is not active.
- **Acceptance criteria:**
  - [ ] The `Gap` type exists as S2.9 defines.
  - [ ] The three reviewer nodes run in parallel on the review-role model with the inputs of S6.1, the checklists of S6.2 and the rules and severity definitions of S6.3.
  - [ ] The `gap_merger` drops findings that cite no existing item, combines duplicates keeping the higher severity, and issues `GAP` IDs (S6.4).
  - [ ] A graph-seam test with a scripted review model shows a finding that proposes a new component produces no design item and no requirement (S6.3, G3).
  - [ ] Zero gaps sends the session to `prd_draft`; otherwise to `gap_resolution` (S6.4).
  - [ ] Tokens are counted under the `review` role (S13.3).
  - [ ] The gap register panel and the same-model warning render as S11.2 and S6.6 define.

### T-11: Gap resolution — answer or accept

- **Summary:** T-11: Gap resolution — answer or accept
- **Parent feature:** F-3 (from US-21)
- **Delivers stories:** US-21, US-22
- **Blocked by:** T-10
- **What to build:** The user goes through the gap register in a card, answering gaps or accepting them as open risks, or accepting all at once. Answers go to the interviewer, which records them as ordinary design items and marks each gap resolved. When no gap is open, the session moves to PRD drafting.
- **Acceptance criteria:**
  - [ ] `decide_gaps` is a frontend tool with per-gap decisions and "accept all"; answers and acceptances require text where S11.4 says so.
  - [ ] Accepted gaps get `status` `accepted` and the note; answered gaps are recorded through design tools and closed with `resolve_gap`, filling `resolved_by` (S6.5, S5.3).
  - [ ] The review does not re-run; `stage` becomes `prd_draft` when no gap is open (S6.5).

### T-12: PRD v1.0 — draft, sign-off and first download

- **Summary:** T-12: PRD v1.0 — draft, sign-off and first download
- **Parent feature:** F-4 (from US-24)
- **Delivers stories:** US-24, US-25, US-26, US-27, US-36
- **Blocked by:** T-11
- **What to build:** The agent drafts a full PRD from the design record and gap register: problem, goals, users, features grouping the requirements, requirements copied verbatim, scope, and open gaps with their features. The user reviews it in a PRD viewer and signs it off, or rejects it with a reason until it is right. Once signed off, v1.0 is frozen and downloadable as Word.
- **Acceptance criteria:**
  - [ ] `PrdDoc`, `Feature`, `PrdRequirement`, `PrdNfr` and `PrdVersion` exist as S2.10 and S2.12 define.
  - [ ] The `prd_drafter` behaves as S7.1 defines; a graph-seam test shows FR and NFR statements in the draft are byte-identical to the design record.
  - [ ] Validation and its one retry behave as S7.2 defines.
  - [ ] `sign_off_prd` approval and rejection behave as S7.3 and S7.4 define; a signed-off version is never modified.
  - [ ] The PRD viewer shows the draft and every version with a version switcher (S11.2).
  - [ ] The download listing and file routes of S10.3 exist, backed by pure renderers (S10.1); `prd-v1.0.docx` renders as S10.4 defines and is `409` before sign-off.
  - [ ] The file opens without a repair prompt in Word 365, LibreOffice 24+ and Google Docs (NFR-11).

### T-13: PRD v1.1 with `to-spec`, and seam approval

- **Summary:** T-13: PRD v1.1 with `to-spec`, and seam approval
- **Parent feature:** F-5 (from US-28)
- **Delivers stories:** US-28, US-29, US-31, US-36
- **Blocked by:** T-12
- **What to build:** After sign-off, the `to-spec` method extends the PRD with a solution, user stories traced to requirements and features, implementation decisions and further notes, without touching signed-off sections. The agent proposes test seams; once the user approves them, v1.1 is frozen and downloadable.
- **Acceptance criteria:**
  - [ ] The `spec_synthesizer` prompt and output behave as S8.1 defines, using `app-assets/to-spec.md` verbatim.
  - [ ] A graph-seam test shows the signed-off sections of `prd_draft` are byte-identical to v1.0 after synthesis, and every open gap appears in further notes with its ID (S8.1).
  - [ ] `UserStory` exists as S2.11 defines; validation and its one retry behave as S8.2 defines, including that every FR is covered by a story.
  - [ ] `approve_seams` approve, edit and reject behave as S8.3; approval appends v1.1 and routes as S8.4 defines.
  - [ ] `prd-v1.1.docx` renders as S10.4 defines and ends with the attribution line of S12.3.

### T-14: Proposed changes and PRD v1.2

- **Summary:** T-14: Proposed changes and PRD v1.2
- **Parent feature:** F-5 (from US-30)
- **Delivers stories:** US-30, US-36
- **Blocked by:** T-13
- **What to build:** When synthesis proposed changes to signed-off content, the user reviews each one in a card, approving or rejecting it, or accepting all. Approved changes produce PRD v1.2, with a table of what changed; rejected ones are dropped. With no proposals, this stage is skipped.
- **Acceptance criteria:**
  - [ ] `ProposedChange` exists as S2.13 defines.
  - [ ] `review_changes` and the `change_applier` behave as S8.5 defines; no v1.2 is created when every change is rejected.
  - [ ] A graph-seam test shows v1.0 and v1.1 are unchanged after v1.2 is created, and later stages read v1.2 as the current PRD (S2.12, S8.6).
  - [ ] `prd-v1.2.docx` renders with its "Changes from v1.1" table (S10.4).

### T-15: Tickets with `to-tickets` and the review loop

- **Summary:** T-15: Tickets with `to-tickets` and the review loop
- **Parent feature:** F-5 (from US-32)
- **Delivers stories:** US-32, US-33, US-34, US-35
- **Blocked by:** T-13
- **What to build:** The `to-tickets` method breaks the current PRD into tracer-bullet tickets with blocking edges and acceptance criteria, with open gaps kept out of its input. The user approves the breakdown or asks for changes in plain words until it is right. A cyclic breakdown is never shown as valid.
- **Acceptance criteria:**
  - [ ] The `ticket_planner` prompt is built as S9.1 defines, using `app-assets/to-tickets.md` verbatim; a graph-seam test shows the planner's input contains no gap text.
  - [ ] `Ticket` exists as S2.14 defines; validation and its one retry behave as S9.2 defines.
  - [ ] The `dag_validator` rejects unknown blockers, duplicates and cycles, naming the cycle, and renumbers valid tickets topologically (S9.3).
  - [ ] `review_tickets` approve and revise behave as S9.4 defines; approval sets `tickets_approved_at` and `stage` `complete`.
  - [ ] The ticket view shows the breakdown with blocking edges (S11.2).

### T-16: Requirements.docx and UserStories.docx

- **Summary:** T-16: Requirements.docx and UserStories.docx
- **Parent feature:** F-6 (from US-37)
- **Delivers stories:** US-37, US-38, US-53
- **Blocked by:** T-15
- **What to build:** Once tickets are approved, the user can download a requirements document with coverage and a gap appendix, and a user-stories document with stories by feature, tickets with acceptance criteria, and build waves.
- **Acceptance criteria:**
  - [ ] `requirements.docx` renders as S10.5 defines from the current PRD.
  - [ ] `user-stories.docx` renders as S10.6 defines, with build waves computed from the blocking edges.
  - [ ] Both are `409` before `stage` is `complete` (S10.3).
  - [ ] Both open without repair prompts in Word 365, LibreOffice 24+ and Google Docs (NFR-11).

### T-17: The Jira hand-off — context.md

- **Summary:** T-17: The Jira hand-off — context.md
- **Parent feature:** F-6 (from US-39)
- **Delivers stories:** US-39, US-40, US-41, US-42
- **Blocked by:** T-15
- **What to build:** Once tickets are approved, the user can download context.md: a self-contained prompt any agent can follow to create the Jira issues, with an editable mapping table, hard rules against adding anything, the embedded features, stories, tickets and open gaps, and a required report format.
- **Acceptance criteria:**
  - [ ] `context.md` follows the six-part template of S10.7 in order, with the default mapping rows exactly as listed.
  - [ ] Every feature, story and ticket of the current PRD and breakdown appears with every field; every open gap appears under its feature (S10.7, S7.1).
  - [ ] The rules include every stop-and-ask condition in S10.7, including the existing-issue check.
  - [ ] The file ends with the attribution line of S12.3.
  - [ ] An export-seam test compares a rendered context.md for a fixture session against a checked-in expected file, byte for byte.

### T-18: Completion view, zip and deterministic downloads

- **Summary:** T-18: Completion view, zip and deterministic downloads
- **Parent feature:** F-6 (from US-43)
- **Delivers stories:** US-43, US-44, US-45
- **Blocked by:** T-14, T-16, T-17
- **What to build:** When the session completes, a completion view lists every document with a "Download all (.zip)" action. Every download is byte-identical across renders of the same state, and generating all of them is fast.
- **Acceptance criteria:**
  - [ ] The completion view renders from the S10.3 listing (S11.5), and the `completer` posts the downloads message (S9.4).
  - [ ] `bundle.zip` contains every available kind except itself, with the file names of S10.2 (S10.8).
  - [ ] Rendering every kind twice from the same state yields byte-identical files, Word documents and zip included (S10.9, FR-28).
  - [ ] With a 50-ticket fixture, generating `bundle.zip` takes at most 10 s at p95 over 20 runs, and each download logs `export_ms` (NFR-2, S13.5).

### T-19: Resilience, token budget and structured logs

- **Summary:** T-19: Resilience, token budget and structured logs
- **Parent feature:** F-7 (from US-45)
- **Delivers stories:** US-45, US-46, US-47, US-48, US-50
- **Blocked by:** T-04
- **What to build:** When a provider throttles, errors or times out, the app retries quietly; only if retries fail does the user see an alert with a retry button, and state is never half-written. A token meter shows use per model role and warns at 80 %; at 100 % no further model calls are made. Logs are structured JSON with per-node, per-role latency and tokens, and never contain secrets.
- **Acceptance criteria:**
  - [ ] Model calls retry as S13.1 defines; after exhausted retries only `last_error` changes (S13.2), proven through the graph seam with a failing fake model.
  - [ ] Token accounting per role, the budget stop and the usage estimate behave as S13.3 defines.
  - [ ] Structured output falls back from JSON-schema mode to tool calling as S13.4 defines.
  - [ ] The error alert, Retry action and per-role token meter behave as S11.6 defines.
  - [ ] Logs follow S13.5, including `role`, `ttft_ms` and `export_ms`; LangSmith tracing toggles by variable.
  - [ ] A test scans log output, the web bundle and every download kind for both configured key values and finds none (S1.5, NFR-6).

### T-20: Accessibility audit and end-to-end smoke test

- **Summary:** T-20: Accessibility audit and end-to-end smoke test
- **Parent feature:** F-7 (from US-49)
- **Delivers stories:** US-49, US-54
- **Blocked by:** T-09, T-18, T-19
- **What to build:** Every screen, panel and card is usable by keyboard and screen reader and meets WCAG 2.1 AA. One Playwright test drives a short session through the full stack with scripted fake models, from creating a session to downloading the zip, and five sessions run concurrently with independent state.
- **Acceptance criteria:**
  - [ ] Every interactive element is keyboard-operable with an accessible name and meets AA contrast in both themes (S11.7).
  - [ ] An automated accessibility scan of the session list, the workspace in each stage panel, every gate card and the completion view reports no AA violations.
  - [ ] The Playwright smoke test passes end to end and downloads a zip containing every available kind (S10.8).
  - [ ] Five sessions driven concurrently with the fake models all complete with correct, independent state (NFR-12).

## 8. Open gaps

None recorded for this project.

## 9. Report

When you have finished, reply with:

1. A table with columns ID, Issue type, Jira key, Parent key, Links created, with one row per ID in sections 5 to 7.
2. A list of anything you did not create and why. It should be empty.

---

*Ticket and spec method: to-tickets / to-spec, mattpocock-skills 1.2.3 (MIT, © 2026 Matt Pocock).*
