"""Tests for SQLiteResumeMemoryRepository.

TDD RED → GREEN cycle for Task 3.

Design choices documented here:
- save_tailored_resume uses INSERT OR REPLACE semantics (upsert by job_fingerprint).
  Rationale: a job fingerprint uniquely identifies a job submission; re-running with the
  same fingerprint should overwrite the previous tailored result deterministically rather
  than duplicating rows or raising an error.
- Tests use :memory: SQLite databases for speed and isolation.
- Every timestamp returned by the repository must be timezone-aware UTC.
"""

import json

import pytest

from memory.models import ResumeMemoryError
from memory.sqlite_repository import SQLiteResumeMemoryRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CV_JSON = json.dumps({"full_name": "Jane Doe", "skills": ["Python"]})
SAMPLE_TAILORED_CV_JSON = json.dumps({"full_name": "Jane Doe (tailored)"})
SAMPLE_AUDIT_JSON = json.dumps({"score": 95})


@pytest.fixture
def repo() -> SQLiteResumeMemoryRepository:
    """Return a fresh in-memory SQLite repository for each test."""
    return SQLiteResumeMemoryRepository(db_path=":memory:")


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------


def test_repository_initialises_schema_without_error() -> None:
    """Constructing the repo should create all tables without raising."""
    repo = SQLiteResumeMemoryRepository(db_path=":memory:")
    # If schema init raised, we would not reach this assertion.
    assert repo is not None


# ---------------------------------------------------------------------------
# Original source: basic upsert & retrieval
# ---------------------------------------------------------------------------


def test_upsert_original_source_returns_source_record(repo, subtests) -> None:
    record = repo.upsert_original_source(
        path="/resumes/resume.md",
        content_hash="hash-abc",
        is_active=True,
    )

    with subtests.test("id is non-empty"):
        assert record.id != ""

    with subtests.test("path matches"):
        assert record.path == "/resumes/resume.md"

    with subtests.test("content_hash matches"):
        assert record.content_hash == "hash-abc"

    with subtests.test("is_active matches"):
        assert record.is_active is True

    with subtests.test("created_at is timezone-aware"):
        assert record.created_at.tzinfo is not None

    with subtests.test("updated_at is timezone-aware"):
        assert record.updated_at.tzinfo is not None

    with subtests.test("last_seen_at is timezone-aware"):
        assert record.last_seen_at.tzinfo is not None


def test_upsert_original_source_updates_existing_record_for_same_path(
    repo, subtests
) -> None:
    """Calling upsert twice with the same path should update, not duplicate."""
    first = repo.upsert_original_source(
        path="/resumes/resume.md",
        content_hash="hash-v1",
        is_active=True,
    )
    second = repo.upsert_original_source(
        path="/resumes/resume.md",
        content_hash="hash-v2",
        is_active=True,
    )

    with subtests.test("same id on update"):
        assert first.id == second.id

    with subtests.test("content_hash updated"):
        assert second.content_hash == "hash-v2"


# ---------------------------------------------------------------------------
# get_source_by_path
# ---------------------------------------------------------------------------


def test_get_source_by_path_returns_record(repo) -> None:
    repo.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=True)
    found = repo.get_source_by_path("/r/a.md")
    assert found is not None
    assert found.path == "/r/a.md"


def test_get_source_by_path_returns_none_for_unknown_path(repo) -> None:
    result = repo.get_source_by_path("/does/not/exist.md")
    assert result is None


# ---------------------------------------------------------------------------
# Active original source
# ---------------------------------------------------------------------------


def test_get_active_original_source_returns_none_when_empty(repo) -> None:
    assert repo.get_active_original_source() is None


def test_get_active_original_source_returns_active_record(repo) -> None:
    repo.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=True)
    active = repo.get_active_original_source()
    assert active is not None
    assert active.path == "/r/a.md"
    assert active.is_active is True


def test_set_active_original_source_clears_previous_active(repo, subtests) -> None:
    """Setting a new source active must deactivate all others atomically."""
    repo.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=True)
    second = repo.upsert_original_source(
        path="/r/b.md", content_hash="h2", is_active=False
    )

    repo.set_active_original_source(second.id)

    # Re-fetch both to confirm DB state.
    refreshed_first = repo.get_source_by_path("/r/a.md")
    refreshed_second = repo.get_source_by_path("/r/b.md")

    with subtests.test("previous source is now inactive"):
        assert refreshed_first is not None
        assert refreshed_first.is_active is False

    with subtests.test("new source is now active"):
        assert refreshed_second is not None
        assert refreshed_second.is_active is True


def test_upsert_with_is_active_true_deactivates_others(repo) -> None:
    """upsert_original_source(is_active=True) must also clear other actives."""
    repo.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=True)
    # Now upsert a second path as active.
    repo.upsert_original_source(path="/r/b.md", content_hash="h2", is_active=True)

    refreshed_first = repo.get_source_by_path("/r/a.md")
    assert refreshed_first is not None
    assert refreshed_first.is_active is False


# ---------------------------------------------------------------------------
# get_latest_original_source
# ---------------------------------------------------------------------------


def test_get_latest_original_source_returns_none_when_empty(repo) -> None:
    assert repo.get_latest_original_source() is None


def test_get_latest_original_source_returns_most_recently_created(repo) -> None:
    repo.upsert_original_source(path="/r/old.md", content_hash="h0", is_active=False)
    repo.upsert_original_source(path="/r/new.md", content_hash="h1", is_active=False)
    latest = repo.get_latest_original_source()
    assert latest is not None
    assert latest.path == "/r/new.md"


# ---------------------------------------------------------------------------
# Parsed original resume
# ---------------------------------------------------------------------------


def test_get_parsed_original_resume_returns_none_when_absent(repo) -> None:
    assert repo.get_parsed_original_resume("nonexistent-source-id") is None


def test_save_parsed_original_resume_returns_record(repo, subtests) -> None:
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    parsed = repo.save_parsed_original_resume(
        source_id=source.id,
        content_hash="h1",
        parser_version="v1.0",
        cv_json=SAMPLE_CV_JSON,
    )

    with subtests.test("source_id matches"):
        assert parsed.source_id == source.id

    with subtests.test("content_hash matches"):
        assert parsed.content_hash == "h1"

    with subtests.test("parser_version matches"):
        assert parsed.parser_version == "v1.0"

    with subtests.test("cv_json is valid JSON"):
        data = json.loads(parsed.cv_json)
        assert data["full_name"] == "Jane Doe"

    with subtests.test("created_at is timezone-aware"):
        assert parsed.created_at.tzinfo is not None

    with subtests.test("updated_at is timezone-aware"):
        assert parsed.updated_at.tzinfo is not None


def test_get_parsed_original_resume_returns_stored_record(repo) -> None:
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    repo.save_parsed_original_resume(
        source_id=source.id,
        content_hash="h1",
        parser_version="v1.0",
        cv_json=SAMPLE_CV_JSON,
    )
    found = repo.get_parsed_original_resume(source.id)
    assert found is not None
    assert found.source_id == source.id


def test_save_parsed_original_resume_upserts_by_source_id(repo, subtests) -> None:
    """Saving a parsed resume for an existing source_id must update in place."""
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    repo.save_parsed_original_resume(
        source_id=source.id,
        content_hash="h1",
        parser_version="v1.0",
        cv_json=SAMPLE_CV_JSON,
    )
    updated_cv = json.dumps({"full_name": "Jane Doe v2"})
    repo.save_parsed_original_resume(
        source_id=source.id,
        content_hash="h2",
        parser_version="v1.1",
        cv_json=updated_cv,
    )

    found = repo.get_parsed_original_resume(source.id)
    assert found is not None

    with subtests.test("content_hash updated"):
        assert found.content_hash == "h2"

    with subtests.test("parser_version updated"):
        assert found.parser_version == "v1.1"

    with subtests.test("cv_json updated"):
        assert json.loads(found.cv_json)["full_name"] == "Jane Doe v2"


# ---------------------------------------------------------------------------
# Tailored resume
# ---------------------------------------------------------------------------


def test_get_tailored_resume_returns_none_when_absent(repo) -> None:
    assert repo.get_tailored_resume("no-such-fingerprint") is None


def test_save_tailored_resume_returns_record(repo, subtests) -> None:
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    tailored = repo.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="job-fp-001",
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_cv_json=SAMPLE_TAILORED_CV_JSON,
        audit_report_json=SAMPLE_AUDIT_JSON,
    )

    with subtests.test("id is non-empty"):
        assert tailored.id != ""

    with subtests.test("source_id matches"):
        assert tailored.source_id == source.id

    with subtests.test("job_fingerprint matches"):
        assert tailored.job_fingerprint == "job-fp-001"

    with subtests.test("company_name matches"):
        assert tailored.company_name == "Acme Corp"

    with subtests.test("job_title matches"):
        assert tailored.job_title == "Software Engineer"

    with subtests.test("tailored_cv_json is valid JSON"):
        assert json.loads(tailored.tailored_cv_json)

    with subtests.test("audit_report_json is valid JSON"):
        assert json.loads(tailored.audit_report_json)

    with subtests.test("created_at is timezone-aware"):
        assert tailored.created_at.tzinfo is not None

    with subtests.test("updated_at is timezone-aware"):
        assert tailored.updated_at.tzinfo is not None


def test_get_tailored_resume_returns_stored_record(repo) -> None:
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    repo.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="job-fp-001",
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_cv_json=SAMPLE_TAILORED_CV_JSON,
        audit_report_json=SAMPLE_AUDIT_JSON,
    )
    found = repo.get_tailored_resume("job-fp-001")
    assert found is not None
    assert found.job_fingerprint == "job-fp-001"


def test_save_tailored_resume_replaces_on_duplicate_fingerprint(repo, subtests) -> None:
    """Saving with an existing job_fingerprint must overwrite, not duplicate.

    Design choice: INSERT OR REPLACE semantics.  A fingerprint uniquely
    identifies a job description; a repeat submission for the same job should
    overwrite the prior tailored result deterministically rather than leaving
    stale duplicates or raising a constraint error.
    """
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    repo.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="dup-fp",
        company_name="Acme v1",
        job_title="Engineer",
        tailored_cv_json=SAMPLE_TAILORED_CV_JSON,
        audit_report_json=SAMPLE_AUDIT_JSON,
    )
    new_tailored = json.dumps({"full_name": "Updated"})
    repo.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="dup-fp",
        company_name="Acme v2",
        job_title="Senior Engineer",
        tailored_cv_json=new_tailored,
        audit_report_json=SAMPLE_AUDIT_JSON,
    )

    found = repo.get_tailored_resume("dup-fp")
    assert found is not None

    with subtests.test("company_name updated"):
        assert found.company_name == "Acme v2"

    with subtests.test("job_title updated"):
        assert found.job_title == "Senior Engineer"

    with subtests.test("tailored_cv_json updated"):
        assert json.loads(found.tailored_cv_json)["full_name"] == "Updated"


# ---------------------------------------------------------------------------
# get_latest_original_source — orders by last_seen_at, not created_at
# ---------------------------------------------------------------------------


def test_get_latest_original_source_returns_most_recently_seen(repo) -> None:
    """Latest source must be the one with the highest last_seen_at, not created_at.

    Scenario: source A was created first, source B was created second.
    We then re-upsert source A (bumping its last_seen_at past B's).
    get_latest_original_source() must return A because it was seen most recently.
    """
    # Insert A first (older created_at).
    repo.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=False)
    # Insert B second (newer created_at under normal clock progression).
    repo.upsert_original_source(path="/r/b.md", content_hash="h2", is_active=False)
    # Re-upsert A — this bumps A's last_seen_at to "now", past B's.
    repo.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=False)

    latest = repo.get_latest_original_source()
    assert latest is not None
    assert latest.path == "/r/a.md", (
        "Expected the source with the most recent last_seen_at (A), "
        f"but got {latest.path!r}"
    )


# ---------------------------------------------------------------------------
# set_active_original_source — invalid source_id raises, preserves state
# ---------------------------------------------------------------------------


def test_set_active_original_source_raises_for_unknown_id(repo) -> None:
    """Passing a non-existent source_id must raise ResumeMemoryError, not silently pass."""
    with pytest.raises(ResumeMemoryError):
        repo.set_active_original_source("non-existent-id")


def test_set_active_original_source_preserves_active_when_raises(repo) -> None:
    """If set_active_original_source raises, the previously active source must stay active."""
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )

    with pytest.raises(ResumeMemoryError):
        repo.set_active_original_source("bad-id-that-does-not-exist")

    # The original source should still be active (no partial state mutation).
    still_active = repo.get_active_original_source()
    assert still_active is not None
    assert still_active.id == source.id


# ---------------------------------------------------------------------------
# save_parsed_original_resume — missing source raises domain error
# ---------------------------------------------------------------------------


def test_save_parsed_original_resume_raises_for_missing_source(repo) -> None:
    """Saving a parsed resume for a non-existent source must raise ResumeMemoryError."""
    with pytest.raises(ResumeMemoryError):
        repo.save_parsed_original_resume(
            source_id="ghost-source-id",
            content_hash="h1",
            parser_version="v1.0",
            cv_json=SAMPLE_CV_JSON,
        )


# ---------------------------------------------------------------------------
# save_tailored_resume — missing source raises domain error
# ---------------------------------------------------------------------------


def test_save_tailored_resume_raises_for_missing_source(repo) -> None:
    """Saving a tailored resume for a non-existent source must raise ResumeMemoryError."""
    with pytest.raises(ResumeMemoryError):
        repo.save_tailored_resume(
            source_id="ghost-source-id",
            job_fingerprint="fp-x",
            company_name="Acme",
            job_title="Engineer",
            tailored_cv_json=SAMPLE_TAILORED_CV_JSON,
            audit_report_json=SAMPLE_AUDIT_JSON,
        )


# ---------------------------------------------------------------------------
# created_at preservation across upserts
# ---------------------------------------------------------------------------


def test_save_parsed_original_resume_preserves_created_at_on_update(repo) -> None:
    """Re-saving a parsed resume must not change the original created_at timestamp."""
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    first = repo.save_parsed_original_resume(
        source_id=source.id,
        content_hash="h1",
        parser_version="v1.0",
        cv_json=SAMPLE_CV_JSON,
    )
    second = repo.save_parsed_original_resume(
        source_id=source.id,
        content_hash="h2",
        parser_version="v1.1",
        cv_json=SAMPLE_CV_JSON,
    )
    assert second.created_at == first.created_at, (
        "created_at must be preserved across upserts; "
        f"first={first.created_at!r}, second={second.created_at!r}"
    )
    assert second.updated_at >= first.updated_at


def test_save_tailored_resume_preserves_created_at_on_update(repo) -> None:
    """Re-saving a tailored resume (same fingerprint) must not change created_at."""
    source = repo.upsert_original_source(
        path="/r/a.md", content_hash="h1", is_active=True
    )
    first = repo.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="fp-preserve",
        company_name="Acme v1",
        job_title="Engineer",
        tailored_cv_json=SAMPLE_TAILORED_CV_JSON,
        audit_report_json=SAMPLE_AUDIT_JSON,
    )
    second = repo.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="fp-preserve",
        company_name="Acme v2",
        job_title="Senior Engineer",
        tailored_cv_json=SAMPLE_TAILORED_CV_JSON,
        audit_report_json=SAMPLE_AUDIT_JSON,
    )
    assert second.created_at == first.created_at, (
        "created_at must be preserved across upserts; "
        f"first={first.created_at!r}, second={second.created_at!r}"
    )
    assert second.updated_at >= first.updated_at


# ---------------------------------------------------------------------------
# Connection lifecycle — close() and context-manager support
# ---------------------------------------------------------------------------


def test_repository_close_is_callable() -> None:
    """repo.close() must exist and not raise."""
    r = SQLiteResumeMemoryRepository(db_path=":memory:")
    r.close()  # must not raise


def test_repository_supports_context_manager() -> None:
    """Using the repository as a context manager must close cleanly."""
    with SQLiteResumeMemoryRepository(db_path=":memory:") as r:
        r.upsert_original_source(path="/r/a.md", content_hash="h1", is_active=True)
    # After __exit__, the connection should be closed; further queries should raise.

    with pytest.raises(Exception):
        r.get_active_original_source()
