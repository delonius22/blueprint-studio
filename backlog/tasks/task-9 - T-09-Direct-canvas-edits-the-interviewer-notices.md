---
id: TASK-9
title: 'T-09: Direct canvas edits the interviewer notices'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 01:19'
labels: []
dependencies:
  - TASK-8
references:
  - TICKETS.md
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The user can add, edit and delete any item on any canvas panel. Invalid edits are rejected with a visible reason and the old value is kept. On its next turn the interviewer acknowledges the edits by item ID.

Delivers stories: US-13

Mirrors T-09 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every canvas panel supports add, edit and delete through `agent.setState` (S11.3).
- [x] #2 Writes are validated as S2.15 defines; an invalid write keeps the old state and sets `last_error`.
- [x] #3 New items get IDs per S2.5; deleted IDs are never reused.
- [x] #4 A graph-seam test shows the next interviewer call receives a note naming the edited IDs, and that `agent_design` tracks the interviewer's own writes (S5.9).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. SessionAgent.run: browser state writes limited to design, id_counters and clearing last_error; validated against the checkpoint (schemas, S2.15, counters never decrease, no reused IDs); invalid -> keep old state, set last_error (invalid_edit).
2. Interviewer: diff design vs agent_design -> S5.9 edit note naming added/changed/deleted IDs; the interviewer's reply and design_tools writes set agent_design.
3. Web: add/edit/delete on every canvas panel via agent.setState with S2.5 IDs from id_counters, then a no-message run to persist and validate.
4. Tests: service-level write validation, graph seam edit note + agent_design tracking, component tests for editing.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.edits.apply_browser_write runs in SessionAgent.run before the graph sees a run's state: the browser may change only design and id_counters (and clear last_error); every other session field comes from the checkpoint. A changed design is validated whole (schemas, S2.15 violations, counters never decrease, an ID issued before is never reused); invalid -> old state kept, last_error code invalid_edit (not retryable); a later valid write clears it. The interviewer diffs design vs agent_design and passes an S5.9 edit note (added/changed/deleted IDs) into its prompt; its reply and design_tools writes set agent_design. Web: lib/editing.ts (field specs for all 16 lists, S2.5 ID issuance, pure add/update/delete, storage choice reset to proposed on hand edits), ItemForm (nested entity fields and flow steps), editable Panel and CapStancePanel through CanvasEditContext; each save is agent.setState plus a run with no message, which saves and validates at once. Editing is enabled during the interview stage, when the canvas is the main panel (S11.2).
Validation: agent pytest 130 passed; web vitest 42 passed; browser: canvas add saved on the server, survived reload, and the next interviewer turn received the note naming FR-1.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every canvas panel supports add, edit and delete; edits are written through agent.setState with IDs issued from id_counters, saved and validated by the agent (invalid writes keep the old state and set last_error), and the interviewer's next call receives a note naming the edited IDs while agent_design tracks its own writes. Verified with service-level write tests, graph-seam tests, component tests and a browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
