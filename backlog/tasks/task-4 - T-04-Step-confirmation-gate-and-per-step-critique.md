---
id: TASK-4
title: 'T-04: Step confirmation gate and per-step critique'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 23:08'
labels: []
dependencies:
  - TASK-3
references:
  - TICKETS.md
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When the interviewer thinks a step is complete, an approval card appears summarizing it. Approving advances the session and produces a three-part critique; rejecting with a reason keeps the session on the step. A stage tracker in the header shows progress.

Delivers stories: US-15, US-16

Mirrors T-04 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `confirm_step` is a frontend tool rendered with `useHumanInTheLoop`; rejection requires text (S5.7, S11.4).
- [x] #2 Approval and rejection update state exactly as S5.7 defines.
- [x] #3 After each approval the `critic` stores one critique with strengths, bottlenecks and questions (S5.8, S2.8).
- [x] #4 Routing is a pure function of state and ends the run while a gate call is unanswered (S5.1), verified through the graph seam.
- [x] #5 The header shows the stage tracker with current and confirmed steps (S11.2).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
confirm_step is registered on the frontend with useHumanInTheLoop (zod schema) and rendered as ConfirmStepCard (rejection requires text). Graph: route_start reads the newest tool result (gates.last_answer); approved confirm_step -> critic, anything else -> interviewer. The critic (interview model, structured output via llm.structured with JSON-schema then tool-calling) appends the step to confirmed_steps, advances current_step, stores one Critique and posts it as a three-part chat message. Header shows StageTracker. Backend calls in the same turn as a gate run in design_tools, then the run ends while the gate waits.
Validation: agent pytest (graph seam: run ends on unanswered gate, approve/reject state, steps 1-5, pure routing), web vitest 17 passed (card, tracker), browser: reject with reason then approve; tracker moved to step 2 and the critique appeared.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Step confirmation gate: the interviewer calls the confirm_step frontend tool, the run ends until the user answers in a card; approval confirms the step, advances it and stores a three-part critique from the critic; rejection with a required reason returns to the interviewer on the same step. The header shows a stage tracker. Verified through the graph seam, component tests and a browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
