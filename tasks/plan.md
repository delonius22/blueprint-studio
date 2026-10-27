# Plan: document import (SPEC-document-import.md)

## Approach
Vertical order, each step green before the next:

1. **Reading files** (pure): `imports/files.py` checks type, size and length and turns a file into
   sections; `imports/outline.py` turns Mermaid and draw.io into an outline. No model, no I/O.
2. **Storing files**: an `attachments` table in both stores (Postgres and SQLite), on the
   existing `SessionStore`. File bytes never enter the checkpoint.
3. **Import logic** (pure): `imports/proposal.py` holds the proposal schema the model answers with, turns it
   into candidates (quote check, step, staging), applies the user's decisions through
   `run_tool`, and writes the interviewer's "Imported material" note.
4. **Graph**: an `importer` node (one structured call per new attachment) and an
   `import_applier` node (no model) answering the new `review_import` gate; the critic offers
   staged candidates when a step opens; the interviewer and PRD drafter get the new context.
5. **API**: upload, list, remove and content routes; the run-start sync of attachment refs
   from the store into state (server-owned, so the browser never writes them); vision probe.
6. **Web**: binary-safe proxy, attach control, sources panel, `ReviewImportCard`, source badges.
7. **Docs**: merge into PRD.md and SPECS.md; README.

## Decisions taken while planning (spec updated to match)
- OQ-I1 is settled without a spike: `SessionAgent.run` already merges state at run start;
  it now also copies the store's attachment refs into state.
- Upload is a raw body (`?name=`), not multipart: no `python-multipart` dependency.
- No `defusedxml`: expat 2.7.4 in Python 3.14 refuses entity-expansion bombs (tested).
- Invalid candidates are dropped, not retried; storage choices import as `proposed` only.
- OQ-I6 (`read_attachment` tool) deferred; not built.

## Risks
- Strict JSON schema for the proposal: built from the upsert tools' argument models, which
  already pass strict mode in the interviewer's tool calls.
- Images depend on the provider accepting `image_url` parts; the vision probe gates them.

## Then
Code review for maintainability and readability (folder structure, dead code,
shared helpers), then simplification.
