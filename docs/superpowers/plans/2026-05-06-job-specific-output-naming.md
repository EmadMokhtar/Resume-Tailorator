# Job-Specific Output Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Organize resume and report outputs into per-job subdirectories with user-configurable naming templates.

**Architecture:** Add a `_resolve_pattern()` helper that slugifies template variables, update `generate_resume()` to accept a base filename, modify `_run_workflow()` to compute job-specific directories and filenames, and wire new CLI options through both `tailor` and `re_tailor` commands.

**Tech Stack:** Python 3.13, Typer, pytest, rich console, pathlib

---

## File Structure

| File | Responsibility |
|------|---------------|
| `resume_tailorator/main.py` | CLI commands, `_resolve_pattern()` helper, `_run_workflow()` orchestration, `_tailor_impl()`, `_re_tailor_impl()` |
| `resume_tailorator/utils/markdown_writer.py` | `generate_resume()` — writes md/pdf/docx files given a base filename |
| `tests/test_cli_typer.py` | Integration tests for CLI commands with new options |
| `tests/test_main.py` | Unit tests for `_resolve_pattern()` and `_run_workflow()` directory logic |

---

### Task 1: Add `_resolve_pattern()` helper to `main.py`

**Files:**
- Modify: `resume_tailorator/main.py:36-43` (after `_get_company_slug` / `_get_job_fingerprint`)
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_main.py` (new tests at the end, or in a new test file `tests/test_pattern_resolution.py`):

```python
from datetime import date

import pytest

from resume_tailorator.main import _resolve_pattern
from resume_tailorator.models.agents.output import CV, WorkExperience
from resume_tailorator.models.workflow import ResumeTailorResult


def _make_cv(full_name: str = "Jane Doe") -> CV:
    return CV(
        full_name=full_name,
        contact_info="jane@example.com",
        summary="Platform engineer.",
        skills=["Python", "SQL"],
        experience=[
            WorkExperience(
                company="Acme",
                role="Engineer",
                dates="2022-2026",
                highlights=["Built services"],
            )
        ],
        education=["BSc CS"],
    )


def _make_result() -> ResumeTailorResult:
    return ResumeTailorResult(
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_resume=_make_cv().model_dump_json(),
        audit_report={"passed": True},
        passed=True,
    )


class TestResolvePattern:
    def test_all_variables_replaced(self):
        result = _make_result()
        cv = _make_cv()
        template = "{company_name}-{job_title}-{full_name}-{timestamp}"
        actual = _resolve_pattern(template, result, cv)
        today = date.today().strftime("%Y%m%d")
        expected = f"acme_corp-software_engineer-jane_doe-{today}"
        assert actual == expected

    def test_unknown_variables_left_unchanged(self):
        result = _make_result()
        cv = _make_cv()
        template = "{company_name}-{unknown}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "acme_corp-{unknown}"

    def test_empty_value_produces_empty_segment(self):
        result = _make_result()
        result.company_name = ""
        cv = _make_cv()
        template = "{company_name}-{job_title}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "-software_engineer"

    def test_special_chars_are_slugified(self):
        result = _make_result()
        result.company_name = "Google Inc. (Remote)"
        result.job_title = "Senior/Staff Engineer"
        cv = _make_cv(full_name="John O'Connor")
        template = "{company_name}-{job_title}-{full_name}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "google_inc_remote-senior_staff_engineer-john_oconnor"

    def test_custom_pattern_without_defaults(self):
        result = _make_result()
        cv = _make_cv()
        template = "{full_name}_for_{company_name}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "jane_doe_for_acme_corp"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_main.py::TestResolvePattern -v
```

Expected: FAIL with "ImportError: cannot import name '_resolve_pattern'"

- [ ] **Step 3: Write minimal implementation**

Add to `resume_tailorator/main.py` after `_get_job_fingerprint` (around line 43):

```python
import re
from datetime import date


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    # Lowercase, replace spaces with underscores, remove non-alphanumeric chars except underscores
    text = text.lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def _resolve_pattern(template: str, result: ResumeTailorResult, cv: CV) -> str:
    """Replace template variables with slugified values from result and CV."""
    timestamp = date.today().strftime("%Y%m%d")
    replacements = {
        "{company_name}": _slugify(result.company_name),
        "{job_title}": _slugify(result.job_title),
        "{full_name}": _slugify(cv.full_name),
        "{timestamp}": timestamp,
    }
    resolved = template
    for variable, value in replacements.items():
        resolved = resolved.replace(variable, value)
    return resolved
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_main.py::TestResolvePattern -v
```

Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add resume_tailorator/main.py tests/test_main.py
git commit -m "feat: add _resolve_pattern() for template-based output naming

- _slugify() converts text to filesystem-safe slugs
- _resolve_pattern() replaces {company_name}, {job_title},
  {full_name}, {timestamp} in user templates
- Unit tests cover all variables, unknown vars, empty values,
  special chars, and custom patterns

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Update `generate_resume()` in `markdown_writer.py`

**Files:**
- Modify: `resume_tailorator/utils/markdown_writer.py:9-105`
- Test: `tests/test_cli_typer.py` (integration)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli_typer.py` in the `_make_result` / test helpers area (verify `generate_resume` is called with correct args):

Actually, the existing tests already mock `generate_resume`. We'll verify the call signature change in Task 6. For now, skip the standalone test and rely on integration tests.

Instead, verify the existing test suite still passes after the signature change:

```bash
pytest tests/test_cli_typer.py::test_tailor_command_success -v
```

- [ ] **Step 2: Update `generate_resume()` signature and implementation**

In `resume_tailorator/utils/markdown_writer.py`, replace lines 9-26:

```python
def generate_resume(
    result: ResumeTailorResult, output_dir: str, base_filename: str
) -> str:
    """
    Convert tailored CV to Markdown, PDF, and DOCX formats.

    Args:
        result: ResumeTailorResult object containing tailored resume and company name
        output_dir: Directory to save output files (job-specific subdirectory).
        base_filename: Base name for all output files (without extension).

    Returns:
        The path to the generated Markdown file.
    """
    os.makedirs(output_dir, exist_ok=True)
    md_output_path = os.path.join(output_dir, f"{base_filename}.md")
    pdf_output_path = os.path.join(output_dir, f"{base_filename}.pdf")
    docx_output_path = os.path.join(output_dir, f"{base_filename}.docx")
```

Remove the old lines 21-23 (company_slug computation):
```python
    # Use slugified filename to match CLI path expectations.
    company_slug = result.company_name.replace(" ", "_").lower()
    base_filename = f"tailored_resume_{company_slug}"
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

```bash
pytest tests/test_cli_typer.py -v
```

Expected: All tests still pass (they mock `generate_resume`, so signature change doesn't break them).

- [ ] **Step 4: Commit**

```bash
git add resume_tailorator/utils/markdown_writer.py
git commit -m "refactor: generate_resume() accepts base_filename param

- Replaced internal company_slug computation with caller-provided
  base_filename parameter
- Output files now use: {base_filename}.md/pdf/docx
- Caller (_run_workflow) now controls naming entirely

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Update `_run_workflow()` in `main.py`

**Files:**
- Modify: `resume_tailorator/main.py:122-170`
- Test: `tests/test_cli_typer.py`

- [ ] **Step 1: Update `_run_workflow()` signature**

Change line 122-128 from:

```python
async def _run_workflow(
    resume_content: str,
    job_posting_markdown: str,
    output_dir: str,
    model: str | None,
    recommendations: str = "",
) -> tuple[int, str | None, str | None, ResumeTailorResult]:
```

To:

```python
async def _run_workflow(
    resume_content: str,
    job_posting_markdown: str,
    output_dir: str,
    model: str | None,
    recommendations: str = "",
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
) -> tuple[int, str | None, str | None, ResumeTailorResult]:
```

- [ ] **Step 2: Update the resume generation block (lines 146-148)**

Change:
```python
    if result.passed:
        console.print("\n✅ Audit Passed. Saving CV...")
        resume_path = generate_resume(result, output_dir=output_dir)
```

To:
```python
    if result.passed:
        console.print("\n✅ Audit Passed. Saving CV...")

        # Parse CV to get full_name for pattern resolution
        cv = CV.model_validate_json(result.tailored_resume)

        # Resolve directory and file name patterns
        job_dir_name = _resolve_pattern(output_pattern, result, cv)
        job_dir = os.path.join(output_dir, job_dir_name)
        os.makedirs(job_dir, exist_ok=True)

        resume_base_name = _resolve_pattern(resume_name_pattern, result, cv)
        resume_path = generate_resume(result, job_dir, resume_base_name)
```

- [ ] **Step 3: Update the report generation block (lines 154-166)**

Change:
```python
    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        company_slug = _get_company_slug(result.company_name)
        report_path = os.path.join(output_dir, f"report_{company_slug}.md")

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            console.print(f"\n📄 Report saved to: {report_path}")
        except IOError as e:
            console.print(f"⚠️ Error writing report file: {e}")
```

To:
```python
    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)

        # Compute report path using same directory and resume base name
        if result.passed:
            # Use the same job_dir and resume_base_name computed above
            report_path = os.path.join(job_dir, f"{resume_base_name}_report.md")
        else:
            # When audit fails, we still need a report path.
            # Use the default patterns since generate_resume wasn't called.
            cv = CV.model_validate_json(result.tailored_resume)
            job_dir_name = _resolve_pattern(output_pattern, result, cv)
            job_dir = os.path.join(output_dir, job_dir_name)
            os.makedirs(job_dir, exist_ok=True)
            resume_base_name = _resolve_pattern(resume_name_pattern, result, cv)
            report_path = os.path.join(job_dir, f"{resume_base_name}_report.md")

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            console.print(f"\n📄 Report saved to: {report_path}")
        except IOError as e:
            console.print(f"⚠️ Error writing report file: {e}")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cli_typer.py -v
```

Expected: All tests pass (they mock `generate_resume` and don't assert on report paths).

- [ ] **Step 5: Commit**

```bash
git add resume_tailorator/main.py
git commit -m "feat: _run_workflow() uses job-specific directories and templates

- Added output_pattern and resume_name_pattern params to _run_workflow
- Computes job_dir from output_pattern + creates it with makedirs
- Computes resume_base_name from resume_name_pattern
- Calls generate_resume(result, job_dir, resume_base_name)
- Report saved as {resume_base_name}_report.md in same directory
- Handles both passed=True and passed=False cases

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Update `tailor` CLI command and `_tailor_impl()`

**Files:**
- Modify: `resume_tailorator/main.py:173-315` (`_tailor_impl` and `tailor`)
- Test: `tests/test_cli_typer.py`

- [ ] **Step 1: Update `_tailor_impl()` signature**

Change line 173-178 from:
```python
async def _tailor_impl(
    job_url: str,
    resume_path: str,
    output_dir: str,
    model: str | None,
) -> int:
```

To:
```python
async def _tailor_impl(
    job_url: str,
    resume_path: str,
    output_dir: str,
    model: str | None,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
) -> int:
```

- [ ] **Step 2: Pass patterns to `_run_workflow()`**

Change lines 257-262 from:
```python
    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
    )
```

To:
```python
    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        output_pattern=output_pattern,
        resume_name_pattern=resume_name_pattern,
    )
```

- [ ] **Step 3: Update `tailor()` CLI command**

Change lines 307-315 from:
```python
@app.command()
def tailor(
    job_url: str = typer.Argument(..., help="URL of job posting to scrape"),
    resume_path: str = typer.Argument(..., help="Path to resume (Markdown, DOCX, PDF)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use (e.g., openai:gpt-4o-mini)"),
) -> int:
    """Run the full resume tailoring workflow."""
    return asyncio.run(_tailor_impl(job_url, resume_path, output_dir, model))
```

To:
```python
@app.command()
def tailor(
    job_url: str = typer.Argument(..., help="URL of job posting to scrape"),
    resume_path: str = typer.Argument(..., help="Path to resume (Markdown, DOCX, PDF)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use (e.g., openai:gpt-4o-mini)"),
    output_pattern: str = typer.Option(
        "{company_name}-{job_title}",
        help="Template for the job-specific subdirectory name",
    ),
    resume_name_pattern: str = typer.Option(
        "{company_name}-{full_name}",
        help="Template for the resume file base name (without extension)",
    ),
) -> int:
    """Run the full resume tailoring workflow."""
    return asyncio.run(
        _tailor_impl(
            job_url,
            resume_path,
            output_dir,
            model,
            output_pattern=output_pattern,
            resume_name_pattern=resume_name_pattern,
        )
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cli_typer.py::test_tailor_command_success -v
pytest tests/test_cli_typer.py::test_tailor_command_docx_conversion -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_tailorator/main.py
git commit -m "feat: add --output-pattern and --resume-name-pattern to tailor command

- _tailor_impl() accepts output_pattern and resume_name_pattern
- tailor() CLI adds --output-pattern and --resume-name-pattern options
- Patterns passed through to _run_workflow()
- Defaults: {company_name}-{job_title} for directory,
  {company_name}-{full_name} for file base name

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Update `re_tailor` CLI command and `_re_tailor_impl()`

**Files:**
- Modify: `resume_tailorator/main.py:318-444` (`_re_tailor_impl` and `re_tailor`)
- Test: `tests/test_cli_typer.py`

- [ ] **Step 1: Update `_re_tailor_impl()` signature**

Change lines 318-324 from:
```python
async def _re_tailor_impl(
    job_id: str,
    recommendations: str,
    resume_path: str | None,
    output_dir: str,
    model: str | None,
) -> int:
```

To:
```python
async def _re_tailor_impl(
    job_id: str,
    recommendations: str,
    resume_path: str | None,
    output_dir: str,
    model: str | None,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
) -> int:
```

- [ ] **Step 2: Pass patterns to `_run_workflow()`**

Change lines 395-401 from:
```python
    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        recommendations=recommendations,
    )
```

To:
```python
    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        recommendations=recommendations,
        output_pattern=output_pattern,
        resume_name_pattern=resume_name_pattern,
    )
```

- [ ] **Step 3: Update `re_tailor()` CLI command**

Change lines 435-444 from:
```python
@app.command()
def re_tailor(
    job_id: str = typer.Argument(..., help="UUID of prior job"),
    recommendations: str = typer.Argument(..., help="Comments/recommendations from prior audit"),
    resume_path: str | None = typer.Option(None, help="Path to resume (uses stored path if omitted)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use"),
) -> int:
    """Re-run tailoring with recommendations from a prior audit."""
    return asyncio.run(_re_tailor_impl(job_id, recommendations, resume_path, output_dir, model))
```

To:
```python
@app.command()
def re_tailor(
    job_id: str = typer.Argument(..., help="UUID of prior job"),
    recommendations: str = typer.Argument(..., help="Comments/recommendations from prior audit"),
    resume_path: str | None = typer.Option(None, help="Path to resume (uses stored path if omitted)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use"),
    output_pattern: str = typer.Option(
        "{company_name}-{job_title}",
        help="Template for the job-specific subdirectory name",
    ),
    resume_name_pattern: str = typer.Option(
        "{company_name}-{full_name}",
        help="Template for the resume file base name (without extension)",
    ),
) -> int:
    """Re-run tailoring with recommendations from a prior audit."""
    return asyncio.run(
        _re_tailor_impl(
            job_id,
            recommendations,
            resume_path,
            output_dir,
            model,
            output_pattern=output_pattern,
            resume_name_pattern=resume_name_pattern,
        )
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cli_typer.py::test_re_tailor_success -v
pytest tests/test_cli_typer.py::test_re_tailor_with_resume_path -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add resume_tailorator/main.py
git commit -m "feat: add --output-pattern and --resume-name-pattern to re-tailor command

- _re_tailor_impl() accepts output_pattern and resume_name_pattern
- re_tailor() CLI adds --output-pattern and --resume-name-pattern options
- Patterns passed through to _run_workflow()
- Same defaults as tailor command

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Add CLI integration tests for new options

**Files:**
- Modify: `tests/test_cli_typer.py`
- Create: (no new files)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli_typer.py` after `test_tailor_command_docx_conversion` (around line 367):

```python
def test_tailor_command_custom_patterns(tmp_path, monkeypatch) -> None:
    """tailor command with custom patterns should create correctly named files."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    workflow_result = _make_result(cv=cv, passed=True)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)

    # Mock generate_resume to capture the arguments
    captured_args = {}

    def mock_generate_resume(result, output_dir, base_filename):
        captured_args["output_dir"] = output_dir
        captured_args["base_filename"] = base_filename
        return os.path.join(output_dir, f"{base_filename}.md")

    scraped_job = _make_scraped_job()

    with (
        patch(
            "resume_tailorator.main.job_scraper_agent.run",
            AsyncMock(return_value=MagicMock(output=scraped_job)),
        ),
        patch("resume_tailorator.main.ResumeTailorWorkflow", return_value=mock_workflow),
        patch("resume_tailorator.main.generate_resume", mock_generate_resume),
        patch("resume_tailorator.main.SQLiteResumeMemoryRepository") as mock_repo_cls,
        patch("resume_tailorator.main.PydanticAIResumeParser") as mock_parser_cls,
        patch("resume_tailorator.main.ResumeMemoryService") as mock_svc_cls,
    ):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_parser = MagicMock()
        mock_parser_cls.return_value = mock_parser
        mock_svc = MagicMock()
        mock_svc.resolve_original_resume.return_value = MagicMock(
            source=MagicMock(id="src-123"),
            cv=cv,
        )
        mock_svc.save_tailored_resume.return_value = MagicMock(id="job-456")
        mock_svc_cls.return_value = mock_svc

        result = runner.invoke(
            app,
            [
                "tailor",
                "https://example.com/job/123",
                str(resume_file),
                "--output-dir",
                str(output_dir),
                "--output-pattern",
                "{company_name}-{timestamp}",
                "--resume-name-pattern",
                "{full_name}-{job_title}",
            ],
        )

    assert result.exit_code == 0, result.output
    mock_workflow.run.assert_called_once()

    # Verify generate_resume was called with correct directory and filename
    today = date.today().strftime("%Y%m%d")
    expected_dir = str(output_dir / f"acme_corp-{today}")
    expected_base = "jane_doe-software_engineer"
    assert captured_args["output_dir"] == expected_dir
    assert captured_args["base_filename"] == expected_base
```

Note: Add `from datetime import date` to the imports at the top of `tests/test_cli_typer.py` if not already present.

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli_typer.py::test_tailor_command_custom_patterns -v
```

Expected: FAIL with ImportError for `_resolve_pattern` or assertion error if patterns not wired yet. (If Tasks 1-5 are done, this should pass.)

- [ ] **Step 3: Verify it passes (code already implemented in Tasks 1-5)**

```bash
pytest tests/test_cli_typer.py::test_tailor_command_custom_patterns -v
```

Expected: PASS

- [ ] **Step 4: Add re-tailor pattern test**

Add after the previous test:

```python
def test_re_tailor_custom_patterns(tmp_path, monkeypatch) -> None:
    """re_tailor with custom patterns should create correctly named files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    workflow_result = _make_result(cv=cv, passed=True)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)

    captured_args = {}

    def mock_generate_resume(result, output_dir, base_filename):
        captured_args["output_dir"] = output_dir
        captured_args["base_filename"] = base_filename
        return os.path.join(output_dir, f"{base_filename}.md")

    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Smith\n\nPython developer", encoding="utf-8")

    with (
        patch("resume_tailorator.main.ResumeTailorWorkflow", return_value=mock_workflow),
        patch("resume_tailorator.main.generate_resume", mock_generate_resume),
        patch("resume_tailorator.main.SQLiteResumeMemoryRepository") as mock_repo_cls,
        patch("resume_tailorator.main.PydanticAIResumeParser") as mock_parser_cls,
        patch("resume_tailorator.main.ResumeMemoryService") as mock_svc_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.get_tailored_resume_by_id.return_value = MagicMock(
            source_id="src-123",
            company_name="Acme Corp",
            job_title="Software Engineer",
            job_fingerprint="fp123",
            job_posting_markdown="# Job Posting\nPython engineer",
        )
        mock_repo.get_source_by_id.return_value = MagicMock(path=str(resume_file))
        mock_repo_cls.return_value = mock_repo

        mock_parser = MagicMock()
        mock_parser_cls.return_value = mock_parser

        mock_svc = MagicMock()
        mock_svc.resolve_original_resume.return_value = MagicMock(
            source=MagicMock(id="src-123", path=str(resume_file)),
            cv=cv,
        )
        mock_svc_cls.return_value = mock_svc

        result = runner.invoke(
            app,
            [
                "re-tailor",
                "job-456",
                "Add more detail about leadership skills",
                "--output-dir",
                str(output_dir),
                "--output-pattern",
                "{timestamp}-{company_name}",
                "--resume-name-pattern",
                "{job_title}-{full_name}",
            ],
        )

    assert result.exit_code == 0, result.output
    mock_workflow.run.assert_called_once()

    today = date.today().strftime("%Y%m%d")
    expected_dir = str(output_dir / f"{today}-acme_corp")
    expected_base = "software_engineer-jane_doe"
    assert captured_args["output_dir"] == expected_dir
    assert captured_args["base_filename"] == expected_base
```

- [ ] **Step 5: Run both pattern tests**

```bash
pytest tests/test_cli_typer.py::test_tailor_command_custom_patterns tests/test_cli_typer.py::test_re_tailor_custom_patterns -v
```

Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_cli_typer.py
git commit -m "test: add CLI integration tests for custom naming patterns

- test_tailor_command_custom_patterns: verifies --output-pattern
  and --resume-name-pattern are passed through to generate_resume
- test_re_tailor_custom_patterns: verifies same for re-tailor
- Both assert on exact directory name and base filename

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Run full test suite and verify

**Files:** None to modify.

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```

- [ ] **Step 2: Fix any failures**

Common issues to watch for:
- `test_main.py` tests may fail because they test a non-existent `main()` function. These tests are testing an old CLI interface. Skip them with `@pytest.mark.skip(reason="Tests old CLI interface")` or fix them to test `_run_workflow` directly.
- Any tests that assert on hardcoded file paths like `"tailored_resume_acme_corp.md"` will need updating.

- [ ] **Step 3: Run smoke test**

```bash
python -m resume_tailorator tailor --help
```

Expected output should include:
```
  --output-pattern        TEXT  Template for the job-specific subdirectory
                                name  [default: {company_name}-{job_title}]
  --resume-name-pattern   TEXT  Template for the resume file base name
                                (without extension)
                                [default: {company_name}-{full_name}]
```

```bash
python -m resume_tailorator re-tailor --help
```

Expected: Same options visible.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "test: fix test suite for job-specific output naming

- Full test suite passes with new pattern-based directory/filename logic

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

### 1. Spec Coverage

| Spec Requirement | Implementing Task |
|------------------|-------------------|
| `_resolve_pattern()` helper | Task 1 |
| Template variables: `{company_name}`, `{job_title}`, `{full_name}`, `{timestamp}` | Task 1 |
| Slugification (lowercase, spaces → `_`, unsafe chars stripped) | Task 1 |
| Unknown variables left untouched | Task 1 |
| Empty values handled | Task 1 |
| `generate_resume()` accepts `base_filename` | Task 2 |
| `--output-pattern` CLI option on `tailor` | Task 4 |
| `--resume-name-pattern` CLI option on `tailor` | Task 4 |
| `--output-pattern` CLI option on `re_tailor` | Task 5 |
| `--resume-name-pattern` CLI option on `re_tailor` | Task 5 |
| `_run_workflow()` creates job-specific directory | Task 3 |
| `_run_workflow()` uses patterns for resume and report | Task 3 |
| Report named `{base_name}_report.md` in same dir | Task 3 |
| Default: `{company_name}-{job_title}` for directory | Tasks 4, 5 |
| Default: `{company_name}-{full_name}` for file base | Tasks 4, 5 |
| Unit tests for `_resolve_pattern()` | Task 1 |
| Integration tests for CLI options | Task 6 |

### 2. Placeholder Scan

- No "TBD", "TODO", "implement later" in any step.
- All code blocks contain complete, runnable code.
- All test commands have expected output.
- All commit messages are complete.

### 3. Type Consistency

- `_resolve_pattern(template: str, result: ResumeTailorResult, cv: CV) -> str` used consistently.
- `generate_resume(result, output_dir, base_filename)` signature matches across all call sites.
- `_run_workflow()` parameter names match across `_tailor_impl` and `_re_tailor_impl`.

### 4. Known Issues / Notes

- `tests/test_main.py` tests a non-existent `main()` function (old CLI interface). These tests are stale and may need to be skipped or rewritten in a separate task. The new functionality is covered by `tests/test_cli_typer.py`.
- `tests/test_job_scraper_integration.py` may reference old file paths. Run the full suite in Task 7 to catch these.
- The `converted_resume_path` in `_tailor_impl` is still saved to the top-level `output_dir` (not the job-specific subdirectory). This is intentional — the converted resume is a temporary artifact, not the final output.
