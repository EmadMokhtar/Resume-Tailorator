"""Repository contract for resume memory."""

from abc import ABC, abstractmethod

from memory.models import (
    ParsedOriginalResumeRecord,
    ResumeSourceRecord,
    TailoredResumeRecord,
)


class ResumeMemoryRepository(ABC):
    @abstractmethod
    def get_active_original_source(self) -> ResumeSourceRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_original_source(self) -> ResumeSourceRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get_source_by_path(self, path: str) -> ResumeSourceRecord | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_original_source(
        self,
        path: str,
        content_hash: str,
        is_active: bool,
    ) -> ResumeSourceRecord:
        raise NotImplementedError

    @abstractmethod
    def get_parsed_original_resume(
        self,
        source_id: str,
    ) -> ParsedOriginalResumeRecord | None:
        raise NotImplementedError

    @abstractmethod
    def save_parsed_original_resume(
        self,
        source_id: str,
        content_hash: str,
        parser_version: str,
        cv_json: str,
    ) -> ParsedOriginalResumeRecord:
        raise NotImplementedError

    @abstractmethod
    def set_active_original_source(self, source_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_tailored_resume(
        self,
        source_id: str,
        job_fingerprint: str,
        company_name: str,
        job_title: str,
        tailored_cv_json: str,
        audit_report_json: str,
    ) -> TailoredResumeRecord:
        raise NotImplementedError

    @abstractmethod
    def get_tailored_resume(self, job_fingerprint: str) -> TailoredResumeRecord | None:
        raise NotImplementedError
