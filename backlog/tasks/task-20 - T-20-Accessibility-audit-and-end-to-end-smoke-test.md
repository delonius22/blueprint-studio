---
id: TASK-20
title: 'T-20: Accessibility audit and end-to-end smoke test'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 11:48'
labels: []
dependencies:
  - TASK-9
  - TASK-18
  - TASK-19
references:
  - TICKETS.md
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every screen, panel and card is usable by keyboard and screen reader and meets WCAG 2.1 AA. One Playwright test drives a short session through the full stack with scripted fake models, from creating a session to downloading the zip, and five sessions run concurrently with independent state.

Delivers stories: US-49, US-54

Mirrors T-20 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every interactive element is keyboard-operable with an accessible name and meets AA contrast in both themes (S11.7).
- [x] #2 An automated accessibility scan of the session list, the workspace in each stage panel, every gate card and the completion view reports no AA violations.
- [x] #3 The Playwright smoke test passes end to end and downloads a zip containing every available kind (S10.8).
- [x] #4 Five sessions driven concurrently with the fake models all complete with correct, independent state (NFR-12).
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
End-to-end smoke test (web/e2e/smoke.spec.ts) runs the real compose stack with a stdlib OpenAI-compatible fake model service (web/e2e/fake_model.py, docker-compose.e2e.yml) playing both roles by content, so five sessions run in parallel: create session, five steps with a reject-then-approve gate, design review with an accepted gap, PRD v1.0 sign-off, seams v1.1, proposed changes v1.2, tickets, completion and zip download. Each session checks its zip entries, that context.md holds only its own design, and the REST state.
Session 1 also runs axe (wcag2a/aa, wcag21a/aa) in light and dark on the session list, canvas, every gate card, PRD viewer, ticket view and completion view, and drives session creation and a step-confirmation gate by keyboard alone.
Accessibility fixes found by the audit: an accessible name for the chat send button and no unlabeled add-menu button (Workspace.tsx), a focusable labelled workspace region for scrollable content, and an explicit foreground colour on gate cards for dark-mode contrast.
docker-compose.yml: the agent's .env is now optional (required: false) so the e2e override can run without one; the real stack still reads it.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the Playwright smoke test over the full compose stack with scripted fake models: five parallel sessions go from creation to zip download, each verifying its own documents and state, and the first audits every screen, panel and gate card with axe in both themes plus keyboard-only operation. Fixed the three accessibility violations the audit found. Run with `cd web && npm run test:e2e`.
<!-- SECTION:FINAL_SUMMARY:END -->
