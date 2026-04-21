"""Pydantic models for original and tailored resume memory."""

from datetime import datetime

from pydantic import BaseModel

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
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


class ParsedOriginalResumeRecord(BaseModel):
    source_id: str
    content_hash: str
    parser_version: str
    cv_json: str
    created_at: datetime
    updated_at: datetime


class TailoredResumeRecord(BaseModel):
    id: str
    source_id: str
    job_fingerprint: str
    company_name: str
    job_title: str
    tailored_cv_json: str
    audit_report_json: str
    created_at: datetime
    updated_at: datetime


class ResolvedOriginalResume(BaseModel):
    source: ResumeSourceRecord
    cv: CV
