"""Tests for Task 6 CLI integration: main.py wired to memory service.

Coverage:
- Explicit --resume-path argument → service resolves from that path, workflow
  runs against the resolved CV, tailored resume is persisted.
- No --resume-path argument → service.resolve_original_resume called with
  path=None (latest-stored fallback handled inside service).
- First run with no stored resume → MissingOriginalResumeError → user-facing
  message printed and sys.exit(1) raised (no raw traceback).
- FileNotFoundError from service → user-facing message and sys.exit(1).
- Workflow result.passed=False → tailored resume NOT saved.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import main as main_module
from memory.models import (
    MissingOriginalResumeError,
    ResolvedOriginalResume,
    ResumeMemoryError,
    ResumeSourceRecord,
)
from models.agents.output import CV, WorkExperience
from models.workflow import ResumeTailorResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_source_record(path: str = "/fake/resume.md") -> ResumeSourceRecord:
    now = datetime.now(timezone.utc)
    return ResumeSourceRecord(
        id="source-abc-123",
        path=path,
        content_hash="deadbeef",
        is_active=True,
        created_at=now,
        updated_at=now,
        last_seen_at=now,
    )


def _make_resolved(
    cv: CV | None = None, path: str = "/fake/resume.md"
) -> ResolvedOriginalResume:
    cv = cv or _make_cv()
    return ResolvedOriginalResume(source=_make_source_record(path=path), cv=cv)


def _make_result(cv: CV | None = None, passed: bool = True) -> ResumeTailorResult:
    cv = cv or _make_cv()
    return ResumeTailorResult(
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_resume=cv.model_dump_json(),
        audit_report={
            "passed": passed,
            "hallucination_score": 0,
            "ai_cliche_score": 1,
            "issues": [],
            "feedback_summary": "Looks good.",
        },
        passed=passed,
    )


def _patch_all(
    *,
    resolved: ResolvedOriginalResume,
    workflow_result: ResumeTailorResult,
    resolve_side_effect=None,
    save_side_effect=None,
):
    """Return a context manager stack that patches all external collaborators.

    Returns a dict of named mocks so tests can assert on them.
    """
    mock_repo = MagicMock()
    mock_parser = MagicMock()
    mock_service = MagicMock()
    if resolve_side_effect is not None:
        mock_service.resolve_original_resume.side_effect = resolve_side_effect
    else:
        mock_service.resolve_original_resume.return_value = resolved
    if save_side_effect is not None:
        mock_service.save_tailored_resume.side_effect = save_side_effect
    else:
        mock_service.save_tailored_resume.return_value = MagicMock()

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)
    mock_generate_resume = MagicMock()

    patches = [
        patch("main.SQLiteResumeMemoryRepository", return_value=mock_repo),
        patch("main.PydanticAIResumeParser", return_value=mock_parser),
        patch("main.ResumeMemoryService", return_value=mock_service),
        patch("main.ResumeTailorWorkflow", return_value=mock_workflow),
        patch("main.generate_resume", mock_generate_resume),
    ]
    return patches, {
        "repo": mock_repo,
        "parser": mock_parser,
        "service": mock_service,
        "workflow": mock_workflow,
        "generate_resume": mock_generate_resume,
    }


# ---------------------------------------------------------------------------
# Test 1: explicit --resume-path
# ---------------------------------------------------------------------------


async def test_main_explicit_resume_path_wires_service_and_workflow(
    tmp_path, monkeypatch, subtests
) -> None:
    """main() with --resume-path should:
    - call resolve_original_resume(path=<given path>)
    - call workflow.run with the resolved CV
    - call save_tailored_resume when result.passed
    """
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer at Acme\nPython role.")

    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    resolved = _make_resolved(cv=cv, path=str(resume_file))
    workflow_result = _make_result(cv=cv, passed=True)

    patches, mocks = _patch_all(resolved=resolved, workflow_result=workflow_result)

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        await main_module.main(argv=["--resume-path", str(resume_file)])

    with subtests.test("resolve called with explicit path"):
        mocks["service"].resolve_original_resume.assert_called_once_with(
            path=str(resume_file)
        )

    with subtests.test("workflow.run called with resolved cv"):
        call_kwargs = mocks["workflow"].run.call_args
        assert call_kwargs is not None
        # first positional arg or keyword 'original_cv'
        called_cv = (
            call_kwargs.args[0]
            if call_kwargs.args
            else call_kwargs.kwargs.get("original_cv")
        )
        assert called_cv == cv

    with subtests.test("save_tailored_resume called once"):
        mocks["service"].save_tailored_resume.assert_called_once()

    with subtests.test("save_tailored_resume got correct source_id"):
        save_kwargs = mocks["service"].save_tailored_resume.call_args.kwargs
        assert save_kwargs["source_id"] == resolved.source.id

    with subtests.test("save_tailored_resume got company_name"):
        save_kwargs = mocks["service"].save_tailored_resume.call_args.kwargs
        assert save_kwargs["company_name"] == "Acme Corp"

    with subtests.test("save_tailored_resume got job_title"):
        save_kwargs = mocks["service"].save_tailored_resume.call_args.kwargs
        assert save_kwargs["job_title"] == "Software Engineer"

    with subtests.test("save_tailored_resume got a non-empty job_fingerprint"):
        save_kwargs = mocks["service"].save_tailored_resume.call_args.kwargs
        assert save_kwargs["job_fingerprint"]

    with subtests.test("repository closed after run"):
        mocks["repo"].close.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: no --resume-path → path=None passed to service
# ---------------------------------------------------------------------------


async def test_main_no_resume_path_passes_none_to_service(
    tmp_path, monkeypatch, subtests
) -> None:
    """main() without --resume-path should call resolve_original_resume(path=None)."""
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer at Acme\nPython role.")

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    resolved = _make_resolved(cv=cv)
    workflow_result = _make_result(cv=cv, passed=True)

    patches, mocks = _patch_all(resolved=resolved, workflow_result=workflow_result)

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        await main_module.main(argv=[])

    with subtests.test("resolve called with path=None"):
        mocks["service"].resolve_original_resume.assert_called_once_with(path=None)


# ---------------------------------------------------------------------------
# Test 3: first run — no stored resume and no path → user-facing message + exit
# ---------------------------------------------------------------------------


async def test_main_first_run_no_original_resume_exits_cleanly(
    tmp_path, monkeypatch, capsys
) -> None:
    """main() must print a user-friendly warning and exit 1 on MissingOriginalResumeError.

    It must NOT let the raw exception propagate as an unhandled traceback.
    """
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer\nPython.")

    monkeypatch.chdir(tmp_path)

    error = MissingOriginalResumeError(
        "No original resume found. Please provide a path with --resume-path."
    )

    patches, mocks = _patch_all(
        resolved=_make_resolved(),
        workflow_result=_make_result(),
        resolve_side_effect=error,
    )

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        with pytest.raises(SystemExit) as exc_info:
            await main_module.main(argv=[])

    assert exc_info.value.code == 1

    output = capsys.readouterr().out
    assert "resume" in output.lower() or "⚠️" in output, (
        f"Expected a user-facing warning in stdout, got: {output!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: FileNotFoundError from service → user-facing message + exit
# ---------------------------------------------------------------------------


async def test_main_file_not_found_exits_cleanly(tmp_path, monkeypatch, capsys) -> None:
    """main() must handle FileNotFoundError from the service gracefully."""
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer\nPython.")

    monkeypatch.chdir(tmp_path)

    patches, mocks = _patch_all(
        resolved=_make_resolved(),
        workflow_result=_make_result(),
        resolve_side_effect=FileNotFoundError("No such file: /no/such/file.md"),
    )

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        with pytest.raises(SystemExit) as exc_info:
            await main_module.main(argv=["--resume-path", "/no/such/file.md"])

    assert exc_info.value.code == 1
    output = capsys.readouterr().out
    assert "⚠️" in output or "not found" in output.lower()


async def test_main_resume_resolution_failure_exits_cleanly(
    tmp_path, monkeypatch, capsys
) -> None:
    """Domain errors during original resume resolution must be user-facing."""
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer\nPython.")

    monkeypatch.chdir(tmp_path)

    patches, mocks = _patch_all(
        resolved=_make_resolved(),
        workflow_result=_make_result(),
        resolve_side_effect=ResumeMemoryError("corrupted cached CV"),
    )

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        with pytest.raises(SystemExit) as exc_info:
            await main_module.main(argv=[])

    assert exc_info.value.code == 1
    output = capsys.readouterr().out
    assert "failed to resolve original resume" in output.lower()
    mocks["workflow"].run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: result.passed=False → save_tailored_resume NOT called
# ---------------------------------------------------------------------------


async def test_main_failed_audit_does_not_save_tailored_resume(
    tmp_path, monkeypatch
) -> None:
    """When the workflow result.passed is False, save_tailored_resume must not be called."""
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer\nPython.")

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    resolved = _make_resolved(cv=cv)
    workflow_result = _make_result(cv=cv, passed=False)

    patches, mocks = _patch_all(resolved=resolved, workflow_result=workflow_result)

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        await main_module.main(argv=[])

    mocks["service"].save_tailored_resume.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: save_tailored_resume failure → user-facing message + exit
# ---------------------------------------------------------------------------


async def test_main_save_tailored_resume_failure_exits_cleanly(
    tmp_path, monkeypatch, capsys
) -> None:
    """A persistence failure must stop the run with a user-facing message."""
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    (files_dir / "job_posting.md").write_text("# Engineer\nPython.")

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    resolved = _make_resolved(cv=cv)
    workflow_result = _make_result(cv=cv, passed=True)

    patches, mocks = _patch_all(
        resolved=resolved,
        workflow_result=workflow_result,
        save_side_effect=ResumeMemoryError("disk full"),
    )

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        with pytest.raises(SystemExit) as exc_info:
            await main_module.main(argv=[])

    assert exc_info.value.code == 1
    output = capsys.readouterr().out
    assert "failed to save tailored resume" in output.lower()
    mocks["generate_resume"].assert_not_called()
