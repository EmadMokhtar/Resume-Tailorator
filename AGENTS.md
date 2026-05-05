# AGENTS.md — Resume Tailorator

## Quickstart

```bash
uv sync                        # install dev deps
export OPENAI_API_KEY=sk-…
uv run resume-tailor tailor <JOB_URL> <RESUME_PATH>          # scrape + tailor
uv run resume-tailor re-tailor <JOB_ID> <RECOMMENDATIONS>    # re-run with feedback
```

## CLI Commands

Two Typer subcommands in `resume_tailorator/main.py`:

| Command | Signature | Description |
|---------|-----------|-------------|
| `tailor` | `tailor JOB_URL RESUME_PATH [--output-dir] [--model]` | Scrape job posting, run full pipeline |
| `re-tailor` | `re-tailor JOB_ID RECOMMENDATIONS [--resume-path] [--output-dir] [--model]` | Re-run with prior audit feedback |

A console script is registered: `resume-tailor` → `resume_tailorator.main:run` (see `pyproject.toml`).

## Execution & Commands

| Command | How to run | Description |
|---------|------------|-------------|
| `tailor` | `uv run resume-tailor tailor <URL> <PATH>` | Scrape job posting and run the agentic workflow. |
| `re-tailor` | `uv run resume-tailor re-tailor <ID> <RECS>` | Re-run tailoring with prior audit recommendations. |
| `test` | `make test` or `uv run pytest -v` | Run the full test suite. |
| `install/dev` | `make install/dev` or `uv sync` | Install development dependencies (incl. `pytest`, `ruff`). |
| `help` | `make help` | Show Makefile targets. |

> **Note**: The Makefile `run` target is deprecated and uses broken paths. Use `uv run resume-tailor tailor` instead.

### Environment

- **Python** `3.13+` managed by `uv`. (`.python-version` pins 3.13)
- **Required env var**: `OPENAI_API_KEY`.

### Inputs

- Both CLI commands use **positional arguments** (not interactive prompts).
- `tailor` requires a job URL (scraped via Playwright) and a resume path (`.md`, `.docx`, or `.pdf`).
- `re-tailor` requires a job ID (UUID from a prior `tailor` run) and recommendations text. It uses the stored job posting and resolved resume.
- `resume_tailorator/utils/` contains:
  - `validate_inputs.py` — Standalone input validation script (not used by the Typer CLI).
  - `resume_converter.py` — Converts DOCX/PDF to Markdown via `markitdown`.
  - `markdown_writer.py` — Generates Markdown output for resumes and reports.
  - `cv_diff.py` — Computes structural diffs and gap analysis between original and tailored CVs.
  - `pdf_converter.py` — PDF creation helpers.
  - `resume_output_converter.py` — Resume output conversion utilities.

## Architecture

Single package: `resume_tailorator/`

| Directory | Purpose |
|-----------|---------|
| `resume_tailorator/workflows/` | Workflow orchestration (`ResumeTailorWorkflow`) and agent definitions |
| `resume_tailorator/models/` | Pydantic data models (agents output types, workflow result) |
| `resume_tailorator/memory/` | SQLite-backed memory (parser, repository, service) |
| `resume_tailorator/tools/` | Playwright scraping, HTML→Markdown parsing, placeholder detection |
| `resume_tailorator/utils/` | Markdown writer, resume conversion, CV diff, PDF converter, validation |
| `output/` | Default output directory for generated files |

### Multi-Agent Pipeline (6 Stages)

1. **Resume Parser** — parses Markdown/DOCX/PDF resume into structured `CV` object.
2. **Job Analyst** — extracts structured `JobAnalysis` (title, company, skills, keywords).
3. **CV Writer** — tailors CV to match job requirements using only original content.
4. **Reviewer** — scores draft quality and provides improvement suggestions (feeds refinement loop).
5. **Auditor** — checks for hallucinations and AI clichés; triggers write-retry loop on failure.
6. **Report Generator** — compiles `FinalReport` with CVDiff, gap analysis, and narrative.

The **Write → Review → Audit** inner loop: after the initial write, the reviewer assesses quality and the writer refines. The auditor then checks the final draft. If audit fails, the entire loop retries (up to 3 write attempts).

### Agents Defined (in `workflows/agents.py`)

| Agent | Output Type | Has Quality Gate |
|-------|------------|-----------------|
| `job_scraper_agent` | `ScrapedJobPosting` | No (has `validate_extraction` tool) |
| `resume_parser_agent` | `CV` | Yes |
| `analyst_agent` | `JobAnalysis` | Yes |
| `writer_agent` | `CV` | Yes |
| `reviewer_agent` | `ReviewResult` | No |
| `auditor_agent` | `AuditResult` | Yes |
| `report_agent` | `FinalReport` | No |
| `cover_letter_writer_agent` | `str` | Yes (defined but not wired into workflow) |
| `quality_gate_agent` | `QualityCheckResult` | N/A (this is the gate itself) |

### Technology Stack

- **Framework**: `pydantic-ai` (agent orchestration)
- **LLM**: OpenAI GPT (configurable; default `openai:gpt-5-mini`)
- **Models**: Pydantic v2 for structured outputs
- **CLI**: Typer with two subcommands (`tailor`, `re-tailor`)
- **Web Scraping**: Playwright (headless Chromium)
- **HTML→Markdown**: `html2text` and `markitdown` (multi-strategy fallback)
- **Resume Conversion**: `markitdown` (DOCX/PDF → Markdown)
- **Memory**: SQLite (`files/resume_memory.sqlite3`)
- **Formatting**: `ruff`

## Testing

```bash
uv run pytest -v
```

- Test config lives in `pyproject.toml` (`[tool.pytest.ini_options]`).
- `tests/conftest.py` disables real LLM calls when testing (`models.ALLOW_MODEL_REQUESTS = False`).
- All tests use a dummy `OPENAI_API_KEY`; no real API calls are made.

## Style & Linting

- Python style enforced by `ruff` (see `pyproject.toml` dev dependencies).
- No pre-commit hooks or CI workflows configured.

## Key Conventions

- **Never hallucinate**: Agents must only rephrase existing content, never invent skills or experiences.
- **Anti-cliché**: Avoid terms like "spearheaded", "synergy", "leveraged", "game-changer".
- **Quality Gates**: Each agent output is scored 0–10 by a quality gate validator; score < 9 triggers retry.
- **Resume formats**: Accepts `.md`, `.docx`, `.pdf`; DOCX/PDF are converted to Markdown before processing.
- **Memory**: Each `tailor` run stores the original resume, tailored CV, audit result, and job posting in SQLite. `re-tailor` reuses the stored job posting.
- **Output**: Tailored resumes and reports are saved to `output/` (overridable via `--output-dir`).

## Other Instruction Files

- `.github/copilot-instructions.md` — Additional agent-specific guidelines and anti-hallucination rules.
