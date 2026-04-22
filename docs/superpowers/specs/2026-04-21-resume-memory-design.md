# Resume Memory System Design

## Overview

The CLI currently reads `files/resume.md` and reparses it on every job submission. That keeps the flow simple, but it repeats expensive work and mixes two separate concerns: resume ingestion and job-specific tailoring.

This design introduces a dedicated resume memory subsystem that persists both the original resume and job-specific tailored outputs. The subsystem stores the latest known original resume, its parsed `CV` representation, and the tailored result generated for each job submission. The subsystem uses a repository pattern so the CLI and workflow remain storage-agnostic. The first backend is local SQLite.

## Goals

- Reuse a parsed original resume when the effective original resume has not changed.
- Reparse the original resume automatically when its content changes.
- Default to the latest stored original resume when the user does not provide a resume path.
- Store the original resume and the tailored resume generated for each job submission.
- Ensure every job submission starts from the original resume, never from a previously tailored resume.
- Keep persistence behind a repository interface so new storage backends can be added later.
- Keep the existing tailoring workflow focused on job analysis and resume rewriting, not resume caching.

## Non-Goals

- Supporting multiple active resumes at the same time.
- Designing remote or shared multi-user storage in this first iteration.
- Using a tailored resume as the source for a future job submission.
- Changing the writer, reviewer, or auditor agent behavior.

## Proposed Architecture

### Command layer

The CLI remains responsible for resolving the optional original-resume path argument for the current run.

- If the user provides a resume path, that path becomes the effective original resume source for the run.
- If the user does not provide a resume path, the CLI asks the memory service for the latest stored original resume.
- If no original resume exists, the CLI fails early with a clear message telling the user to provide a resume path for the first run.

### Resume memory service

`ResumeMemoryService` owns the application logic for:

- resolving the effective original resume source
- reading original resume file contents
- computing a content hash
- checking whether the stored parsed original resume is still valid
- reparsing when the source changed or the parser version changed
- returning a structured original `CV` object to the workflow
- persisting the tailored resume produced for each job submission

The service depends on two abstractions:

- `ResumeMemoryRepository` for persistence
- `ResumeParser` adapter for producing a `CV` from raw markdown

### Repository layer

`ResumeMemoryRepository` defines the persistence contract for original and tailored resume records. The CLI and workflow must depend only on this contract through the service. The first implementation is `SQLiteResumeMemoryRepository`.

### Workflow boundary

The tailoring workflow should no longer parse raw resume markdown internally on every run. Instead, it should receive a ready structured original `CV` from the memory service. After the workflow finishes successfully, the tailored resume should be stored as a job-specific record linked back to the original source used for that run. This keeps original resume ingestion, job-specific tailoring, and persistence as separate responsibilities.

## Components

### `ResumeMemoryRepository`

Suggested contract:

- `get_active_original_source() -> ResumeSourceRecord | None`
- `get_latest_original_source() -> ResumeSourceRecord | None`
- `get_source_by_path(path: str) -> ResumeSourceRecord | None`
- `upsert_original_source(path: str, content_hash: str, is_active: bool) -> ResumeSourceRecord`
- `get_parsed_original_resume(source_id: str) -> ParsedResumeRecord | None`
- `save_parsed_original_resume(source_id: str, content_hash: str, parser_version: str, cv_json: str) -> ParsedResumeRecord`
- `set_active_original_source(source_id: str) -> None`
- `save_tailored_resume(source_id: str, job_fingerprint: str, company_name: str, job_title: str, tailored_cv_json: str, audit_report_json: str) -> TailoredResumeRecord`
- `get_tailored_resume(job_fingerprint: str) -> TailoredResumeRecord | None`

This interface is intentionally narrow. It exposes storage primitives, not business rules.

### `SQLiteResumeMemoryRepository`

The SQLite implementation maps the repository contract onto local tables and hides SQL details from the rest of the app.

### `ResumeMemoryService`

Suggested public behaviors:

- `resolve_original_resume(optional_path: str | None) -> CV`
- `import_original_resume(path: str) -> CV`
- `get_latest_original_resume() -> CV`
- `store_tailored_resume(source_id: str, job_fingerprint: str, result: ResumeTailorResult) -> None`

The service decides whether the parsed original resume can be reused or must be refreshed. It also persists the tailored output for each completed job submission.

### `ResumeParser`

This adapter wraps the existing `resume_parser_agent`. It gives the memory service a clean parsing dependency without coupling the service directly to workflow orchestration details.

## SQLite Data Model

The first version should use three tables.

### `original_resume_sources`

Stores the latest known metadata about each original resume source.

- `id`
- `path`
- `content_hash`
- `is_active`
- `created_at`
- `updated_at`
- `last_seen_at`

Exactly one original source should be marked active at a time. When the user provides a new resume path, that source becomes the active original source and previously active sources are deactivated.

### `parsed_original_resumes`

Stores the latest parsed output for an original resume source.

- `source_id`
- `content_hash`
- `parser_version`
- `cv_json`
- `created_at`
- `updated_at`

This keeps original source metadata separate from derived parser output. The `parser_version` field is required so the system can invalidate cached parsed data if the `CV` schema or parsing logic changes.

### `tailored_resumes`

Stores the tailored output generated for each job submission.

- `id`
- `source_id`
- `job_fingerprint`
- `company_name`
- `job_title`
- `tailored_cv_json`
- `audit_report_json`
- `created_at`
- `updated_at`

Each tailored resume record must reference the original resume source used to create it. The system never promotes a tailored resume into the original source table.

## Runtime Flow

### Case 1: user provides an original resume path

1. CLI passes the path to `ResumeMemoryService`.
2. Service reads the file and computes its content hash.
3. Service upserts the original source record and marks it active.
4. Service loads the stored parsed original resume for that source.
5. If the stored hash and parser version still match, service returns the cached `CV`.
6. Otherwise, service calls the parser, persists the fresh parsed result, and returns the new `CV`.
7. The tailoring workflow runs against that original `CV`.
8. When tailoring completes, the service stores the tailored resume as a job-specific record linked to the original source.

### Case 2: user does not provide a resume path

1. CLI asks the service for the latest stored original resume.
2. Service loads the active original source.
3. If no source exists, service raises a clear domain error.
4. Service re-reads the file at the stored path and computes the current content hash.
5. If the file still matches the stored parsed result and parser version, service returns the cached `CV`.
6. Otherwise, service reparses, persists, and returns the refreshed `CV`.
7. The tailoring workflow runs against that original `CV`.
8. When tailoring completes, the service stores the tailored resume as a job-specific record linked to the original source.

If the active-source invariant is broken in storage, the service may fall back to the latest original source as a defensive recovery path, but that is an implementation safeguard rather than the normal rule.

## Job Submission Rule

Every job submission must begin from the original resume resolved for that run. The system must never use a previously tailored resume as the input for another tailoring pass.

## Cache Invalidation Rules

The parsed original resume is invalid and must be regenerated when any of the following is true:

- the effective resume path is new
- the file content hash changed
- the parser version changed
- no parsed resume exists for the resolved source

Otherwise, the cached parsed original `CV` is reused.

## Error Handling

Errors should be explicit rather than silently bypassing memory.

- **No stored original resume and no input path**: fail early with a message asking the user to provide a resume path for the first run.
- **Resume file missing or unreadable**: fail the run before job tailoring starts.
- **SQLite unavailable or corrupted**: raise a persistence error instead of pretending memory is optional.
- **Original resume parsing fails**: keep the previous valid parsed record untouched and fail the current run clearly.
- **Stored path no longer exists**: fail with a message that the saved resume is unavailable and a new path must be provided.
- **Tailored resume persistence fails**: fail the job submission instead of reporting a successful completed run with missing memory state.

## Testing Strategy

### Service tests

Cover:

- explicit path overrides stored default
- missing path falls back to latest stored original resume
- cache hit when hash and parser version match
- reparse when file content changes
- reparse when parser version changes
- clear failure when no original resume is available
- tailored result is stored after a successful job submission

### Repository tests

Cover:

- insert and update behavior for source records
- active-original-source switching
- parsed original resume persistence and retrieval
- latest-original-source lookup
- tailored resume persistence and retrieval by job fingerprint

### Integration tests

Cover:

- first run imports and parses a resume
- second run reuses cached parsed data
- editing the same file triggers reparse
- workflow receives the original structured `CV` from memory rather than reparsing internally
- tailored output is stored and linked back to the original source used for the run
- a later job submission still starts from the original resume, not the prior tailored one

## Why This Design

This design solves the immediate problem without overbuilding. It introduces a clear boundary for original-resume memory and tailored-resume storage, keeps SQLite as a local-first implementation detail, and leaves space for future backends without leaking storage logic into the CLI or workflow. It also improves correctness by making the “always start from the original resume” rule explicit and testable.
