"""SQLite-backed implementation of ResumeMemoryRepository.

Uses stdlib ``sqlite3`` only — no ORM or third-party DB layer.

Runtime database location: ``files/resume_memory.sqlite3``
Tests should supply ``:memory:`` or a temporary path.

Design choices
--------------
* **Upsert for tailored resumes**: ``save_tailored_resume`` uses
  ``INSERT OR REPLACE`` keyed on ``job_fingerprint``.  A fingerprint uniquely
  identifies a job description; re-running against the same job should
  overwrite the previous tailored result deterministically rather than
  accumulating stale duplicates or raising a constraint error.

* **Active-source atomicity**: ``set_active_original_source`` and the
  ``upsert_original_source(is_active=True)`` path both run inside a single
  transaction that first clears all other active flags before setting the
  requested source active.  This guarantees at-most-one active source even if
  a crash or concurrent write occurs.

* **Row mapping**: every ``SELECT`` that returns a model passes through a
  dedicated ``_row_to_*`` helper so the mapping logic is centralised and the
  main methods stay readable.

* **Timestamps**: all timestamps are stored as ISO-8601 strings in UTC
  (``+00:00`` suffix).  On read they are parsed back to
  ``datetime`` objects with ``tzinfo=timezone.utc`` so Pydantic's
  ``AwareDatetime`` field accepts them without coercion issues.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from memory.models import (
    ParsedOriginalResumeRecord,
    ResumeMemoryError,
    ResumeSourceRecord,
    TailoredResumeRecord,
)
from memory.repository import ResumeMemoryRepository

# ---------------------------------------------------------------------------
# SQL DDL
# ---------------------------------------------------------------------------

_CREATE_ORIGINAL_RESUME_SOURCES = """
CREATE TABLE IF NOT EXISTS original_resume_sources (
    id           TEXT PRIMARY KEY,
    path         TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
)
"""

_CREATE_PARSED_ORIGINAL_RESUMES = """
CREATE TABLE IF NOT EXISTS parsed_original_resumes (
    source_id      TEXT PRIMARY KEY,
    content_hash   TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    cv_json        TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES original_resume_sources(id)
)
"""

_CREATE_TAILORED_RESUMES = """
CREATE TABLE IF NOT EXISTS tailored_resumes (
    id                 TEXT PRIMARY KEY,
    source_id          TEXT NOT NULL,
    job_fingerprint    TEXT NOT NULL UNIQUE,
    company_name       TEXT NOT NULL,
    job_title          TEXT NOT NULL,
    tailored_cv_json   TEXT NOT NULL,
    audit_report_json  TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES original_resume_sources(id)
)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: datetime) -> str:
    """Serialise a datetime to an ISO-8601 UTC string for DB storage."""
    return dt.astimezone(timezone.utc).isoformat()


def _parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 string from the DB back to a timezone-aware datetime."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        # Defensively treat naive timestamps stored by older code as UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _row_to_source(row: sqlite3.Row) -> ResumeSourceRecord:
    return ResumeSourceRecord(
        id=row["id"],
        path=row["path"],
        content_hash=row["content_hash"],
        is_active=bool(row["is_active"]),
        created_at=_parse_ts(row["created_at"]),
        updated_at=_parse_ts(row["updated_at"]),
        last_seen_at=_parse_ts(row["last_seen_at"]),
    )


def _row_to_parsed(row: sqlite3.Row) -> ParsedOriginalResumeRecord:
    return ParsedOriginalResumeRecord(
        source_id=row["source_id"],
        content_hash=row["content_hash"],
        parser_version=row["parser_version"],
        cv_json=row["cv_json"],
        created_at=_parse_ts(row["created_at"]),
        updated_at=_parse_ts(row["updated_at"]),
    )


def _row_to_tailored(row: sqlite3.Row) -> TailoredResumeRecord:
    return TailoredResumeRecord(
        id=row["id"],
        source_id=row["source_id"],
        job_fingerprint=row["job_fingerprint"],
        company_name=row["company_name"],
        job_title=row["job_title"],
        tailored_cv_json=row["tailored_cv_json"],
        audit_report_json=row["audit_report_json"],
        created_at=_parse_ts(row["created_at"]),
        updated_at=_parse_ts(row["updated_at"]),
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class SQLiteResumeMemoryRepository(ResumeMemoryRepository):
    """SQLite-backed resume memory repository.

    Parameters
    ----------
    db_path:
        File-system path for the SQLite database, or ``":memory:"`` for an
        in-process ephemeral database (used by tests).
    """

    def __init__(self, db_path: str | Path = "files/resume_memory.sqlite3") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Enable WAL mode for slightly better concurrent read behaviour on disk.
        if self._db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._initialise_schema()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _initialise_schema(self) -> None:
        with self._conn:
            self._conn.execute(_CREATE_ORIGINAL_RESUME_SOURCES)
            self._conn.execute(_CREATE_PARSED_ORIGINAL_RESUMES)
            self._conn.execute(_CREATE_TAILORED_RESUMES)

    def _ensure_source_exists(self, source_id: str) -> None:
        """Raise ResumeMemoryError if source_id is not in the DB."""
        cur = self._conn.execute(
            "SELECT 1 FROM original_resume_sources WHERE id = ? LIMIT 1",
            (source_id,),
        )
        if cur.fetchone() is None:
            raise ResumeMemoryError(
                f"Original resume source '{source_id}' does not exist."
            )

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    def __enter__(self) -> "SQLiteResumeMemoryRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # ResumeMemoryRepository contract
    # ------------------------------------------------------------------

    def get_active_original_source(self) -> ResumeSourceRecord | None:
        cur = self._conn.execute(
            "SELECT * FROM original_resume_sources WHERE is_active = 1 LIMIT 1"
        )
        row = cur.fetchone()
        return _row_to_source(row) if row else None

    def get_latest_original_source(self) -> ResumeSourceRecord | None:
        cur = self._conn.execute(
            "SELECT * FROM original_resume_sources ORDER BY last_seen_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        return _row_to_source(row) if row else None

    def get_source_by_path(self, path: str) -> ResumeSourceRecord | None:
        cur = self._conn.execute(
            "SELECT * FROM original_resume_sources WHERE path = ?",
            (path,),
        )
        row = cur.fetchone()
        return _row_to_source(row) if row else None

    def upsert_original_source(
        self,
        path: str,
        content_hash: str,
        is_active: bool,
    ) -> ResumeSourceRecord:
        now = _now_utc()
        now_str = _ts(now)

        with self._conn:
            # Check if a record already exists for this path.
            cur = self._conn.execute(
                "SELECT id, created_at FROM original_resume_sources WHERE path = ?",
                (path,),
            )
            existing = cur.fetchone()

            if existing:
                record_id = existing["id"]
                created_at_str = existing["created_at"]
                if is_active:
                    # Clear all other active flags first (atomic with the UPDATE below).
                    self._conn.execute(
                        "UPDATE original_resume_sources SET is_active = 0 WHERE id != ?",
                        (record_id,),
                    )
                self._conn.execute(
                    """
                    UPDATE original_resume_sources
                    SET content_hash = ?,
                        is_active    = ?,
                        updated_at   = ?,
                        last_seen_at = ?
                    WHERE id = ?
                    """,
                    (content_hash, int(is_active), now_str, now_str, record_id),
                )
            else:
                record_id = str(uuid.uuid4())
                created_at_str = now_str
                if is_active:
                    self._conn.execute(
                        "UPDATE original_resume_sources SET is_active = 0 WHERE id != ?",
                        (record_id,),
                    )
                self._conn.execute(
                    """
                    INSERT INTO original_resume_sources
                        (id, path, content_hash, is_active, created_at, updated_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        path,
                        content_hash,
                        int(is_active),
                        created_at_str,
                        now_str,
                        now_str,
                    ),
                )

        return ResumeSourceRecord(
            id=record_id,
            path=path,
            content_hash=content_hash,
            is_active=is_active,
            created_at=_parse_ts(created_at_str),
            updated_at=now,
            last_seen_at=now,
        )

    def set_active_original_source(self, source_id: str) -> None:
        # Validate source exists before mutating any state.
        self._ensure_source_exists(source_id)
        with self._conn:
            # Deactivate all sources, then activate only the requested one.
            self._conn.execute("UPDATE original_resume_sources SET is_active = 0")
            self._conn.execute(
                "UPDATE original_resume_sources SET is_active = 1, updated_at = ? WHERE id = ?",
                (_ts(_now_utc()), source_id),
            )

    def get_parsed_original_resume(
        self, source_id: str
    ) -> ParsedOriginalResumeRecord | None:
        cur = self._conn.execute(
            "SELECT * FROM parsed_original_resumes WHERE source_id = ?",
            (source_id,),
        )
        row = cur.fetchone()
        return _row_to_parsed(row) if row else None

    def save_parsed_original_resume(
        self,
        source_id: str,
        content_hash: str,
        parser_version: str,
        cv_json: str,
    ) -> ParsedOriginalResumeRecord:
        # Validate source exists before attempting any writes.
        self._ensure_source_exists(source_id)

        now = _now_utc()
        now_str = _ts(now)

        with self._conn:
            # Check whether a record already exists so we can preserve created_at.
            cur = self._conn.execute(
                "SELECT created_at FROM parsed_original_resumes WHERE source_id = ?",
                (source_id,),
            )
            existing = cur.fetchone()
            created_at_str = existing["created_at"] if existing else now_str

            self._conn.execute(
                """
                INSERT INTO parsed_original_resumes
                    (source_id, content_hash, parser_version, cv_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    content_hash   = excluded.content_hash,
                    parser_version = excluded.parser_version,
                    cv_json        = excluded.cv_json,
                    updated_at     = excluded.updated_at
                """,
                (
                    source_id,
                    content_hash,
                    parser_version,
                    cv_json,
                    created_at_str,
                    now_str,
                ),
            )

        return ParsedOriginalResumeRecord(
            source_id=source_id,
            content_hash=content_hash,
            parser_version=parser_version,
            cv_json=cv_json,
            created_at=_parse_ts(created_at_str),
            updated_at=now,
        )

    def save_tailored_resume(
        self,
        source_id: str,
        job_fingerprint: str,
        company_name: str,
        job_title: str,
        tailored_cv_json: str,
        audit_report_json: str,
    ) -> TailoredResumeRecord:
        # Validate source exists before attempting any writes.
        self._ensure_source_exists(source_id)

        now = _now_utc()
        now_str = _ts(now)

        with self._conn:
            # Preserve created_at for existing fingerprints.
            cur = self._conn.execute(
                "SELECT id, created_at FROM tailored_resumes WHERE job_fingerprint = ?",
                (job_fingerprint,),
            )
            existing = cur.fetchone()
            record_id = existing["id"] if existing else str(uuid.uuid4())
            created_at_str = existing["created_at"] if existing else now_str

            self._conn.execute(
                """
                INSERT INTO tailored_resumes
                    (id, source_id, job_fingerprint, company_name, job_title,
                     tailored_cv_json, audit_report_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_fingerprint) DO UPDATE SET
                    source_id         = excluded.source_id,
                    company_name      = excluded.company_name,
                    job_title         = excluded.job_title,
                    tailored_cv_json  = excluded.tailored_cv_json,
                    audit_report_json = excluded.audit_report_json,
                    updated_at        = excluded.updated_at
                """,
                (
                    record_id,
                    source_id,
                    job_fingerprint,
                    company_name,
                    job_title,
                    tailored_cv_json,
                    audit_report_json,
                    created_at_str,
                    now_str,
                ),
            )

        return TailoredResumeRecord(
            id=record_id,
            source_id=source_id,
            job_fingerprint=job_fingerprint,
            company_name=company_name,
            job_title=job_title,
            tailored_cv_json=tailored_cv_json,
            audit_report_json=audit_report_json,
            created_at=_parse_ts(created_at_str),
            updated_at=now,
        )

    def get_tailored_resume(self, job_fingerprint: str) -> TailoredResumeRecord | None:
        cur = self._conn.execute(
            "SELECT * FROM tailored_resumes WHERE job_fingerprint = ?",
            (job_fingerprint,),
        )
        row = cur.fetchone()
        return _row_to_tailored(row) if row else None
