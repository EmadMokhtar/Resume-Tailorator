# Resume Memory System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SQLite-backed resume memory system that stores the original resume and job-specific tailored resumes, reuses parsed original resume data when valid, and makes every job submission start from the original resume.

**Architecture:** Add a focused `memory/` subsystem with record models, a repository contract, a SQLite implementation, a parser adapter, and a service that resolves the effective original resume for each run. Refactor the workflow to accept a structured original `CV` instead of reparsing raw markdown, then wire `main.py` to choose the explicit resume path or fall back to the latest stored original resume and persist the tailored output after successful runs.

**Tech Stack:** Python 3.13, sqlite3, Pydantic v2, pydantic-ai, pytest, pytest-asyncio, pytest-subtests, uv, Make

---

## File Structure

### Create

- `memory/__init__.py` — exports the memory subsystem surface.
- `memory/models.py` — Pydantic records and domain errors for original and tailored resume memory.
- `memory/repository.py` — abstract repository contract for original and tailored resume persistence.
- `memory/sqlite_repository.py` — SQLite-backed repository implementation using `sqlite3`.
- `memory/parser.py` — adapter that turns markdown into `CV` using `resume_parser_agent`.
- `memory/service.py` — orchestration layer for original-resume resolution, cache invalidation, and tailored-resume persistence.
- `tests/conftest.py` — pytest global setup, including real-model blocking.
- `tests/test_smoke.py` — basic harness smoke test.
- `tests/memory/test_models.py` — model and error tests.
- `tests/memory/test_sqlite_repository.py` — repository behavior tests.
- `tests/memory/test_service.py` — memory service behavior tests.
- `tests/workflows/test_resume_tailor_workflow.py` — workflow contract test for structured `CV` input.
- `tests/test_main.py` — CLI integration tests.

### Modify

- `pyproject.toml` — add test dependencies.
- `Makefile` — add `test` target and simplify `run` to let `main.py` own validation and memory resolution.
- `.gitignore` — ignore the SQLite memory database.
- `main.py` — parse CLI args, resolve original resume through the memory service, run workflow, persist tailored results.
- `utils/validate_inputs.py` — expose reusable validation helpers instead of exiting in a standalone preflight-only script.
- `models/workflow.py` — extend `ResumeTailorResult` with `job_title`.
- `workflows/__init__.py` — accept a structured original `CV` instead of raw markdown and stop calling `resume_parser_agent` directly.
- `README.md` — document `--resume-path`, latest-original fallback, first-run behavior, and memory semantics.

---

### Task 1: Add test tooling and repo hygiene

**Files:**
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Modify: `.gitignore`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Add the test dependencies and Make targets**

```toml
[dependency-groups]
dev = [
    "ruff>=0.14.6",
    "pytest>=8.3.5",
    "pytest-asyncio>=0.25.3",
    "pytest-subtests>=0.14.2",
]
```

```make
.PHONY: help install/uv install install/dev test tests run

test: install/dev ## Run the test suite
	@echo "🧪 Running tests..."
	@uv run pytest

tests: test ## Alias for test

run: install ## Run the resume tailorator agentic workflow
	@echo "🚀 Running Resume Tailorator..."
	@uv run python main.py
```

```gitignore
files/resume_memory.sqlite3
files/resume_memory.sqlite3-journal
```

- [ ] **Step 2: Add pytest bootstrap files**

```python
"""Pytest configuration for Resume Tailorator."""

import pytest

from pydantic_ai import models

from models.agents.output import CV, WorkExperience


models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def sample_cv() -> CV:
    return CV(
        full_name="Jane Doe",
        contact_info="jane@example.com",
        summary="Platform engineer with Python experience.",
        skills=["Python", "SQL", "Communication"],
        projects=["Built internal tooling"],
        experience=[
            WorkExperience(
                company="Acme",
                role="Software Engineer",
                dates="2022-2026",
                highlights=["Built Python services", "Improved reliability"],
            )
        ],
        education=["BSc Computer Science"],
        certifications=[],
        publications=[],
    )
```

```python
def test_pytest_harness() -> None:
    assert True
```

- [ ] **Step 3: Install dev dependencies**

Run: `make install/dev`
Expected: `uv sync --dev` completes successfully and installs pytest packages.

- [ ] **Step 4: Run the smoke test**

Run: `make test`
Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml Makefile .gitignore tests/conftest.py tests/test_smoke.py
git commit -m "test: add pytest harness for resume memory work"
```

### Task 2: Add memory records and repository contract

**Files:**
- Create: `memory/__init__.py`
- Create: `memory/models.py`
- Create: `memory/repository.py`
- Test: `tests/memory/test_models.py`

- [ ] **Step 1: Write the failing model and contract tests**

```python
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
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `make test`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory'`.

- [ ] **Step 3: Implement the records and repository contract**

```python
"""Memory subsystem exports."""

from memory.models import (
    MissingOriginalResumeError,
    ParsedOriginalResumeRecord,
    ResolvedOriginalResume,
    ResumeSourceRecord,
    TailoredResumeRecord,
)
from memory.repository import ResumeMemoryRepository

__all__ = [
    "MissingOriginalResumeError",
    "ParsedOriginalResumeRecord",
    "ResolvedOriginalResume",
    "ResumeMemoryRepository",
    "ResumeSourceRecord",
    "TailoredResumeRecord",
]
```

```python
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
```

```python
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
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `make test`
Expected: PASS for `tests/memory/test_models.py`.

- [ ] **Step 5: Commit**

```bash
git add memory/__init__.py memory/models.py memory/repository.py tests/memory/test_models.py
git commit -m "feat(model): add resume memory records and contract"
```

### Task 3: Implement the SQLite repository

**Files:**
- Create: `memory/sqlite_repository.py`
- Test: `tests/memory/test_sqlite_repository.py`

- [ ] **Step 1: Write the failing SQLite repository tests**

```python
from memory.sqlite_repository import SQLiteResumeMemoryRepository


def test_repository_upserts_and_marks_active_source(tmp_path) -> None:
    db_path = tmp_path / "resume_memory.sqlite3"
    repository = SQLiteResumeMemoryRepository(str(db_path))

    first = repository.upsert_original_source("/tmp/resume-a.md", "hash-a", True)
    second = repository.upsert_original_source("/tmp/resume-b.md", "hash-b", True)

    assert repository.get_active_original_source().id == second.id
    assert repository.get_source_by_path("/tmp/resume-a.md").is_active is False


def test_repository_saves_parsed_original_resume(tmp_path) -> None:
    db_path = tmp_path / "resume_memory.sqlite3"
    repository = SQLiteResumeMemoryRepository(str(db_path))
    source = repository.upsert_original_source("/tmp/resume.md", "hash-a", True)

    repository.save_parsed_original_resume(
        source_id=source.id,
        content_hash="hash-a",
        parser_version="cv-v1",
        cv_json='{"full_name":"Jane Doe"}',
    )

    parsed = repository.get_parsed_original_resume(source.id)

    assert parsed is not None
    assert parsed.parser_version == "cv-v1"


def test_repository_saves_tailored_resume_by_job_fingerprint(tmp_path) -> None:
    db_path = tmp_path / "resume_memory.sqlite3"
    repository = SQLiteResumeMemoryRepository(str(db_path))
    source = repository.upsert_original_source("/tmp/resume.md", "hash-a", True)

    repository.save_tailored_resume(
        source_id=source.id,
        job_fingerprint="job-123",
        company_name="Acme",
        job_title="Platform Engineer",
        tailored_cv_json='{"full_name":"Jane Doe"}',
        audit_report_json='{"passed": true}',
    )

    tailored = repository.get_tailored_resume("job-123")

    assert tailored is not None
    assert tailored.company_name == "Acme"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `make test`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory.sqlite_repository'`.

- [ ] **Step 3: Implement the SQLite repository**

```python
"""SQLite repository for original and tailored resume memory."""

from datetime import datetime, timezone
import sqlite3
import uuid

from memory import models as memory_models
from memory.repository import ResumeMemoryRepository


class SQLiteResumeMemoryRepository(ResumeMemoryRepository):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS original_resume_sources (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    content_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS parsed_original_resumes (
                    source_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    cv_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES original_resume_sources(id)
                );

                CREATE TABLE IF NOT EXISTS tailored_resumes (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    job_fingerprint TEXT NOT NULL UNIQUE,
                    company_name TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    tailored_cv_json TEXT NOT NULL,
                    audit_report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES original_resume_sources(id)
                );
                """
            )

    def upsert_original_source(
        self,
        path: str,
        content_hash: str,
        is_active: bool,
    ) -> memory_models.ResumeSourceRecord:
        now = datetime.now(timezone.utc).isoformat()
        existing = self.get_source_by_path(path)
        source_id = existing.id if existing else str(uuid.uuid4())
        with self._connect() as connection:
            if is_active:
                connection.execute("UPDATE original_resume_sources SET is_active = 0")
            connection.execute(
                """
                INSERT INTO original_resume_sources (
                    id, path, content_hash, is_active, created_at, updated_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at,
                    last_seen_at = excluded.last_seen_at
                """,
                (source_id, path, content_hash, int(is_active), now, now, now),
            )
        return self.get_source_by_path(path)
```

```python
    def get_source_by_path(self, path: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM original_resume_sources WHERE path = ?",
                (path,),
            ).fetchone()
        return self._row_to_source(row) if row else None

    def get_active_original_source(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM original_resume_sources WHERE is_active = 1 LIMIT 1"
            ).fetchone()
        return self._row_to_source(row) if row else None

    def get_latest_original_source(self):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM original_resume_sources
                ORDER BY last_seen_at DESC
                LIMIT 1
                """
            ).fetchone()
        return self._row_to_source(row) if row else None

    def get_parsed_original_resume(self, source_id: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM parsed_original_resumes WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return memory_models.ParsedOriginalResumeRecord(**dict(row)) if row else None

    def save_parsed_original_resume(
        self,
        source_id: str,
        content_hash: str,
        parser_version: str,
        cv_json: str,
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO parsed_original_resumes (
                    source_id, content_hash, parser_version, cv_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    parser_version = excluded.parser_version,
                    cv_json = excluded.cv_json,
                    updated_at = excluded.updated_at
                """,
                (source_id, content_hash, parser_version, cv_json, now, now),
            )
        return self.get_parsed_original_resume(source_id)

    def save_tailored_resume(
        self,
        source_id: str,
        job_fingerprint: str,
        company_name: str,
        job_title: str,
        tailored_cv_json: str,
        audit_report_json: str,
    ):
        now = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO tailored_resumes (
                    id, source_id, job_fingerprint, company_name, job_title,
                    tailored_cv_json, audit_report_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    source_id,
                    job_fingerprint,
                    company_name,
                    job_title,
                    tailored_cv_json,
                    audit_report_json,
                    now,
                    now,
                ),
            )
        return self.get_tailored_resume(job_fingerprint)

    def get_tailored_resume(self, job_fingerprint: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tailored_resumes WHERE job_fingerprint = ?",
                (job_fingerprint,),
            ).fetchone()
        return memory_models.TailoredResumeRecord(**dict(row)) if row else None

    def _row_to_source(self, row: sqlite3.Row):
        return memory_models.ResumeSourceRecord(**dict(row))
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `make test`
Expected: PASS for `tests/memory/test_sqlite_repository.py`.

- [ ] **Step 5: Commit**

```bash
git add memory/sqlite_repository.py tests/memory/test_sqlite_repository.py
git commit -m "feat(adapter): add sqlite resume memory repository"
```

### Task 4: Implement the parser adapter and memory service

**Files:**
- Create: `memory/parser.py`
- Create: `memory/service.py`
- Test: `tests/memory/test_service.py`

- [ ] **Step 1: Write the failing memory service tests**

```python
import json

import pytest

from memory import models as memory_models
from memory.service import ResumeMemoryService


class FakeRepository:
    def __init__(self) -> None:
        self.active_source = None
        self.latest_source = None
        self.parsed = {}
        self.tailored_calls = []

    def get_active_original_source(self):
        return self.active_source

    def get_latest_original_source(self):
        return self.latest_source

    def get_source_by_path(self, path: str):
        return self.active_source if self.active_source and self.active_source.path == path else None

    def upsert_original_source(self, path: str, content_hash: str, is_active: bool):
        self.active_source = memory_models.ResumeSourceRecord(
            id="resume-1",
            path=path,
            content_hash=content_hash,
            is_active=is_active,
            created_at="2026-04-21T20:00:00+00:00",
            updated_at="2026-04-21T20:00:00+00:00",
            last_seen_at="2026-04-21T20:00:00+00:00",
        )
        self.latest_source = self.active_source
        return self.active_source

    def get_parsed_original_resume(self, source_id: str):
        return self.parsed.get(source_id)

    def save_parsed_original_resume(self, source_id: str, content_hash: str, parser_version: str, cv_json: str):
        record = memory_models.ParsedOriginalResumeRecord(
            source_id=source_id,
            content_hash=content_hash,
            parser_version=parser_version,
            cv_json=cv_json,
            created_at="2026-04-21T20:00:00+00:00",
            updated_at="2026-04-21T20:00:00+00:00",
        )
        self.parsed[source_id] = record
        return record

    def set_active_original_source(self, source_id: str) -> None:
        return None

    def save_tailored_resume(self, **kwargs):
        self.tailored_calls.append(kwargs)
        return kwargs

    def get_tailored_resume(self, job_fingerprint: str):
        return None


class FakeParser:
    parser_version = "cv-v1"

    def __init__(self, cv):
        self.cv = cv
        self.calls = []

    async def parse(self, resume_text: str):
        self.calls.append(resume_text)
        return self.cv


@pytest.mark.asyncio
async def test_resolve_original_resume_uses_explicit_path(tmp_path, sample_cv) -> None:
    resume_path = tmp_path / "resume.md"
    resume_path.write_text("# Jane Doe", encoding="utf-8")
    repository = FakeRepository()
    parser = FakeParser(sample_cv)
    service = ResumeMemoryService(repository, parser)

    resolved = await service.resolve_original_resume(str(resume_path))

    assert resolved.source.path == str(resume_path)
    assert resolved.cv.full_name == sample_cv.full_name
    assert parser.calls == ["# Jane Doe"]


@pytest.mark.asyncio
async def test_resolve_original_resume_falls_back_to_latest_when_path_missing(tmp_path, sample_cv) -> None:
    resume_path = tmp_path / "resume.md"
    resume_path.write_text("# Jane Doe", encoding="utf-8")
    repository = FakeRepository()
    repository.latest_source = repository.upsert_original_source(str(resume_path), "hash-a", True)
    parser = FakeParser(sample_cv)
    service = ResumeMemoryService(repository, parser)

    resolved = await service.resolve_original_resume(None)

    assert resolved.source.path == str(resume_path)


@pytest.mark.asyncio
async def test_resolve_original_resume_raises_when_no_original_exists(sample_cv) -> None:
    repository = FakeRepository()
    parser = FakeParser(sample_cv)
    service = ResumeMemoryService(repository, parser)

    with pytest.raises(memory_models.MissingOriginalResumeError):
        await service.resolve_original_resume(None)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `make test`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory.service'`.

- [ ] **Step 3: Implement the parser adapter and service**

```python
"""Resume parser adapter for the memory service."""

from models.agents.output import CV
from workflows.agents import resume_parser_agent


class ResumeParser:
    parser_version = "cv-v1"

    async def parse(self, resume_text: str) -> CV:
        result = await resume_parser_agent.run(
            f"Parse this resume into structured format:\n\n{resume_text}"
        )
        if result.output is None:
            raise ValueError("Resume parsing returned None")
        return result.output
```

```python
"""Service for resolving original resumes and persisting tailored outputs."""

import hashlib
import json
from pathlib import Path

from memory import models as memory_models
from models.agents.output import CV
from models.workflow import ResumeTailorResult


class ResumeMemoryService:
    def __init__(self, repository, parser) -> None:
        self._repository = repository
        self._parser = parser

    async def resolve_original_resume(
        self,
        optional_path: str | None,
    ) -> memory_models.ResolvedOriginalResume:
        source = self._resolve_source(optional_path)
        resume_path = Path(source.path)
        if not resume_path.exists():
            raise FileNotFoundError(f"Stored resume path does not exist: {resume_path}")

        resume_text = resume_path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(resume_text.encode("utf-8")).hexdigest()
        source = self._repository.upsert_original_source(str(resume_path), content_hash, True)
        parsed = self._repository.get_parsed_original_resume(source.id)

        if parsed and parsed.content_hash == content_hash and parsed.parser_version == self._parser.parser_version:
            cv = CV.model_validate_json(parsed.cv_json)
            return memory_models.ResolvedOriginalResume(source=source, cv=cv)

        cv = await self._parser.parse(resume_text)
        self._repository.save_parsed_original_resume(
            source_id=source.id,
            content_hash=content_hash,
            parser_version=self._parser.parser_version,
            cv_json=cv.model_dump_json(),
        )
        return memory_models.ResolvedOriginalResume(source=source, cv=cv)

    def _resolve_source(self, optional_path: str | None) -> memory_models.ResumeSourceRecord:
        if optional_path:
            existing = self._repository.get_source_by_path(optional_path)
            if existing:
                return existing
            return memory_models.ResumeSourceRecord(
                id="pending",
                path=optional_path,
                content_hash="",
                is_active=True,
                created_at="2026-04-21T20:00:00+00:00",
                updated_at="2026-04-21T20:00:00+00:00",
                last_seen_at="2026-04-21T20:00:00+00:00",
            )

        active = self._repository.get_active_original_source()
        if active:
            return active

        latest = self._repository.get_latest_original_source()
        if latest:
            return latest

        raise memory_models.MissingOriginalResumeError(
            "No stored original resume found. Provide --resume-path on the first run."
        )

    def store_tailored_resume(
        self,
        source_id: str,
        job_fingerprint: str,
        result: ResumeTailorResult,
    ) -> None:
        self._repository.save_tailored_resume(
            source_id=source_id,
            job_fingerprint=job_fingerprint,
            company_name=result.company_name,
            job_title=result.job_title,
            tailored_cv_json=result.tailored_resume,
            audit_report_json=json.dumps(result.audit_report),
        )
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `make test`
Expected: PASS for `tests/memory/test_service.py`.

- [ ] **Step 5: Commit**

```bash
git add memory/parser.py memory/service.py tests/memory/test_service.py
git commit -m "feat(service): add resume memory resolution service"
```

### Task 5: Refactor the workflow to consume structured original CV input

**Files:**
- Modify: `workflows/__init__.py`
- Modify: `models/workflow.py`
- Test: `tests/workflows/test_resume_tailor_workflow.py`

- [ ] **Step 1: Write the failing workflow contract test**

```python
import pytest

from models.agents.output import CV, JobAnalysis, ReviewResult, AuditResult
from workflows import ResumeTailorWorkflow


class DummyRunResult:
    def __init__(self, output):
        self.output = output


@pytest.mark.asyncio
async def test_workflow_uses_provided_original_cv_without_reparsing(monkeypatch, sample_cv) -> None:
    async def fail_parser(*args, **kwargs):
        raise AssertionError("resume_parser_agent should not be called")

    async def run_analyst(*args, **kwargs):
        return DummyRunResult(
            JobAnalysis(
                job_title="Platform Engineer",
                company_name="Acme",
                summary="Platform role",
                hard_skills=["Python"],
                soft_skills=["Communication"],
                key_responsibilities=["Build systems"],
                keywords_to_target=["Python", "Platform"],
            )
        )

    async def run_writer(*args, **kwargs):
        return DummyRunResult(sample_cv)

    async def run_reviewer(*args, **kwargs):
        return DummyRunResult(
            ReviewResult(
                quality_score=9,
                needs_improvement=False,
                specific_suggestions=[],
                strengths=["Good targeting"],
            )
        )

    async def run_auditor(*args, **kwargs):
        return DummyRunResult(
            AuditResult(
                passed=True,
                hallucination_score=0,
                ai_cliche_score=0,
                issues=[],
                feedback_summary="Looks good",
            )
        )

    monkeypatch.setattr("workflows.resume_parser_agent.run", fail_parser)
    monkeypatch.setattr("workflows.analyst_agent.run", run_analyst)
    monkeypatch.setattr("workflows.writer_agent.run", run_writer)
    monkeypatch.setattr("workflows.reviewer_agent.run", run_reviewer)
    monkeypatch.setattr("workflows.auditor_agent.run", run_auditor)

    result = await ResumeTailorWorkflow().run(sample_cv, "files/job_posting.md")

    assert result.job_title == "Platform Engineer"
    assert result.company_name == "Acme"
    assert result.passed is True
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `make test`
Expected: FAIL because `ResumeTailorWorkflow.run()` still expects raw resume text and `ResumeTailorResult` has no `job_title`.

- [ ] **Step 3: Refactor the workflow and result model**

```python
from pydantic import BaseModel


class ResumeTailorResult(BaseModel):
    company_name: str
    job_title: str
    tailored_resume: str
    audit_report: dict
    passed: bool
```

```python
from models.agents.output import JobAnalysis, CV
from models.workflow import ResumeTailorResult


class ResumeTailorWorkflow:
    async def run(
        self,
        original_cv: CV,
        job_content_file_path: str,
    ) -> ResumeTailorResult:
        print("🚀 STARTING MULTI-AGENT PIPELINE\n")
        print(f"   ✅ Resume Loaded From Memory: {original_cv.full_name}")
        print(
            f"   📋 Found {len(original_cv.skills)} skills, {len(original_cv.experience)} work experiences\n"
        )

        original_cv_json = original_cv.model_dump_json()
```

```python
return ResumeTailorResult(
    company_name=job_analysis_result.output.company_name,
    job_title=job_analysis_result.output.job_title,
    tailored_resume=new_cv.model_dump_json() if new_cv else "",
    audit_report={
        "passed": getattr(audit, "passed", None),
        "hallucination_score": getattr(audit, "hallucination_score", None),
        "ai_cliche_score": getattr(audit, "ai_cliche_score", None),
        "feedback_summary": getattr(audit, "feedback_summary", ""),
        "issues": [
            {
                "severity": getattr(i, "severity", "Unknown"),
                "issue": getattr(i, "issue", str(i)),
                "suggestion": getattr(i, "suggestion", ""),
            }
            for i in getattr(audit, "issues", []) or []
        ],
    },
    passed=True,
)
```

- [ ] **Step 4: Run the targeted test to verify it passes**

Run: `make test`
Expected: PASS for `tests/workflows/test_resume_tailor_workflow.py`.

- [ ] **Step 5: Commit**

```bash
git add workflows/__init__.py models/workflow.py tests/workflows/test_resume_tailor_workflow.py
git commit -m "refactor(workflow): use structured original resume input"
```

### Task 6: Wire the CLI to the memory service and store tailored outputs

**Files:**
- Modify: `main.py`
- Modify: `utils/validate_inputs.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing CLI behavior tests**

```python
import pytest

from memory import models as memory_models
from models.workflow import ResumeTailorResult
import main as app_main


class FakeWorkflow:
    async def run(self, original_cv, job_content_file_path):
        return ResumeTailorResult(
            company_name="Acme",
            job_title="Platform Engineer",
            tailored_resume=original_cv.model_dump_json(),
            audit_report={"passed": True, "feedback_summary": "Looks good"},
            passed=True,
        )


@pytest.mark.asyncio
async def test_main_uses_latest_original_resume_when_resume_path_missing(
    monkeypatch,
    sample_cv,
    tmp_path,
    capsys,
) -> None:
    job_path = tmp_path / "job_posting.md"
    job_path.write_text("Platform Engineer at Acme", encoding="utf-8")

    class FakeService:
        async def resolve_original_resume(self, optional_path):
            assert optional_path is None
            return memory_models.ResolvedOriginalResume(
                source=memory_models.ResumeSourceRecord(
                    id="resume-1",
                    path=str(tmp_path / "resume.md"),
                    content_hash="hash-a",
                    is_active=True,
                    created_at="2026-04-21T20:00:00+00:00",
                    updated_at="2026-04-21T20:00:00+00:00",
                    last_seen_at="2026-04-21T20:00:00+00:00",
                ),
                cv=sample_cv,
            )

        def store_tailored_resume(self, source_id, job_fingerprint, result):
            assert source_id == "resume-1"
            assert result.company_name == "Acme"

    monkeypatch.setattr(app_main, "build_memory_service", lambda db_path: FakeService())
    monkeypatch.setattr(app_main, "ResumeTailorWorkflow", lambda: FakeWorkflow())

    exit_code = await app_main.run_cli(None, str(job_path), str(tmp_path / "resume_memory.sqlite3"))

    assert exit_code == 0


@pytest.mark.asyncio
async def test_main_warns_when_no_original_resume_exists(monkeypatch, tmp_path, capsys) -> None:
    job_path = tmp_path / "job_posting.md"
    job_path.write_text("Platform Engineer at Acme", encoding="utf-8")

    class FakeService:
        async def resolve_original_resume(self, optional_path):
            raise memory_models.MissingOriginalResumeError(
                "No stored original resume found. Provide --resume-path on the first run."
            )

    monkeypatch.setattr(app_main, "build_memory_service", lambda db_path: FakeService())

    exit_code = await app_main.run_cli(None, str(job_path), str(tmp_path / "resume_memory.sqlite3"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Provide --resume-path on the first run." in captured.out
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `make test`
Expected: FAIL because `run_cli()` and `build_memory_service()` do not exist.

- [ ] **Step 3: Implement CLI argument parsing, validation, memory resolution, and tailored-resume persistence**

```python
import argparse
import asyncio
import hashlib
import os

from memory.parser import ResumeParser
from memory.service import ResumeMemoryService
from memory.sqlite_repository import SQLiteResumeMemoryRepository
from utils.markdown_writer import generate_resume
from workflows import ResumeTailorWorkflow
```

```python
def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tailor a resume against a job posting.")
    files_path = os.path.join(os.getcwd(), "files")
    parser.add_argument("--resume-path", dest="resume_path", default=None)
    parser.add_argument(
        "--job-posting-path",
        dest="job_posting_path",
        default=os.path.join(files_path, "job_posting.md"),
    )
    parser.add_argument(
        "--memory-db-path",
        dest="memory_db_path",
        default=os.path.join(files_path, "resume_memory.sqlite3"),
    )
    return parser


def build_memory_service(db_path: str) -> ResumeMemoryService:
    repository = SQLiteResumeMemoryRepository(db_path)
    parser = ResumeParser()
    return ResumeMemoryService(repository, parser)


def build_job_fingerprint(job_posting_path: str) -> str:
    with open(job_posting_path, "r", encoding="utf-8") as file_handle:
        return hashlib.sha256(file_handle.read().encode("utf-8")).hexdigest()
```

```python
from utils.validate_inputs import validate_file


def validate_job_posting_file(job_posting_path: str) -> bool:
    job_defaults = [
        "PASTE JOB POSTING HERE",
        "<!-- REPLACE WITH JOB POSTING -->",
        "[Job Title]",
        "[Company Name]",
    ]
    return validate_file(job_posting_path, "Job posting file", job_defaults)
```

```python
async def run_cli(
    resume_path: str | None,
    job_posting_path: str,
    memory_db_path: str,
) -> int:
    if not validate_job_posting_file(job_posting_path):
        return 1

    memory_service = build_memory_service(memory_db_path)
    try:
        resolved_original = await memory_service.resolve_original_resume(resume_path)
    except Exception as error:
        print(f"❌ {error}")
        return 1

    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        resolved_original.cv,
        job_content_file_path=job_posting_path,
    )

    if result.passed:
        job_fingerprint = build_job_fingerprint(job_posting_path)
        memory_service.store_tailored_resume(
            source_id=resolved_original.source.id,
            job_fingerprint=job_fingerprint,
            result=result,
        )
        generate_resume(result)
        return 0

    print("\n❌ Audit Failed. Please review the feedback and try again.")
    print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")
    return 1
```

```python
def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            run_cli(
                resume_path=args.resume_path,
                job_posting_path=args.job_posting_path,
                memory_db_path=args.memory_db_path,
            )
        )
    )
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `make test`
Expected: PASS for `tests/test_main.py`.

- [ ] **Step 5: Commit**

```bash
git add main.py utils/validate_inputs.py tests/test_main.py
git commit -m "feat(api): wire cli to resume memory service"
```

### Task 7: Document the new memory-driven CLI flow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the usage section and behavior notes**

```markdown
## 🏃 Usage

1.  **Prepare the job posting**:
    Update `files/job_posting.md` with the target job description.

2.  **Choose how to provide the original resume**:
    - First run: pass the original resume explicitly.
      ```bash
      uv run python main.py --resume-path /absolute/path/to/resume.md
      ```
    - Later runs: omit `--resume-path` to reuse the latest stored original resume.
      ```bash
      make run
      ```

3.  **How memory works**:
    - The app stores the original resume and reuses its parsed `CV` when the file content has not changed.
    - If the original resume file changes, the app reparses it automatically.
    - Every job submission starts from the original resume, not from any previously tailored output.
    - Tailored resumes are stored per job submission.
```

- [ ] **Step 2: Update the Make commands table**

```markdown
| Command            | Description                                                             |
|--------------------|-------------------------------------------------------------------------|
| `make help`        | Show available commands and descriptions.                               |
| `make install`     | Install production dependencies using `uv`.                             |
| `make install/dev` | Install development dependencies using `uv`.                            |
| `make test`        | Run the automated test suite.                                           |
| `make run`         | Run the workflow using the latest stored original resume when available. |
| `make install/uv`  | Ensure `uv` is installed (automatically run by other commands).         |
```

- [ ] **Step 3: Run the full test suite after the documentation update**

Run: `make test`
Expected: PASS for the full suite.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe resume memory cli workflow"
```

## Self-Review

- **Spec coverage:** Task 2 defines the original/tailored memory models and repository contract. Task 3 implements the SQLite backend. Task 4 covers original-resume resolution, auto-reparse, latest-original fallback, and tailored-resume persistence. Task 5 enforces the “always start from the original resume” workflow boundary. Task 6 wires the CLI to require an explicit first-run resume, reuse the latest original when omitted, and persist tailored outputs. Task 7 updates usage docs.
- **Placeholder scan:** No `TODO`, `TBD`, or “similar to” shortcuts remain. Each file path, command, and code step is explicit.
- **Type consistency:** The plan consistently uses `ResumeSourceRecord`, `ParsedOriginalResumeRecord`, `TailoredResumeRecord`, `ResolvedOriginalResume`, `ResumeMemoryService`, and `ResumeTailorResult(job_title=...)`.
