# CLI with Typer - Design Spec

## Overview

Rewrite the CLI using Typer instead of argparse, with two subcommands: `tailor` and `re-tailor`. Remove all environment variable fallbacks.

## Commands

### `tailor`

Run the full resume tailoring workflow.

**Usage:**
```
resume-tailor tailor <job-url> <resume-path> [options]
```

**Arguments:**
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `JOB_URL` | Yes | - | URL of job posting to scrape |
| `RESUME_PATH` | Yes | - | Path to resume (Markdown, DOCX, PDF) |
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
resume-tailor re-tailor <job-id> <recommendations> [options]
```

**Arguments:**
| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `JOB_ID` | Yes | - | UUID of prior job |
| `RECOMMENDATIONS` | Yes | - | Comments/recommendations from prior audit |
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

**Tables:**
- `original_resume_sources` — stores the original resume file path and content
- `parsed_original_resumes` — stores the structured parsed resume linked to a source
- `tailored_resumes` — stores each tailoring run with job posting, tailored CV, audit result, and link to the original source

**Fields stored per tailoring run (`tailored_resumes`):**
- `id` (UUID, primary key)
- `source_id` (FK to `original_resume_sources`)
- `company_name`
- `job_title`
- `job_posting_markdown`
- `tailored_resume`
- `audit_result`
- `report`
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
3. Commands as `typer.Typer()` subcommands
4. Use existing memory service for job storage (check existing repository interface)
5. Keep existing markdown report output format
6. Console output uses emoji prefix for readability

## File Changes

- `main.py`: Rewrite as Typer app with two commands
- `utils/validate_inputs.py`: Remove `os.getenv` fallback, keep validation logic
- Tests: Update to use new CLI interface
