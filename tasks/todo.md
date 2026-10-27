# Tasks: document import

- [x] T1 Reading files: imports/files.py, imports/outline.py, pypdf
  - Acceptance: each kind parses to sections; every refusal has its code; Mermaid round-trips
  - Verify: uv run pytest tests/test_import_files.py
- [x] T2 Storing files: attachments table in Postgres and SQLite, cascade on session delete
  - Verify: uv run pytest tests/test_attachment_store.py
- [x] T3 Import logic: imports.py, new state fields and ID prefixes
  - Verify: uv run pytest tests/test_imports.py
- [x] T4 Graph: importer, import_applier, review_import gate, staging on step change, prompts, vision probe
  - Verify: uv run pytest tests/test_import_graph.py
- [x] T5 API: attachment routes, run-start sync, OpenAPI
  - Verify: uv run pytest tests/test_attachments_api.py
- [x] T6 Web: proxy, attach control, sources panel, ReviewImportCard, source badges, api types
  - Verify: npx tsc --noEmit && npm test
- [x] T7 Docs: PRD.md, SPECS.md, README.md
- [x] Review: maintainability and readability, structure, dead code, shared helpers
- [x] Simplify
