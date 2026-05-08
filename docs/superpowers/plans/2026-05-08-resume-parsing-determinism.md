# Resume Parsing Determinism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make resume parsing deterministic by using the existing `ResumeMemoryService` cache (which already hashes content and caches parsed CVs) *before* the workflow runs, instead of after.

**Architecture:** The `ResumeMemoryService.aresolve_original_resume()` already hashes resume markdown and caches parsed CVs. Currently it's called *after* the workflow — we move it *before* and pass the cached CV to `workflow.run(pre_parsed_cv=...)` to skip AI parsing. Add `--debug` flag for conversion visibility and improve the parser agent prompt.

**Tech Stack:** Python, Typer, Pydantic AI, sqlite3

---

## File Structure

| File | Responsibility |
|------|---------------|
| `resume_tailorator/main.py` | CLI: add `--debug` flag; `_tailor_impl`: move cache lookup before workflow, thread params; `_re_tailor_impl`: same |
| `resume_tailorator/workflows/__init__.py` | `ResumeTailorWorkflow.run()`: add `pre_parsed_cv: CV \| None` and `debug: bool` params; skip Step 0 when `pre_parsed_cv` provided |
| `resume_tailorator/workflows/agents.py` | `resume_parser_agent`: richer system prompt |
| `tests/test_parsing_determinism.py` | New tests for cache hit/miss and debug flag |

Existing memory service and repository code (`service.py`, `repository.py`, `sqlite_repository.py`, `models.py`) needs **no changes** — they already implement the cache correctly.

---

### Task 1: Add `pre_parsed_cv` and `debug` params to workflow

**Files:**
- Modify: `resume_tailorator/workflows/__init__.py:83-89`

- [ ] **Step 1: Update the `run()` signature and Step 0 to skip when cached**

Edit `resume_tailorator/workflows/__init__.py`, change the `run` method signature and add cache-skip logic at Step 0:

```python
async def run(
    self,
    resume_text: str,
    job_content_file_path: str | None = None,
    job_content: str | None = None,
    model: str | None = None,
    pre_parsed_cv: CV | None = None,
    debug: bool = False,
) -> ResumeTailorResult:
```

Now replace Step 0 (lines 115-168, the entire "STEP 0: PARSE ORIGINAL RESUME" block) with a conditional block that skips parsing when `pre_parsed_cv` is provided:

```python
        total_usage = RunUsage()

        # --- STEP 0: PARSE ORIGINAL RESUME ---
        self._set_stage("PARSING_RESUME")
        original_cv_result: AgentRunResult[CV] | None = None
        original_cv: CV | None = None

        if pre_parsed_cv is not None:
            print("♻️  Using cached parsed resume (skipping AI parsing)")
            original_cv = pre_parsed_cv
            if debug:
                print(f"   [Debug] Pre-parsed CV has {len(original_cv.skills)} skills, "
                      f"{len(original_cv.experience)} work experiences")
        else:
            print("🤖 Agent 0 (Parser): Parsing original resume...")
            for attempt in range(self.MAX_RETRIES):
                try:
                    original_cv_result = await resume_parser_agent.run(
                        f"Parse this resume into structured format:\n\n{resume_text}",
                        usage=total_usage,
                        usage_limits=USAGE_LIMITS,
                    )

                    if original_cv_result.output is None:
                        raise ValueError("Resume parsing returned None")

                    if (
                        original_cv_result.output.full_name
                        and original_cv_result.output.experience
                    ):
                        break

                    print(
                        f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete resume parse, retrying..."
                    )

                except UnexpectedModelBehavior:
                    if _parser_qs.last_output is not None:
                        print(
                            "⚠️  Resume Parser quality gate exhausted — using best available output"
                        )
                        original_cv = _parser_qs.last_output
                        break
                    self._complete_stage("PARSING_RESUME", success=False)
                    sys.exit(
                        "❌ Resume Parser quality gate exhausted with no fallback available."
                    )
                except Exception as e:
                    print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                    if attempt == self.MAX_RETRIES - 1:
                        self._complete_stage("PARSING_RESUME", success=False)
                        sys.exit("❌ Failed to parse original resume after retries.")

            if original_cv is None:
                if original_cv_result is None or original_cv_result.output is None:
                    self._complete_stage("PARSING_RESUME", success=False)
                    sys.exit("❌ Failed to parse original resume after retries.")
                original_cv = original_cv_result.output

        self._complete_stage("PARSING_RESUME")
        print(f"   ✅ Resume Parsed: {original_cv.full_name}")
        print(
            f"   📋 Found {len(original_cv.skills)} skills, {len(original_cv.experience)} work experiences\n"
        )
```

- [ ] **Step 2: Verify syntax**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -c "from resume_tailorator.workflows import ResumeTailorWorkflow; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add resume_tailorator/workflows/__init__.py
git commit -m "feat: add pre_parsed_cv and debug params to workflow run()"
```

---

### Task 2: Add `--debug` flag to CLI and wire cache in `_tailor_impl`

**Files:**
- Modify: `resume_tailorator/main.py:253-388`, `resume_tailorator/main.py:392-416`

- [ ] **Step 1: Update `_tailor_impl` signature and move cache before workflow**

After `resume_content` is loaded and validated (after line 305), add hash computation and cache lookup:

```python
    # Compute content hash and check cache before running the workflow
    content_hash = hashlib.sha256(resume_content.encode()).hexdigest()
    pre_parsed_cv: CV | None = None
    try:
        repo = SQLiteResumeMemoryRepository()
        parser = PydanticAIResumeParser()
        service = ResumeMemoryService(repository=repo, parser=parser)
        resolved = await service.aresolve_original_resume(
            path=(converted_resume_path or resume_path_expanded)
        )
        pre_parsed_cv = resolved.cv
        if debug:
            console.print(f"🔍 [Debug] Content hash: {content_hash}")
            console.print(f"🔍 [Debug] Cache hit: using pre-parsed CV with "
                          f"{len(pre_parsed_cv.skills)} skills")
    except Exception:
        if debug:
            console.print("[yellow]🔍 [Debug] Cache miss or error — will parse with AI[/yellow]")
        pre_parsed_cv = None
```

Update the `_tailor_impl` signature to include `debug`:

```python
async def _tailor_impl(
    job_url: str,
    resume_path: str,
    output_dir: str,
    model: str | None,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
    debug: bool = False,  # NEW
) -> int:
```

- [ ] **Step 2: Thread `debug` and `pre_parsed_cv` into `_run_workflow` call**

Update `_run_workflow` signature:

```python
async def _run_workflow(
    resume_content: str,
    job_posting_markdown: str,
    output_dir: str,
    model: str | None,
    recommendations: str = "",
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
    pre_parsed_cv: CV | None = None,   # NEW
    debug: bool = False,               # NEW
) -> tuple[int, str | None, str | None, ResumeTailorResult]:
```

In `_run_workflow`, pass to `workflow.run()`:

```python
    result = await workflow.run(
        resume_content,
        job_content=job_content,
        model=model,
        pre_parsed_cv=pre_parsed_cv,
        debug=debug,
    )
```

And add debug dump logic in `_run_workflow` after the job dir is created:

```python
    if debug:
        debug_path = os.path.join(job_dir, "resume_debug.md")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(resume_content)
        console.print(f"🔍 [Debug] Converted resume saved to: {debug_path}")
        console.print(f"🔍 [Debug] First 500 chars of resume sent to parser:\n"
                      f"{resume_content[:500]}")
```

- [ ] **Step 3: Update `_tailor_impl` to pass `debug` to `_run_workflow`**

Update the call site (line 339):

```python
    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        output_pattern=output_pattern,
        resume_name_pattern=resume_name_pattern,
        pre_parsed_cv=pre_parsed_cv,
        debug=debug,
    )
```

- [ ] **Step 4: Update `_tailor_impl` to skip the post-workflow save for already-cached sources**

Remove the duplicate `aresolve_original_resume` call in the post-workflow block (lines 348-386) for cached sources:

The existing post-workflow block (lines 348-386) calls `aresolve_original_resume` again which is now redundant when cached. Keep the existing behavior but guard it:

```python
    if exit_code == 0:
        try:
            # Only create a new repo connection if we didn't already in the cache block
            repo = SQLiteResumeMemoryRepository()
            parser = PydanticAIResumeParser()
            service = ResumeMemoryService(repository=repo, parser=parser)
            source_path = converted_resume_path or resume_path_expanded
            resolved = await service.aresolve_original_resume(path=source_path)
            job_fingerprint = _get_job_fingerprint(job_url, result.job_title)
            audit = _audit_result_from_dict(result.audit_report)
            if result.tailored_resume:
                tailored_cv = CV.model_validate_json(result.tailored_resume)
            else:
                tailored_cv = resolved.cv
            record = service.save_tailored_resume(
                source_id=resolved.source.id,
                job_fingerprint=job_fingerprint,
                company_name=result.company_name,
                job_title=result.job_title,
                tailored_cv=tailored_cv,
                audit_result=audit,
                job_posting_markdown=job_posting_markdown,
            )
            console.print(f"\n💾 Job ID: {record.id}")
            console.print("\n✅ Job completed")
            console.print(f"📄 Tailored CV: {resume_path_out}")
            console.print(f"📊 Report: {report_path_out}")
        except Exception as e:
            logger.warning("Failed to persist tailored resume", exc_info=True)
            console.print(f"[yellow]⚠️ Failed to save job to memory: {e}[/yellow]")
            if resume_path_out and report_path_out:
                console.print("\n✅ Job completed")
                console.print(f"📄 Tailored CV: {resume_path_out}")
                console.print(f"📊 Report: {report_path_out}")
```

- [ ] **Step 5: Add `--debug` flag to `tailor` CLI command**

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
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output and save converted resume"),  # NEW
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
            debug=debug,
        )
    )
```

- [ ] **Step 6: Verify syntax**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -c "from resume_tailorator.main import app; print('OK')"
```

- [ ] **Step 7: Commit**

```bash
git add resume_tailorator/main.py
git commit -m "feat: add --debug flag and wire parsed CV cache before workflow"
```

---

### Task 3: Wire cache in `_re_tailor_impl`

**Files:**
- Modify: `resume_tailorator/main.py:419-537`, `resume_tailorator/main.py:540-567`

- [ ] **Step 1: Add `debug` param and cache lookup in `_re_tailor_impl`**

Update `_re_tailor_impl` signature:

```python
async def _re_tailor_impl(
    job_id: str,
    recommendations: str,
    resume_path: str | None,
    output_dir: str,
    model: str | None,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
    debug: bool = False,  # NEW
) -> int:
```

After `resume_content` is read (after the if/else block ending around line 489), add cache lookup:

```python
    # Compute hash and try cache before running workflow
    if debug:
        content_hash = hashlib.sha256(resume_content.encode()).hexdigest()
        console.print(f"🔍 [Debug] Content hash: {content_hash}")
        if resolved:
            console.print(f"🔍 [Debug] Using pre-parsed CV with {len(resolved.cv.skills)} skills")

    pre_parsed_cv = resolved.cv if resolved else None
```

The `resolved` variable already exists from the earlier `aresolve_original_resume` call (around line 451 or 457). No need to call it again.

- [ ] **Step 2: Thread `debug` and `pre_parsed_cv` into `_run_workflow`**

Update the call (line 498):

```python
    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        recommendations=recommendations,
        output_pattern=output_pattern,
        resume_name_pattern=resume_name_pattern,
        pre_parsed_cv=pre_parsed_cv,
        debug=debug,
    )
```

- [ ] **Step 3: Add `--debug` flag to `re_tailor` CLI command**

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
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug output and save converted resume"),  # NEW
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
            debug=debug,
        )
    )
```

- [ ] **Step 4: Verify syntax**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -c "from resume_tailorator.main import app; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add resume_tailorator/main.py
git commit -m "feat: wire cache and --debug flag into re_tailor command"
```

---

### Task 4: Improve parser agent system prompt

**Files:**
- Modify: `resume_tailorator/workflows/agents.py:111-129`

- [ ] **Step 1: Replace the `resume_parser_agent` system prompt**

```python
resume_parser_agent = Agent(
    MODEL_NAME,
    model_settings=MODEL_SETTINGS,
    system_prompt="""
    You are an expert Resume Parser.
    Your job is to parse a resume in Markdown format and extract ALL information into a structured format.

    RULES:
    1. Extract ALL information accurately from the markdown resume — leave nothing behind
    2. Extract skills from EVERY section: summary, experience bullets, projects, certifications,
       education, and publications — not just a dedicated "Skills" section
    3. Every technical term, framework, language, tool, methodology, platform, protocol,
       database, and soft skill mentioned anywhere in the resume is a skill — capture it
    4. For a senior professional resume, expect to extract 40+ individual skills
    5. Do NOT add or modify any information — preserve the exact wording
    6. Structure work experience with company, role, dates, and highlight bullets
    7. Include all projects with their descriptions
    8. Preserve all education entries, certifications, and publications
    """,
    output_type=CV,
    retries=5,
)
```

- [ ] **Step 2: Verify syntax**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -c "from resume_tailorator.workflows.agents import resume_parser_agent; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add resume_tailorator/workflows/agents.py
git commit -m "feat: improve resume parser agent system prompt for thoroughness"
```

---

### Task 5: Add tests

**Files:**
- Create: `tests/test_parsing_determinism.py`

- [ ] **Step 1: Create test file**

```python
"""Tests for deterministic resume parsing via pre-parsed CV cache."""
import inspect
import pytest

from resume_tailorator.models.agents.output import CV, WorkExperience
from resume_tailorator.workflows import ResumeTailorWorkflow


@pytest.fixture
def sample_pre_parsed_cv():
    return CV(
        full_name="Jane Doe",
        contact_info="jane@example.com",
        summary="Senior engineer with 10 years experience",
        skills=["Python", "TypeScript", "React", "AWS", "Docker", "Kubernetes"],
        projects=["Built CI/CD pipeline"],
        experience=[
            WorkExperience(
                company="Acme Corp",
                role="Staff Engineer",
                dates="2020-2024",
                highlights=["Led team of 5", "Designed distributed system"],
            )
        ],
        education=["BSc Computer Science"],
        certifications=["AWS Solutions Architect"],
        publications=[],
    )


def test_workflow_run_signature_accepts_pre_parsed_cv():
    """run() has pre_parsed_cv and debug parameters with correct defaults."""
    sig = inspect.signature(ResumeTailorWorkflow.run)
    assert "pre_parsed_cv" in sig.parameters
    assert sig.parameters["pre_parsed_cv"].default is None
    assert "debug" in sig.parameters
    assert sig.parameters["debug"].default is False


def test_pre_parsed_cv_preserves_skills(sample_pre_parsed_cv):
    """A pre-parsed CV should faithfully carry its data."""
    assert len(sample_pre_parsed_cv.skills) == 6
    assert sample_pre_parsed_cv.full_name == "Jane Doe"
    assert len(sample_pre_parsed_cv.experience) == 1


@pytest.mark.asyncio
async def test_tailor_impl_accepts_debug_param():
    """_tailor_impl signature includes debug param."""
    from resume_tailorator.main import _tailor_impl
    sig = inspect.signature(_tailor_impl)
    assert "debug" in sig.parameters
    assert sig.parameters["debug"].default is False


@pytest.mark.asyncio
async def test_re_tailor_impl_accepts_debug_param():
    """_re_tailor_impl signature includes debug param."""
    from resume_tailorator.main import _re_tailor_impl
    sig = inspect.signature(_re_tailor_impl)
    assert "debug" in sig.parameters
    assert sig.parameters["debug"].default is False


@pytest.mark.asyncio
async def test_run_workflow_signature_includes_new_params():
    """_run_workflow passes pre_parsed_cv and debug through."""
    from resume_tailorator.main import _run_workflow
    sig = inspect.signature(_run_workflow)
    assert "pre_parsed_cv" in sig.parameters
    assert "debug" in sig.parameters
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -m pytest tests/test_parsing_determinism.py -v
```

Expected: tests pass

- [ ] **Step 3: Run existing tests to check for regressions**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -m pytest tests/ -v --timeout=30
```

Expected: all pre-existing tests should still pass (the new params have defaults)

- [ ] **Step 4: Commit**

```bash
git add tests/test_parsing_determinism.py
git commit -m "test: add tests for pre-parsed CV cache behavior"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -m pytest tests/ -v --timeout=60
```

- [ ] **Step 2: Review git log**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && git log --oneline
```

Expected: clean history of focused commits
