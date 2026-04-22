"""Tests for memory.service and memory.parser.

TDD RED → GREEN cycle for Task 4.

Design overview:
- FakeRepository: in-memory stub of ResumeMemoryRepository.
- FakeParser: stub of ResumeParserAdapter that records call count.
- Tests cover:
    * resolve_original_resume with an explicit path (fresh + cache hit + cache miss)
    * resolve_original_resume with no path (falls back to latest stored source)
    * MissingOriginalResumeError when no source exists and no path given
    * save_tailored_resume serialises CV and AuditResult via Pydantic v2 model_dump_json
    * reparse when parser version changes (cache invalidation)
    * relative vs absolute path does not create duplicate source records
    * FileNotFoundError when the file does not exist on disk
    * abstract parser_version property enforced at instantiation time
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from memory.models import (
    MissingOriginalResumeError,
    ParsedOriginalResumeRecord,
    ResumeMemoryError,
    ResumeSourceRecord,
    TailoredResumeRecord,
)
from memory.parser import PydanticAIResumeParser, ResumeParserAdapter
from memory.repository import ResumeMemoryRepository
from memory.service import ResumeMemoryService
from models.agents.output import AuditResult, CV, WorkExperience


def _make_cv(full_name: str = "Jane Doe") -> CV:
    return CV(
        full_name=full_name,
        contact_info="jane@example.com",
        summary="Summary.",
        skills=["Python"],
        experience=[
            WorkExperience(
                company="Acme",
                role="Engineer",
                dates="2020-2024",
                highlights=["Did stuff"],
            )
        ],
        education=["BSc CS"],
    )


def _make_audit() -> AuditResult:
    return AuditResult(
        passed=True,
        hallucination_score=0,
        ai_cliche_score=1,
        issues=[],
        feedback_summary="Looks good.",
    )


# ---------------------------------------------------------------------------
# Fake repository
# ---------------------------------------------------------------------------


class FakeRepository(ResumeMemoryRepository):
    """Minimal in-memory stub for all repository operations."""

    def __init__(self) -> None:
        self._sources: dict[str, ResumeSourceRecord] = {}
        self._parsed: dict[str, ParsedOriginalResumeRecord] = {}  # keyed by source_id
        self._tailored: dict[str, TailoredResumeRecord] = {}  # keyed by job_fingerprint

    # -- source helpers --

    def get_active_original_source(self) -> ResumeSourceRecord | None:
        for s in self._sources.values():
            if s.is_active:
                return s
        return None

    def get_latest_original_source(self) -> ResumeSourceRecord | None:
        if not self._sources:
            return None
        return max(self._sources.values(), key=lambda s: s.last_seen_at)

    def get_source_by_path(self, path: str) -> ResumeSourceRecord | None:
        for s in self._sources.values():
            if s.path == path:
                return s
        return None

    def upsert_original_source(
        self,
        path: str,
        content_hash: str,
        is_active: bool,
    ) -> ResumeSourceRecord:
        existing = self.get_source_by_path(path)
        now = datetime.now(timezone.utc)
        if existing is not None:
            updated = existing.model_copy(
                update={
                    "content_hash": content_hash,
                    "is_active": is_active,
                    "updated_at": now,
                    "last_seen_at": now,
                }
            )
            self._sources[existing.id] = updated
            if is_active:
                self.set_active_original_source(existing.id)
            return updated

        new_id = str(uuid.uuid4())
        record = ResumeSourceRecord(
            id=new_id,
            path=path,
            content_hash=content_hash,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        self._sources[new_id] = record
        if is_active:
            self.set_active_original_source(new_id)
        return record

    def set_active_original_source(self, source_id: str) -> None:
        if source_id not in self._sources:
            raise ResumeMemoryError(f"Unknown source_id: {source_id}")
        for sid, s in self._sources.items():
            self._sources[sid] = s.model_copy(update={"is_active": sid == source_id})

    # -- parsed resume --

    def get_parsed_original_resume(
        self, source_id: str
    ) -> ParsedOriginalResumeRecord | None:
        return self._parsed.get(source_id)

    def save_parsed_original_resume(
        self,
        source_id: str,
        content_hash: str,
        parser_version: str,
        cv_json: str,
    ) -> ParsedOriginalResumeRecord:
        now = datetime.now(timezone.utc)
        existing = self._parsed.get(source_id)
        record = ParsedOriginalResumeRecord(
            source_id=source_id,
            content_hash=content_hash,
            parser_version=parser_version,
            cv_json=cv_json,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._parsed[source_id] = record
        return record

    # -- tailored resume --

    def save_tailored_resume(
        self,
        source_id: str,
        job_fingerprint: str,
        company_name: str,
        job_title: str,
        tailored_cv_json: str,
        audit_report_json: str,
    ) -> TailoredResumeRecord:
        now = datetime.now(timezone.utc)
        existing = self._tailored.get(job_fingerprint)
        record = TailoredResumeRecord(
            id=existing.id if existing else str(uuid.uuid4()),
            source_id=source_id,
            job_fingerprint=job_fingerprint,
            company_name=company_name,
            job_title=job_title,
            tailored_cv_json=tailored_cv_json,
            audit_report_json=audit_report_json,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._tailored[job_fingerprint] = record
        return record

    def get_tailored_resume(self, job_fingerprint: str) -> TailoredResumeRecord | None:
        return self._tailored.get(job_fingerprint)


# ---------------------------------------------------------------------------
# Fake parser
# ---------------------------------------------------------------------------


class FakeParser(ResumeParserAdapter):
    """Parser stub that returns a fixed CV and tracks call count.

    ``version`` controls the value returned by the ``parser_version`` property
    so that tests can simulate parser upgrades without touching production code.
    """

    def __init__(self, result: CV | None = None, version: str = "v-fake") -> None:
        self._result = result or _make_cv()
        self._version = version
        self.call_count = 0

    @property
    def parser_version(self) -> str:  # implements the abstract property
        return self._version

    def parse(self, content: str) -> CV:
        self.call_count += 1
        return self._result


# ---------------------------------------------------------------------------
# Helper: build service with fakes
# ---------------------------------------------------------------------------


def _make_service(
    *,
    parser: FakeParser | None = None,
    repo: FakeRepository | None = None,
) -> tuple[ResumeMemoryService, FakeRepository, FakeParser]:
    if repo is None:
        repo = FakeRepository()
    if parser is None:
        parser = FakeParser()
    svc = ResumeMemoryService(repository=repo, parser=parser)
    return svc, repo, parser


# ---------------------------------------------------------------------------
# resolve_original_resume — explicit path (fresh resume)
# ---------------------------------------------------------------------------


def test_resolve_with_explicit_path_returns_resolved_resume(
    tmp_path: Path, subtests
) -> None:
    """Providing an explicit path must return a ResolvedOriginalResume."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\n\nPython developer.")

    svc, repo, parser = _make_service()
    result = svc.resolve_original_resume(path=str(resume_file))

    with subtests.test("source path matches"):
        assert result.source.path == str(resume_file)

    with subtests.test("cv is a CV instance"):
        assert isinstance(result.cv, CV)

    with subtests.test("parser was called once"):
        assert parser.call_count == 1

    with subtests.test("source stored as active"):
        active = repo.get_active_original_source()
        assert active is not None
        assert active.path == str(resume_file)


# ---------------------------------------------------------------------------
# resolve_original_resume — cache hit (same hash, no reparse)
# ---------------------------------------------------------------------------


def test_resolve_with_unchanged_content_skips_reparsing(tmp_path: Path) -> None:
    """If the parsed record already exists with a matching hash, the parser must NOT be called."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\n\nPython developer.")

    svc, repo, parser = _make_service()

    # First call: parse and store.
    svc.resolve_original_resume(path=str(resume_file))
    assert parser.call_count == 1

    # Second call: same content → should use cached parsed record.
    svc.resolve_original_resume(path=str(resume_file))
    assert parser.call_count == 1, (
        "Parser should NOT be called again for unchanged content"
    )


# ---------------------------------------------------------------------------
# resolve_original_resume — cache miss (changed hash, reparse)
# ---------------------------------------------------------------------------


def test_resolve_reparses_when_content_changes(tmp_path: Path) -> None:
    """When the file content changes, the service must reparse."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe v1")

    svc, repo, parser = _make_service()

    svc.resolve_original_resume(path=str(resume_file))
    assert parser.call_count == 1

    # Modify the file content.
    resume_file.write_text("# Jane Doe v2 — changed content here")

    svc.resolve_original_resume(path=str(resume_file))
    assert parser.call_count == 2, "Parser MUST be called again after content change"


# ---------------------------------------------------------------------------
# resolve_original_resume — no path, falls back to latest source
# ---------------------------------------------------------------------------


def test_resolve_without_path_uses_latest_stored_source(tmp_path: Path) -> None:
    """With no explicit path, the service uses the most recently seen stored source."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe")

    svc, repo, parser = _make_service()

    # Register a source first via explicit path call.
    svc.resolve_original_resume(path=str(resume_file))

    # Now call without path — should resolve from stored source.
    result = svc.resolve_original_resume(path=None)
    assert result.source.path == str(resume_file)
    # Cache hit: parser should still only have been called once total.
    assert parser.call_count == 1


# ---------------------------------------------------------------------------
# resolve_original_resume — no path, no stored source → error
# ---------------------------------------------------------------------------


def test_resolve_without_path_and_no_stored_source_raises() -> None:
    """With no path and no stored sources, MissingOriginalResumeError must be raised."""
    svc, _, _ = _make_service()

    with pytest.raises(MissingOriginalResumeError, match="--resume-path"):
        svc.resolve_original_resume(path=None)


# ---------------------------------------------------------------------------
# save_tailored_resume
# ---------------------------------------------------------------------------


def test_save_tailored_resume_persists_record(tmp_path: Path, subtests) -> None:
    """save_tailored_resume must serialise CV and AuditResult and delegate to repository."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe")

    svc, repo, _ = _make_service()
    resolved = svc.resolve_original_resume(path=str(resume_file))

    tailored_cv = _make_cv(full_name="Jane Doe (tailored)")
    audit = _make_audit()

    record = svc.save_tailored_resume(
        source_id=resolved.source.id,
        job_fingerprint="fp-001",
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_cv=tailored_cv,
        audit_result=audit,
    )

    with subtests.test("record is a TailoredResumeRecord"):
        assert isinstance(record, TailoredResumeRecord)

    with subtests.test("job_fingerprint matches"):
        assert record.job_fingerprint == "fp-001"

    with subtests.test("tailored_cv_json is valid JSON containing full_name"):
        data = json.loads(record.tailored_cv_json)
        assert data["full_name"] == "Jane Doe (tailored)"

    with subtests.test("audit_report_json is valid JSON"):
        data = json.loads(record.audit_report_json)
        assert data["passed"] is True

    with subtests.test("record is retrievable from repository"):
        fetched = repo.get_tailored_resume("fp-001")
        assert fetched is not None
        assert fetched.job_fingerprint == "fp-001"


# ---------------------------------------------------------------------------
# ResumeParserAdapter protocol / interface
# ---------------------------------------------------------------------------


def test_fake_parser_implements_adapter_interface() -> None:
    """FakeParser must satisfy the ResumeParserAdapter interface (duck typing check)."""
    parser = FakeParser()
    cv = parser.parse("some content")
    assert isinstance(cv, CV)
    assert parser.parser_version != ""


# ---------------------------------------------------------------------------
# parser_version abstract-property contract
# ---------------------------------------------------------------------------


def test_concrete_parser_without_parser_version_cannot_be_instantiated() -> None:
    """A concrete parser that omits parser_version must fail at class instantiation.

    This verifies that the abstract-property enforcement fires early (TypeError at
    class creation / instantiation) rather than producing a late AttributeError.
    """

    with pytest.raises(TypeError):

        class _IncompleteParser(ResumeParserAdapter):
            """Concrete subclass that intentionally omits parser_version."""

            def parse(self, content: str) -> CV:
                return _make_cv()

        _IncompleteParser()  # must raise TypeError because parser_version is abstract


# ---------------------------------------------------------------------------
# resolve_original_resume — cache invalidation on parser-version change
# ---------------------------------------------------------------------------


def test_resolve_reparses_when_parser_version_changes(tmp_path: Path) -> None:
    """When the parser version changes, the service must reparse even if the content
    hash has not changed.

    Scenario:
    1. Parse with parser v1 → cached under (hash, "v1").
    2. Switch to parser v2 (same file, same content) → cache miss, reparse.
    """
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe")

    repo = FakeRepository()

    # First run: parser v1.
    parser_v1 = FakeParser(version="v1")
    svc_v1 = ResumeMemoryService(repository=repo, parser=parser_v1)
    svc_v1.resolve_original_resume(path=str(resume_file))
    assert parser_v1.call_count == 1

    # Second run: parser v2, same repo, same file, same content.
    parser_v2 = FakeParser(version="v2")
    svc_v2 = ResumeMemoryService(repository=repo, parser=parser_v2)
    svc_v2.resolve_original_resume(path=str(resume_file))
    assert parser_v2.call_count == 1, (
        "Parser v2 MUST be called because parser version changed from v1 to v2"
    )


# ---------------------------------------------------------------------------
# resolve_original_resume — path normalisation (no duplicate sources)
# ---------------------------------------------------------------------------


def test_resolve_relative_and_absolute_path_no_duplicate_source(
    tmp_path: Path, subtests
) -> None:
    """Resolving the same file via a relative path and then its absolute path must
    not create two separate source records or trigger two parse calls.
    """
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe")

    # Build a relative path from CWD → points to the same file as the absolute path.
    rel_path = os.path.relpath(str(resume_file))
    abs_path = str(resume_file)

    svc, repo, parser = _make_service()

    # First call via relative path.
    svc.resolve_original_resume(path=rel_path)

    # Second call via absolute path — same file, same content.
    svc.resolve_original_resume(path=abs_path)

    with subtests.test("only one source record created"):
        assert len(repo._sources) == 1, (
            "Relative and absolute paths for the same file must resolve to a "
            "single source record"
        )

    with subtests.test("parser called only once"):
        assert parser.call_count == 1, (
            "Parser must NOT be called again when content and parser version are "
            "unchanged, regardless of whether the path was relative or absolute"
        )


# ---------------------------------------------------------------------------
# resolve_original_resume — FileNotFoundError when file is missing
# ---------------------------------------------------------------------------


def test_resolve_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    """If the file at the given path does not exist, FileNotFoundError must propagate."""
    nonexistent = tmp_path / "does_not_exist.md"
    svc, _, _ = _make_service()

    with pytest.raises(FileNotFoundError):
        svc.resolve_original_resume(path=str(nonexistent))


def test_parser_raises_when_agent_returns_no_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """The parser adapter must fail clearly when the agent returns no structured output."""

    class _FakeAgent:
        def run_sync(self, content: str) -> SimpleNamespace:
            return SimpleNamespace(output=None)

    monkeypatch.setitem(
        sys.modules,
        "workflows.agents",
        SimpleNamespace(resume_parser_agent=_FakeAgent()),
    )

    parser = PydanticAIResumeParser()

    with pytest.raises(ValueError, match="returned no output"):
        parser.parse("# Jane Doe")


def test_parser_raises_when_agent_returns_invalid_output_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parser adapter must reject non-CV payloads from the agent."""

    class _FakeAgent:
        def run_sync(self, content: str) -> SimpleNamespace:
            return SimpleNamespace(output={"full_name": "Jane"})

    monkeypatch.setitem(
        sys.modules,
        "workflows.agents",
        SimpleNamespace(resume_parser_agent=_FakeAgent()),
    )

    parser = PydanticAIResumeParser()

    with pytest.raises(TypeError, match="expected CV"):
        parser.parse("# Jane Doe")


def test_resolve_raises_resume_memory_error_for_invalid_cached_cv_json(
    tmp_path: Path,
) -> None:
    """Corrupted cached CV JSON must be surfaced as a domain error."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe")

    svc, repo, _ = _make_service()
    resolved = svc.resolve_original_resume(path=str(resume_file))
    repo._parsed[resolved.source.id] = repo._parsed[resolved.source.id].model_copy(
        update={"cv_json": '{"full_name": "Jane Doe"'}
    )

    with pytest.raises(ResumeMemoryError, match="stored parsed resume"):
        svc.resolve_original_resume(path=str(resume_file))


def test_resolve_raises_resume_memory_error_when_parser_fails(tmp_path: Path) -> None:
    """Parser failures must be wrapped in a domain-level error."""

    class _FailingParser(FakeParser):
        def parse(self, content: str) -> CV:
            raise ValueError("agent misbehaved")

    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe")

    svc, _, _ = _make_service(parser=_FailingParser())

    with pytest.raises(ResumeMemoryError, match="Failed to parse"):
        svc.resolve_original_resume(path=str(resume_file))
