"""Resume memory orchestration service.

``ResumeMemoryService`` is the single entry point for the CLI to:

1. Resolve an original resume (from an explicit file path or the latest stored
   source), re-parsing it only when the file content has changed.
2. Persist a tailored resume result alongside its audit report.

All heavy I/O (hashing, parsing, storage) is delegated to the injected
``repository`` and ``parser`` so that the service can be tested without any
real files or model calls.
"""

import hashlib
from pathlib import Path

from memory.models import (
    MissingOriginalResumeError,
    ResolvedOriginalResume,
    TailoredResumeRecord,
)
from memory.parser import ResumeParserAdapter
from memory.repository import ResumeMemoryRepository
from models.agents.output import AuditResult, CV


def _hash_content(content: str) -> str:
    """Return a hex SHA-256 digest of *content*."""
    return hashlib.sha256(content.encode()).hexdigest()


class ResumeMemoryService:
    """Orchestrates repository and parser to manage original and tailored resumes."""

    def __init__(
        self,
        repository: ResumeMemoryRepository,
        parser: ResumeParserAdapter,
    ) -> None:
        self._repo = repository
        self._parser = parser

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_original_resume(
        self,
        *,
        path: str | None,
    ) -> ResolvedOriginalResume:
        """Resolve the original resume to use for a tailoring run.

        Resolution order
        ----------------
        1. If *path* is given, read the file at that path.
        2. If *path* is ``None``, fetch the latest stored source from the
           repository and read the file from its recorded path.
        3. If no stored source exists (first ever run), raise
           ``MissingOriginalResumeError`` with an actionable message.

        Caching
        -------
        The resolved file content is hashed.  If the repository already holds a
        parsed record for this source **with the same content hash and the same
        parser version**, the stored ``CV`` is returned directly and the parser
        is **not** called again.  If the hash or parser version has changed (or
        no parsed record exists), the parser is invoked and the result is
        persisted.

        Path normalisation
        ------------------
        When *path* is given it is resolved to an absolute, canonical path
        before being stored.  This ensures that the same file reached via a
        relative path and via its absolute path is treated as a single source
        record rather than two distinct ones.

        Args:
            path: Absolute or relative path to a resume markdown file, or
                ``None`` to use the latest stored source.

        Returns:
            ``ResolvedOriginalResume`` containing the active source record and
            the parsed ``CV``.

        Raises:
            MissingOriginalResumeError: When *path* is ``None`` and no original
                resume has been stored yet.
            FileNotFoundError: When the resolved file path does not exist on
                disk.
        """
        # ---- Step 1: Determine file path and read content ---------------
        if path is not None:
            file_path = str(Path(path).resolve())
        else:
            latest = self._repo.get_latest_original_source()
            if latest is None:
                raise MissingOriginalResumeError(
                    "No original resume found. Please provide a path to your "
                    "resume with --resume on the first run."
                )
            file_path = latest.path  # already normalised when it was stored

        content = Path(file_path).read_text(encoding="utf-8")
        content_hash = _hash_content(content)

        # ---- Step 2: Upsert source record and set it active -------------
        source = self._repo.upsert_original_source(
            path=file_path,
            content_hash=content_hash,
            is_active=True,
        )

        # ---- Step 3: Try cache; reparse on miss, hash change, or version change ----
        parsed_record = self._repo.get_parsed_original_resume(source.id)
        current_parser_version = self._parser.parser_version

        if (
            parsed_record is not None
            and parsed_record.content_hash == content_hash
            and parsed_record.parser_version == current_parser_version
        ):
            # Cache hit — deserialise stored JSON back into a CV model.
            cv = CV.model_validate_json(parsed_record.cv_json)
        else:
            # Cache miss — parse and persist.
            cv = self._parser.parse(content)
            self._repo.save_parsed_original_resume(
                source_id=source.id,
                content_hash=content_hash,
                parser_version=current_parser_version,
                cv_json=cv.model_dump_json(),
            )

        return ResolvedOriginalResume(source=source, cv=cv)

    def save_tailored_resume(
        self,
        *,
        source_id: str,
        job_fingerprint: str,
        company_name: str,
        job_title: str,
        tailored_cv: CV,
        audit_result: AuditResult,
    ) -> TailoredResumeRecord:
        """Persist a completed tailored resume together with its audit report.

        Args:
            source_id: ID of the original source record this tailoring started
                from.
            job_fingerprint: Deterministic fingerprint of the job description
                (e.g. a hash of its URL + title).
            company_name: Name of the hiring company.
            job_title: Title of the target role.
            tailored_cv: The rewritten ``CV`` produced by the writer agent.
            audit_result: The ``AuditResult`` produced by the auditor agent.

        Returns:
            The persisted ``TailoredResumeRecord``.
        """
        return self._repo.save_tailored_resume(
            source_id=source_id,
            job_fingerprint=job_fingerprint,
            company_name=company_name,
            job_title=job_title,
            tailored_cv_json=tailored_cv.model_dump_json(),
            audit_report_json=audit_result.model_dump_json(),
        )
