---
id: TASK-7
title: 'T-07: Step 3b — CAP stance, cache policies and the failure-mode gate'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-14 23:17'
labels: []
dependencies:
  - TASK-6
references:
  - TICKETS.md
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Still in Step 3, the interviewer records the CAP stance and cache policies and asks at least one failure-mode question. Step 3 cannot be confirmed until a failure mode exists; the attempt explains what is missing instead of opening the card.

Delivers stories: US-9

Mirrors T-07 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CAP stance, cache-policy and failure-mode types and tools exist (S2.7, S5.3).
- [x] #2 Confirming Step 3 with no failure mode returns the blocker as a tool result and opens no card (S5.6).
- [x] #3 The canvas shows the CAP, cache and failure-mode panels (S11.3).
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tools set_cap_stance, upsert_cache_policy, upsert_failure_mode.
2. S5.6: interviewer tool-call streaming suppressed; confirm_step goes through design_tools, which checks step blockers (Step 3: at least one failure mode). Blocked -> error tool result listing blockers, no card (card renders nothing for a blocker result). Clear -> re-emit the call with its original id so the card opens.
3. Canvas CAP, cache-policy and failure-mode panels.
4. Tests: graph seam and AG-UI endpoint (no TOOL_CALL events for a blocked gate), panels.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added set_cap_stance, upsert_cache_policy, upsert_failure_mode. S5.6 mechanism: the interviewer's tool calls are no longer streamed (copilotkit emit-tool-calls False); confirm_step is routed through design_tools, which evaluates step_blockers on the post-tool design. Blocked -> error tool result {"error", "blockers"} and the interviewer explains; ConfirmStepCard renders nothing for a blocker result. Clear -> design_tools dispatches a blueprint_open_gate custom event and SessionAgent translates it into TOOL_CALL_START/ARGS/END under the original tool-call id (copilotkit_emit_tool_call's events are not forwarded on the HttpAgent path). T-04 tests updated for the new Step 3 rule. Canvas: CAP stance, cache policies, failure modes panels.
Validation: agent pytest 100 passed (incl. AG-UI test: no TOOL_CALL events for a blocked gate, one with the original id for a clear gate); web vitest 25 passed; browser: CONFIRM 3 without a failure mode opened no card; after FM-1 the card opened and approval moved to step 4.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Step 3 records the CAP stance, cache policies and failure modes; confirming Step 3 without a failure mode returns the blocker to the interviewer as a tool result and opens no card, enforced in the graph before any card is streamed. The canvas shows the CAP, cache and failure-mode panels. Verified through graph-seam, AG-UI endpoint and component tests and a browser run.
<!-- SECTION:FINAL_SUMMARY:END -->
