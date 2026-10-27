# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Blueprint Studio is for one engineering team, not the public. Three kinds of people use it:

- **Engineers practising system design** (often for interviews). They want structure, honest critique and a scorecard backed by quoted evidence.
- **Tech leads planning a real system.** They want a design they can sign off as a PRD and hand to Jira without anything added that nobody agreed to.
- **PMs.** They need to see every session that is still pending across the team, whoever owns it.

Practice and delivery carry equal weight: when a decision favours one, it must not cost the other.

The team self-hosts the app. Whoever runs it (the operator) configures the two models and the database.

## Product Purpose

Blueprint Studio is a design partner that enforces structure. An AI interviewer takes the user through five framework steps in order: clarify requirements; data and API; high-level architecture; scale and reliability; trade-offs and extensions. Every answer is recorded as structured, ID-labelled data, and each step closes only when the user confirms it.

A second model then reviews the whole design for security, efficiency and maintainability gaps. The user signs off a PRD drafted from the design. The app extends the PRD with user stories and test seams, breaks the work into tickets, and hands back Word documents, Mermaid diagrams and a `context.md` that any agent can follow to create exactly the approved Jira issues.

Users can also attach existing material (PRDs, specs, diagrams, notes). The agent proposes what each file states, quoting it; the user confirms every item; and the interviewer questions whatever the file leaves weak.

Success means the team plans systems in one structured flow. That flow stays traceable from requirement to ticket and never drifts in scope after sign-off.

## Positioning

- **Structure over speed.** The interviewer refuses to draw architecture before requirements are clear, and asks for justification and failure modes before it records a decision.
- **A second opinion from a different model.** A model other than the interviewer judges the design, so blind spots the two share are caught.
- **No scope creep, by construction.** Nothing reaches the tickets or the Jira hand-off that the user did not say or approve. Signed-off PRD versions are frozen, and the design review flags gaps but never adds scope.
- **Traceable end to end.** Every ticket traces to a story, every story to a requirement and a feature, and every imported item to the file and passage it came from.

## Operating Context

- **Where it runs.** Self-hosted, either in local mode (one machine, a SQLite file) or in server mode (Docker Compose with Postgres).
- **Models.** Any OpenAI-compatible endpoint (a hosted vendor, a gateway or a local server), configured as two roles: interview and review.
- **The flow.** A session moves through the interview, the design review and gap resolution, PRD sign-off, synthesis and tickets, and ends with downloads.
- **Outputs.** PRD versions as .docx, Requirements.docx, UserStories.docx, Diagrams.md, `context.md` and a zip of everything. Jira issues are created by a separate agent of the team's choice from `context.md`, never by the app itself.

## Capabilities and Constraints

**Built:**
- the guided interview with approval cards;
- the critique after every step and the final scorecard;
- the design review with its gap register;
- PRD versioning (v1.0 signed off, v1.1, v1.2);
- tickets with build waves;
- deterministic downloads;
- document import (text, PDF, Word, Mermaid, draw.io, and images when the interview model can read them);
- a per-session token budget, and retries on provider errors.

**Fixed rules:**
- the steps run in order;
- signed-off content is changed only through proposed changes;
- exports never call a model;
- API keys stay on the server;
- the canvas is read-only (the interviewer records; the user answers in the chat).

**Terminology:** session, step, design record, item IDs (`FR-1`, `CMP-2`…), gap, sign-off, seam, ticket, attachment, candidate.

**Confirmed direction, not yet built.** These are accounts and shared sessions, and they replace PRD non-goal NG1 ("no accounts, sharing or collaboration"):
- Users log in.
- A user's sessions are private by default: someone who has shared nothing and has nothing shared with them sees only their own work.
- A session or project can be shared with other users as a developer or a participant, who can then see it.
- A PM role sees every pending session, shared or personal.

**Open decisions:**
- what a developer may do that a participant may not;
- exactly which sessions count as "pending" for the PM view;
- whether a "project" groups several sessions or is another name for a session;
- how users log in.

## Brand Commitments

- **Name and standing.** The product is **Blueprint Studio**, and it stands on its own name. The vendored "Senior Software Engineer Design" interviewer instructions and course context are the method it uses, not a brand it belongs to.
- **Interviewer voice.** The interviewer acts as a senior engineer and design partner. It is collaborative, rigorous and probing, and it names the evaluation dimension behind each piece of feedback. Its critiques use three parts: Strengths & Alignment, Bottlenecks & Unaddressed Trade-Offs, Probing / Next-Step Questions.
- **Attribution.** The `to-spec` and `to-tickets` prompts are vendored verbatim under MIT, and their attribution must stay visible in the repository and in the documents derived from them.

## Evidence on Hand

- **What exists.** The approved PRD (`PRD.md`), the technical spec (`SPECS.md`), the import spec (`SPEC-document-import.md`), a worked example of the Jira hand-off (`agent/tests/expected/example-context.md`) and the shared diagram fixtures (`agent/tests/expected/diagrams/`).
- **What doesn't.** There are no users, testimonials, usage metrics, benchmarks or published model compatibility lists. Future work must not invent them.

## Product Principles

1. **Confirm, never assume.** Every step, gap decision, sign-off and imported item needs the user's explicit answer; the agent proposes and the user decides.
2. **Show the evidence.** Feedback quotes the conversation, imports quote their files, and gaps cite the items they concern.
3. **What was agreed is what ships.** Approved content reaches the PRD, the tickets and Jira unchanged, and nothing else does.
4. **Teach while designing.** The tool should leave the engineer better at system design, not just finished with a document.
5. **Private until shared.** A person's work is theirs unless they share it; the PM view is the one deliberate exception.

## Accessibility & Inclusion

Every screen meets WCAG 2.1 AA in both light and dark themes and is fully keyboard-operable, including the approval cards, the gap register, the canvas and the downloads. The end-to-end smoke test checks this with axe in both themes.
