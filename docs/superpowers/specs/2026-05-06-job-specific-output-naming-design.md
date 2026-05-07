# Job-Specific Output Organization with Naming Templates

## Overview

Currently, the `tailor` and `re-tailor` commands output all resumes and reports into a single flat directory (default `./output`), with files named `tailored_resume_{company_slug}.md/pdf/docx` and `report_{company_slug}.md`. This makes it hard to organize and track multiple job applications.

This design introduces job-specific subdirectories and user-configurable naming templates, giving the user full control over how their output is organized and named.

## Goals

- Organize outputs into per-job subdirectories instead of a flat folder.
- Allow users to define the subdirectory naming pattern via a template.
- Allow users to define the resume file base name via a template.
- Provide sensible defaults that produce clean, filesystem-safe names.
- Keep backward compatibility with the existing `--output-dir` top-level option.

## Non-Goals

- No migration of old output files — new runs use the new structure, old files stay where they are.
- No GUI or interactive template builder.
- No advanced template-language validation beyond variable substitution and the existing safety checks on resolved directory/file components (for example, rejecting separators, control characters, and absolute paths).

## Architecture

### Template Variables

Both templates support the following variables, which are replaced and then **slugified** (lowercased, spaces → `_`, unsafe chars stripped) to ensure valid directory/file names:

| Variable | Source | Example (slugified) |
|----------|--------|---------------------|
| `{company_name}` | `ResumeTailorResult.company_name` | `google` |
| `{job_title}` | `ResumeTailorResult.job_title` | `senior_software_engineer` |
| `{full_name}` | Parsed from `CV.full_name` in the tailored resume | `john_doe` |
| `{timestamp}` | Current date in `YYYYMMDD` format | `20250506` |

### CLI Options

Added to both `tailor` and `re_tailor` commands:

```python
output_pattern: str = typer.Option(
    "{company_name}-{job_title}",
    help="Template for the job-specific subdirectory name",
)
resume_name_pattern: str = typer.Option(
    "{company_name}-{full_name}",
    help="Template for the resume file base name (without extension)",
)
```

### Path Construction

Given `output_dir="./output"`, `output_pattern="{company_name}-{job_title}"`, and `resume_name_pattern="{company_name}-{full_name}"`:

```
output/
  google-software_engineer/
    google-john_doe.md
    google-john_doe.pdf
    google-john_doe.docx
    google-john_doe_report.md
```

### Report File Naming

The report uses the same `resume_name_pattern` base with `_report` appended:
```
{resume_name_pattern}_report.md
```

This keeps the report visually paired with the resume files in the same directory.

## Components

### `_resolve_pattern(template: str, result: ResumeTailorResult, cv: CV) -> str`

A helper in `main.py` that:
1. Extracts `company_name`, `job_title` from `result`
2. Extracts `full_name` from `cv`
3. Gets current date for `timestamp`
4. Slugifies each extracted value (lowercase, spaces → `_`, unsafe chars stripped)
5. Replaces each `{variable}` in the template with its slugified value

> **Note:** Only the substituted variable values are slugified. Literal characters in the template (spaces, dots, hyphens, etc.) are left unchanged, and any remaining `{unknown}` placeholders are also left as-is. However, the final resolved directory name or base filename must still be a single safe path component. Templates must not produce path separators such as `/` or `\`, and must not include absolute-path indicators, because those values are rejected during path-component validation.

### `generate_resume()` (updated in `markdown_writer.py`)

Updated signature:
```python
def generate_resume(
    result: ResumeTailorResult,
    output_dir: str,
    base_filename: str,
) -> str:
```

- `output_dir` is the already-resolved job-specific directory (created by caller).
- `base_filename` is the slugified resume name pattern result.
- Outputs: `{base_filename}.md`, `{base_filename}.pdf`, `{base_filename}.docx`

### `_run_workflow()` (updated in `main.py`)

After the workflow completes:
1. Parse `result.tailored_resume` into a `CV` object to extract `full_name`
2. Resolve `output_pattern` → `job_dir_name`
3. Create `job_dir = os.path.join(output_dir, job_dir_name)`
4. Resolve `resume_name_pattern` → `resume_base_name`
5. Call `generate_resume(result, job_dir, resume_base_name)`
6. Write report to `{job_dir}/{resume_base_name}_report.md`

### `_tailor_impl()` and `_re_tailor_impl()` (updated in `main.py`)

Pass the new CLI option values through to `_run_workflow()`.

## Data Flow

```
CLI: tailor <url> <resume> --output-pattern="..." --resume-name-pattern="..."
  │
  ▼
_tailor_impl(job_url, resume_path, output_dir, model, output_pattern, resume_name_pattern)
  │
  ▼
_run_workflow(resume_content, job_posting, output_dir, model, recommendations="",
              output_pattern, resume_name_pattern)
  │
  ▼
workflow.run() → ResumeTailorResult (company_name, job_title, tailored_resume, ...)
  │
  ▼
_resolve_pattern(output_pattern, result, cv) → "google-software_engineer"
_resolve_pattern(resume_name_pattern, result, cv) → "google-john_doe"
  │
  ▼
job_dir = "./output/google-software_engineer/"
generate_resume(result, job_dir, "google-john_doe") → writes md/pdf/docx
report_path = "./output/google-software_engineer/google-john_doe_report.md"
```

## Error Handling

- If a template contains an unknown variable (e.g., `{foo}`), it is left as-is in the path. This is acceptable — the user sees the literal string and can fix their template.
- Empty template values (e.g., `company_name` is empty) produce empty string segments. Slugification handles this gracefully.
- Directory creation uses `os.makedirs(..., exist_ok=True)`, so re-running the same command overwrites files in the same directory.

## Testing

### Unit Tests

- `_resolve_pattern()` with all four variables
- `_resolve_pattern()` with unknown variables left untouched
- `_resolve_pattern()` with empty values
- `_run_workflow()` creates the correct directory structure
- `generate_resume()` uses the provided `base_filename`

### Integration Tests

- `tailor` command with custom `--output-pattern` and `--resume-name-pattern`
- `re_tailor` command with custom patterns
- Verify files exist at expected paths after command completes

## Files to Modify

| File | Change |
|------|--------|
| `resume_tailorator/main.py` | Add `--output-pattern` and `--resume-name-pattern` options to `tailor()` and `re_tailor()`. Add `_resolve_pattern()` helper. Modify `_run_workflow()` to compute directories and filenames. Pass patterns through `_tailor_impl` and `_re_tailor_impl`. |
| `resume_tailorator/utils/markdown_writer.py` | Update `generate_resume()` to accept `base_filename` and use it for all output files. Remove internal `company_slug` logic. |
| `tests/test_cli_typer.py` | Add tests for new CLI options and verify directory/file paths. |
| `tests/test_main.py` | Update `_run_workflow` tests to verify directory creation and path resolution. |
| `tests/test_resume_output_converter.py` | Update `generate_resume` tests if behavior changes. |

## Default Behavior Summary

Without any new flags, running `tailor` produces:

```
output/
  {company_name}-{job_title}/
    {company_name}-{full_name}.md
    {company_name}-{full_name}.pdf
    {company_name}-{full_name}.docx
    {company_name}-{full_name}_report.md
```

Example for a Google Senior Software Engineer application:

```
output/
  google-senior_software_engineer/
    google-john_doe.md
    google-john_doe.pdf
    google-john_doe.docx
    google-john_doe_report.md
```
