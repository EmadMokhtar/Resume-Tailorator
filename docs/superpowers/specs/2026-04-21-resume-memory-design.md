# Resume Memory System Design

## Overview

The CLI currently reads `files/resume.md` and reparses it on every job submission. That keeps the flow simple, but it repeats expensive work and mixes two separate concerns: resume ingestion and job-specific tailoring.

This design introduces a dedicated resume memory subsystem that persists the latest known resume and its parsed `CV` representation. The subsystem uses a repository pattern so the CLI and workflow remain storage-agnostic. The first backend is local SQLite.

## Goals

- Reuse a parsed resume when the effective resume has not changed.
- Reparse automatically when the resume content changes.
- Default to the latest stored resume when the user does not provide a resume path.
- Keep persistence behind a repository interface so new storage backends can be added later.
- Keep the existing tailoring workflow focused on job analysis and resume rewriting, not resume caching.

## Non-Goals

- Supporting multiple active resumes at the same time.
- Designing remote or shared multi-user storage in this first iteration.
- Persisting full job-submission history as part of the memory subsystem.
- Changing the writer, reviewer, or auditor agent behavior.

## Proposed Architecture

### Command layer

The CLI remains responsible for resolving the optional resume path argument for the current run.

- If the user provides a resume path, that path becomes the effective resume source for the run.
- If the user does not provide a resume path, the CLI asks the memory service for the latest stored resume.
- If no stored resume exists, the CLI fails early with a clear message telling the user to provide a resume path first.

### Resume memory service

`ResumeMemoryService` owns the application logic for:

- resolving the effective resume source
- reading resume file contents
- computing a content hash
- checking whether the stored parsed resume is still valid
- reparsing when the source changed or the parser version changed
- returning a structured `CV` object to the workflow

The service depends on two abstractions:

- `ResumeMemoryRepository` for persistence
- `ResumeParser` adapter for producing a `CV` from raw markdown

### Repository layer

`ResumeMemoryRepository` defines the persistence contract. The CLI and workflow must depend only on this contract through the service. The first implementation is `SQLiteResumeMemoryRepository`.

### Workflow boundary

The tailoring workflow should no longer parse raw resume markdown internally on every run. Instead, it should receive a ready structured `CV` from the memory service. This keeps resume ingestion and resume tailoring as separate responsibilities.

## Components

### `ResumeMemoryRepository`

Suggested contract:

- `get_active_source() -> ResumeSourceRecord | None`
- `get_latest_source() -> ResumeSourceRecord | None`
- `get_source_by_path(path: str) -> ResumeSourceRecord | None`
- `upsert_source(path: str, content_hash: str, is_active: bool) -> ResumeSourceRecord`
- `get_parsed_resume(source_id: str) -> ParsedResumeRecord | None`
- `save_parsed_resume(source_id: str, content_hash: str, parser_version: str, cv_json: str) -> ParsedResumeRecord`
- `set_active_source(source_id: str) -> None`

This interface is intentionally narrow. It exposes storage primitives, not business rules.

### `SQLiteResumeMemoryRepository`

The SQLite implementation maps the repository contract onto local tables and hides SQL details from the rest of the app.

### `ResumeMemoryService`

Suggested public behaviors:

- `resolve_resume(optional_path: str | None) -> CV`
- `import_resume(path: str) -> CV`
- `get_latest_resume() -> CV`

The service decides whether the parsed resume can be reused or must be refreshed.

### `ResumeParser`

This adapter wraps the existing `resume_parser_agent`. It gives the memory service a clean parsing dependency without coupling the service directly to workflow orchestration details.

## SQLite Data Model

The first version should use two tables.

### `resume_sources`

Stores the latest known metadata about each resume source.

- `id`
- `path`
- `content_hash`
- `is_active`
- `created_at`
- `updated_at`
- `last_seen_at`

Exactly one source should be marked active at a time. When the user provides a new resume path, that source becomes the active source and previously active sources are deactivated.

### `parsed_resumes`

Stores the latest parsed output for a source.

- `source_id`
- `content_hash`
- `parser_version`
- `cv_json`
- `created_at`
- `updated_at`

This keeps source metadata separate from derived parser output. The `parser_version` field is required so the system can invalidate cached parsed data if the `CV` schema or parsing logic changes.

## Runtime Flow

### Case 1: user provides a resume path

1. CLI passes the path to `ResumeMemoryService`.
2. Service reads the file and computes its content hash.
3. Service upserts the source record and marks it active.
4. Service loads the stored parsed resume for that source.
5. If the stored hash and parser version still match, service returns the cached `CV`.
6. Otherwise, service calls the parser, persists the fresh parsed result, and returns the new `CV`.

### Case 2: user does not provide a resume path

1. CLI asks the service for the latest stored resume.
2. Service loads the active source.
3. If no source exists, service raises a clear domain error.
4. Service re-reads the file at the stored path and computes the current content hash.
5. If the file still matches the stored parsed result and parser version, service returns the cached `CV`.
6. Otherwise, service reparses, persists, and returns the refreshed `CV`.

If the active-source invariant is broken in storage, the service may fall back to the latest source as a defensive recovery path, but that is an implementation safeguard rather than the normal rule.

## Cache Invalidation Rules

The parsed resume is invalid and must be regenerated when any of the following is true:

- the effective resume path is new
- the file content hash changed
- the parser version changed
- no parsed resume exists for the resolved source

Otherwise, the cached parsed `CV` is reused.

## Error Handling

Errors should be explicit rather than silently bypassing memory.

- **No stored resume and no input path**: fail early with a message asking the user to provide a resume path.
- **Resume file missing or unreadable**: fail the run before job tailoring starts.
- **SQLite unavailable or corrupted**: raise a persistence error instead of pretending memory is optional.
- **Resume parsing fails**: keep the previous valid parsed record untouched and fail the current run clearly.
- **Stored path no longer exists**: fail with a message that the saved resume is unavailable and a new path must be provided.

## Testing Strategy

### Service tests

Cover:

- explicit path overrides stored default
- missing path falls back to latest stored resume
- cache hit when hash and parser version match
- reparse when file content changes
- reparse when parser version changes
- clear failure when no resume is available

### Repository tests

Cover:

- insert and update behavior for source records
- active-source switching
- parsed resume persistence and retrieval
- latest-source lookup

### Integration tests

Cover:

- first run imports and parses a resume
- second run reuses cached parsed data
- editing the same file triggers reparse
- workflow receives structured `CV` from memory rather than reparsing internally

## Why This Design

This design solves the immediate problem without overbuilding. It introduces a clear boundary for resume memory, keeps SQLite as a local-first implementation detail, and leaves space for future backends without leaking storage logic into the CLI or workflow. It also improves correctness by making cache invalidation explicit and testable.
