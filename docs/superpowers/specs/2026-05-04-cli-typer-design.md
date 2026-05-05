# CLI with Typer - Design Spec

## Overview

CLI using Typer with two subcommands: `tailor` and `re-tailor`. Remove all environment variable fallbacks.

## Commands

### `tailor`

Run the full resume tailoring workflow.

**Usage:**
```
resume-tailor tailor <job_url> <resume_path> [options]
```

**Arguments:**
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `job_url` | Yes | - | URL of job posting to scrape |
| `resume_path` | Yes | - | Path to resume (Markdown, DOCX, PDF) |
| `--output-dir` | No | `./output` | Directory for output files |
| `--model` | No | None | AI model to use (e.g., `openai:gpt-4o-mini`) |

**Behavior:**
1. Validate inputs (URL format, file exists)
2. Scrape job posting → convert to markdown
3. Run ResumeTailorWorkflow
4. Save tailored CV (if audit passed) and report
5. Store job metadata in SQLite via memory service
6. Print job ID to stdout

**Output on success:**
```
✅ Job completed: <company> / <job_title>
📄 Tailored CV: <path>
📊 Report: <path>
Job ID: <uuid>
```

### `re-tailor`

Re-run tailoring with recommendations from a prior audit.

**Usage:**
```
resume-tailor re-tailor <job_id> <recommendations> [options]
```

**Arguments:**
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `job_id` | Yes | - | UUID of prior job |
| `recommendations` | Yes | - | Comments/recommendations from prior audit |
| `--resume-path` | No | - | Path to resume (uses stored path if omitted) |
| `--output-dir` | No | `./output` | Directory for output files |
| `--model` | No | None | AI model to use |

**Behavior:**
1. Retrieve prior job from database by ID
2. Load stored resume content and job posting markdown
3. Run workflow with recommendations applied
4. Save updated CV and report
5. Update job record with new results

**Output on success:**
```
✅ Re-tailoring completed: <company> / <job_title>
📄 Updated CV: <path>
📊 Updated Report: <path>
```

## Job Storage

Use existing SQLite database via memory service.

**Table:** `tailored_resumes` (via `SQLiteResumeMemoryRepository`)

**Fields stored per job:**
- `id` (UUID, primary key)
- `source_id` (FK to original_resume_sources)
- `job_fingerprint`
- `company_name`
- `job_title`
- `tailored_cv_json`
- `audit_report_json`
- `job_posting_markdown`
- `created_at`
- `updated_at`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Missing required arg | Exit 1, Typer error with usage hint |
| Invalid URL format | Exit 1, clear error message |
| Resume file not found | Exit 1, print error with path |
| Job ID not found | Exit 1, "Job not found: <id>" |
| Scraping failure | Exit 1, tip about public URL |
| Workflow audit failed | Save report, print feedback, exit 0 |

## Exit Codes

- `0`: Success (even if audit failed - still generated report)
- `1`: Fatal error (missing file, invalid input, scraping failed)

## Implementation Notes

1. Remove all `os.getenv` / environment variable fallback code
2. Use Typer's `typer.Argument` and `typer.Option` decorators
3. Commands as `typer.Typer()` subcommands (sync, with internal `asyncio.run()`)
4. Use `SQLiteResumeMemoryRepository` + `ResumeMemoryService` for job persistence
5. Keep existing markdown report output format
6. Console output uses emoji prefix for readability
7. `generate_resume()` uses slugified company name for consistent filenames

## File Changes

- `main.py`: Rewrite as Typer app with two commands
- `memory/sqlite_repository.py`: Add `get_source_by_id` + schema migration
- `memory/repository.py`: Add `get_source_by_id` to ABC
- `utils/markdown_writer.py`: Return path from `generate_resume()`, use slugified name
- `docs/superpowers/specs/2026-05-04-cli-typer-design.md`: This file
- Tests: `tests/test_cli_typer.py` - sync calls, add re_tailor tests
