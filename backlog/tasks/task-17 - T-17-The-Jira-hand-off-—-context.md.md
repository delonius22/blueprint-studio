---
id: TASK-17
title: 'T-17: The Jira hand-off — context.md'
status: To Do
assignee: []
created_date: '2026-10-14 22:19'
labels: []
dependencies:
  - TASK-15
references:
  - TICKETS.md
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Once tickets are approved, the user can download context.md: a self-contained prompt any agent can follow to create the Jira issues, with an editable mapping table, hard rules against adding anything, the embedded features, stories, tickets and open gaps, and a required report format.

Delivers stories: US-39, US-40, US-41, US-42

Mirrors T-17 in TICKETS.md, which is authoritative.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `context.md` follows the six-part template of S10.7 in order, with the default mapping rows exactly as listed.
- [ ] #2 Every feature, story and ticket of the current PRD and breakdown appears with every field; every open gap appears under its feature (S10.7, S7.1).
- [ ] #3 The rules include every stop-and-ask condition in S10.7, including the existing-issue check.
- [ ] #4 The file ends with the attribution line of S12.3.
- [ ] #5 An export-seam test compares a rendered context.md for a fixture session against a checked-in expected file, byte for byte.
<!-- AC:END -->
