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

    assert str(error) == "No stored original resume found. Provide --resume-path on the first run."
