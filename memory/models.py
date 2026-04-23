"""Pydantic models for original and tailored resume memory."""

import json

from pydantic import AwareDatetime, BaseModel, field_validator

from models.agents.output import CV


class ResumeMemoryError(Exception):
    """Base error for resume memory failures."""


class MissingOriginalResumeError(ResumeMemoryError):
    """Raised when no original resume is available for a run."""


class ResumeSourceRecord(BaseModel):
    id: str
    path: str
    content_hash: str
    is_active: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime
    last_seen_at: AwareDatetime


class ParsedOriginalResumeRecord(BaseModel):
    """Represents a parsed original resume.

    This record is keyed one-to-one by source_id; it intentionally does not
    include a separate `id` field (the source_id is the effective primary key).
    """

    source_id: str
    content_hash: str
    parser_version: str
    cv_json: str
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @field_validator("cv_json")
    @classmethod
    def _validate_cv_json(cls, v: str) -> str:
        try:
            json.loads(v)
        except Exception as e:
            raise ValueError("cv_json must be valid JSON") from e
        return v


class TailoredResumeRecord(BaseModel):
    id: str
    source_id: str
    job_fingerprint: str
    company_name: str
    job_title: str
    tailored_cv_json: str
    audit_report_json: str
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @field_validator("tailored_cv_json", "audit_report_json")
    @classmethod
    def _validate_json_strings(cls, v: str) -> str:
        try:
            json.loads(v)
        except Exception as e:
            raise ValueError(
                "tailored_cv_json/audit_report_json must be valid JSON"
            ) from e
        return v


class ResolvedOriginalResume(BaseModel):
    source: ResumeSourceRecord
    cv: CV
