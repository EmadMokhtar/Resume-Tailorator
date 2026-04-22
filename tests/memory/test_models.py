import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from memory import models as memory_models


def test_resume_source_record_round_trip() -> None:
    record = memory_models.ResumeSourceRecord(
        id="resume-1",
        path="/tmp/resume.md",
        content_hash="abc123",
        is_active=True,
        created_at="2026-04-21T20:00:00+00:00",
        updated_at="2026-04-21T20:00:00+00:00",
        last_seen_at="2026-04-21T20:00:00+00:00",
    )

    assert record.path == "/tmp/resume.md"
    assert record.is_active is True


def test_resolved_original_resume_keeps_source_and_cv(sample_cv) -> None:
    source = memory_models.ResumeSourceRecord(
        id="resume-1",
        path="/tmp/resume.md",
        content_hash="abc123",
        is_active=True,
        created_at="2026-04-21T20:00:00+00:00",
        updated_at="2026-04-21T20:00:00+00:00",
        last_seen_at="2026-04-21T20:00:00+00:00",
    )

    resolved = memory_models.ResolvedOriginalResume(source=source, cv=sample_cv)

    assert resolved.source.id == "resume-1"
    assert resolved.cv.full_name == sample_cv.full_name


def test_missing_original_resume_error_has_clear_message() -> None:
    error = memory_models.MissingOriginalResumeError(
        "No stored original resume found. Provide --resume-path on the first run."
    )

    assert (
        str(error)
        == "No stored original resume found. Provide --resume-path on the first run."
    )


def test_resume_memory_error_is_exported() -> None:
    import memory

    assert hasattr(memory, "ResumeMemoryError")
    assert "ResumeMemoryError" in getattr(memory, "__all__", [])


def test_timestamp_fields_require_aware_datetimes() -> None:
    naive_dt = datetime(2026, 4, 21, 20, 0, 0)
    aware_dt = datetime(2026, 4, 21, 20, 0, 0, tzinfo=timezone.utc)

    # ResumeSourceRecord should reject naive datetime
    with pytest.raises(ValidationError):
        memory_models.ResumeSourceRecord(
            id="r1",
            path="/tmp/resume.md",
            content_hash="abc",
            is_active=True,
            created_at=naive_dt,
            updated_at=naive_dt,
            last_seen_at=naive_dt,
        )

    # Should accept aware datetimes
    rec = memory_models.ResumeSourceRecord(
        id="r2",
        path="/tmp/resume.md",
        content_hash="abc",
        is_active=True,
        created_at=aware_dt,
        updated_at=aware_dt,
        last_seen_at=aware_dt,
    )
    assert rec.created_at.tzinfo is not None

    # ParsedOriginalResumeRecord should also reject naive datetimes
    with pytest.raises(ValidationError):
        memory_models.ParsedOriginalResumeRecord(
            source_id="s2",
            content_hash="ch",
            parser_version="v1",
            cv_json=json.dumps({"full_name": "Test"}),
            created_at=naive_dt,
            updated_at=naive_dt,
        )

    # TailoredResumeRecord should also reject naive datetimes
    with pytest.raises(ValidationError):
        memory_models.TailoredResumeRecord(
            id="t3",
            source_id="s2",
            job_fingerprint="jf",
            company_name="C",
            job_title="Engineer",
            tailored_cv_json=json.dumps({"full_name": "Test"}),
            audit_report_json=json.dumps({"score": 1}),
            created_at=naive_dt,
            updated_at=naive_dt,
        )


def test_parsed_and_tailored_records_validate_json_fields() -> None:
    aware_ts = "2026-04-21T20:00:00+00:00"

    # ParsedOriginalResumeRecord: invalid cv_json should raise
    with pytest.raises(ValidationError):
        memory_models.ParsedOriginalResumeRecord(
            source_id="s1",
            content_hash="ch",
            parser_version="v1",
            cv_json="not-a-json",
            created_at=aware_ts,
            updated_at=aware_ts,
        )

    # Valid JSON should pass
    parsed = memory_models.ParsedOriginalResumeRecord(
        source_id="s1",
        content_hash="ch",
        parser_version="v1",
        cv_json=json.dumps({"full_name": "Alice"}),
        created_at=aware_ts,
        updated_at=aware_ts,
    )
    assert json.loads(parsed.cv_json)["full_name"] == "Alice"

    # TailoredResumeRecord: invalid tailored_cv_json / audit_report_json should raise
    with pytest.raises(ValidationError):
        memory_models.TailoredResumeRecord(
            id="t1",
            source_id="s1",
            job_fingerprint="jf",
            company_name="C",
            job_title="Engineer",
            tailored_cv_json="not-json",
            audit_report_json=json.dumps({"score": 1}),
            created_at=aware_ts,
            updated_at=aware_ts,
        )

    with pytest.raises(ValidationError):
        memory_models.TailoredResumeRecord(
            id="t1",
            source_id="s1",
            job_fingerprint="jf",
            company_name="C",
            job_title="Engineer",
            tailored_cv_json=json.dumps({"full_name": "Bob"}),
            audit_report_json="not-json",
            created_at=aware_ts,
            updated_at=aware_ts,
        )

    # Valid JSONs should pass
    tailored = memory_models.TailoredResumeRecord(
        id="t2",
        source_id="s1",
        job_fingerprint="jf",
        company_name="C",
        job_title="Engineer",
        tailored_cv_json=json.dumps({"full_name": "Bob"}),
        audit_report_json=json.dumps({"score": 2}),
        created_at=aware_ts,
        updated_at=aware_ts,
    )
    assert json.loads(tailored.tailored_cv_json)["full_name"] == "Bob"
