---
id: TASK-20
title: 'T-20: Accessibility audit and end-to-end smoke test'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
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
- [ ] #1 Every interactive element is keyboard-operable with an accessible name and meets AA contrast in both themes (S11.7).
- [ ] #2 An automated accessibility scan of the session list, the workspace in each stage panel, every gate card and the completion view reports no AA violations.
- [ ] #3 The Playwright smoke test passes end to end and downloads a zip containing every available kind (S10.8).
- [ ] #4 Five sessions driven concurrently with the fake models all complete with correct, independent state (NFR-12).
<!-- AC:END -->
