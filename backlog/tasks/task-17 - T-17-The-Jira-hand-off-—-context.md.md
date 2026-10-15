---
id: TASK-17
title: 'T-17: The Jira hand-off — context.md'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-14 22:19'
updated_date: '2026-10-15 02:00'
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
- [x] #1 `context.md` follows the six-part template of S10.7 in order, with the default mapping rows exactly as listed.
- [x] #2 Every feature, story and ticket of the current PRD and breakdown appears with every field; every open gap appears under its feature (S10.7, S7.1).
- [x] #3 The rules include every stop-and-ask condition in S10.7, including the existing-issue check.
- [x] #4 The file ends with the attribution line of S12.3.
- [x] #5 An export-seam test compares a rendered context.md for a fixture session against a checked-in expected file, byte for byte.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
blueprint.exports.context_md renders the S10.7 template exactly as the worked example docs/context.md lays it out (role, Jira project with blank Site/Project key lines, mapping table with the default rows, rules incl. every stop-and-ask condition and the existing-issue check, features, user stories, tickets, open gaps, report) and ends with the to-tickets/to-spec attribution (S12.3). Items come from the current PRD and the approved tickets with every field; Summary lines per S10.7 ("<ID>: <I want text, capitalised>" for stories); each ticket's parent feature is derived from its first story; each open gap is listed under every feature it concerns. Fields the worked example lacks because its project had none (feature description, story acceptance criteria, ticket kind) are included because S10.7 asks for every field. The fixed sections are tested byte-for-byte against docs/context.md, and a fixture rendering against tests/expected/context.md.
Validation: agent tests incl. byte comparisons, REST 409/200; key scan covers context.md.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Once tickets are approved, context.md is downloadable: a self-contained Jira hand-off with the editable mapping table, hard rules against adding anything (including the stop-and-ask conditions and the existing-issue check), every feature, story and ticket with every field and Summary line, the open gaps under their features, the required report format and the attribution line. Verified byte for byte against a checked-in expected file and against the worked example's template.
<!-- SECTION:FINAL_SUMMARY:END -->
