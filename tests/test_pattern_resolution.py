"""Tests for _resolve_pattern and _slugify helpers."""

from datetime import date

from resume_tailorator.main import _is_safe_path_component, _resolve_pattern, _slugify
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


class TestSlugify:
    def test_lowercases(self):
        assert _slugify("Google") == "google"

    def test_replaces_spaces_with_underscores(self):
        assert _slugify("Acme Corp") == "acme_corp"

    def test_removes_special_chars(self):
        assert _slugify("Google Inc. (Remote)") == "google_inc_remote"

    def test_handles_empty_string(self):
        assert _slugify("") == ""

    def test_handles_apostrophe(self):
        assert _slugify("John O'Connor") == "john_oconnor"

    def test_keeps_underscores(self):
        assert _slugify("senior_engineer") == "senior_engineer"


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
        # / is removed (not replaced with _), so "Senior/Staff" → "seniorstaff"
        assert actual == "google_inc_remote-seniorstaff_engineer-john_oconnor"

    def test_custom_pattern_without_defaults(self):
        result = _make_result()
        cv = _make_cv()
        template = "{full_name}_for_{company_name}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "jane_doe_for_acme_corp"

    def test_default_output_pattern(self):
        result = _make_result()
        cv = _make_cv()
        template = "{company_name}-{job_title}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "acme_corp-software_engineer"

    def test_default_resume_name_pattern(self):
        result = _make_result()
        cv = _make_cv()
        template = "{company_name}-{full_name}"
        actual = _resolve_pattern(template, result, cv)
        assert actual == "acme_corp-jane_doe"

    def test_timestamp_only(self):
        result = _make_result()
        cv = _make_cv()
        template = "{timestamp}"
        actual = _resolve_pattern(template, result, cv)
        today = date.today().strftime("%Y%m%d")
        assert actual == today


class TestIsSafePathComponent:
    def test_normal_name_is_safe(self):
        assert _is_safe_path_component("acme_corp-software_engineer")

    def test_empty_is_unsafe(self):
        assert not _is_safe_path_component("")

    def test_dot_is_unsafe(self):
        assert not _is_safe_path_component(".")

    def test_double_dot_is_unsafe(self):
        assert not _is_safe_path_component("..")

    def test_parent_reference_in_middle_is_unsafe(self):
        assert not _is_safe_path_component("foo..bar")

    def test_forward_slash_is_unsafe(self):
        assert not _is_safe_path_component("foo/bar")

    def test_backslash_is_unsafe(self):
        assert not _is_safe_path_component("foo\\bar")

    def test_leading_slash_is_unsafe(self):
        assert not _is_safe_path_component("/foo")

    def test_absolute_windows_path_is_unsafe(self):
        assert not _is_safe_path_component("C:")

    def test_null_bytes_are_unsafe(self):
        assert not _is_safe_path_component("foo\x00bar")
