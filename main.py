import argparse
import asyncio
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from memory.models import MissingOriginalResumeError, ResumeMemoryError
from memory.parser import PydanticAIResumeParser
from memory.service import ResumeMemoryService
from memory.sqlite_repository import SQLiteResumeMemoryRepository
from models.agents.output import AuditResult, CV
from utils.markdown_writer import generate_resume
from workflows import ResumeTailorWorkflow


def _job_fingerprint(job_content_file_path: str) -> str:
    """Return a short deterministic fingerprint derived from job-posting content.

    The fingerprint is the first 16 hex characters of the SHA-256 hash of the
    file content.  If the file cannot be read we fall back to hashing the path
    itself so the fingerprint remains deterministic even when the file is
    absent (e.g. in tests that mock the workflow).
    """
    try:
        content = Path(job_content_file_path).read_text(encoding="utf-8")
    except OSError:
        content = job_content_file_path
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def main(argv: list[str] | None = None) -> None:
    """Entry point for the Resume Tailorator CLI."""
    # --- Argument parsing ---
    arg_parser = argparse.ArgumentParser(
        description="Tailor your resume to a job posting using AI agents."
    )
    arg_parser.add_argument(
        "--resume-path",
        default=None,
        metavar="PATH",
        help=(
            "Path to your original resume (Markdown). "
            "Required on the very first run; omit to reuse the latest stored resume."
        ),
    )
    args = arg_parser.parse_args(argv)

    # --- Paths ---
    files_path = os.path.join(os.getcwd(), "files")
    job_content_file_path = os.path.join(files_path, "job_posting.md")
    db_path = os.path.join(files_path, "resume_memory.sqlite3")

    # --- Memory service setup ---
    repo = SQLiteResumeMemoryRepository(db_path=db_path)
    try:
        parser_adapter = PydanticAIResumeParser()
        memory_service = ResumeMemoryService(repository=repo, parser=parser_adapter)

        # --- Resolve original resume ---
        try:
            resolved = memory_service.resolve_original_resume(path=args.resume_path)
        except MissingOriginalResumeError as exc:
            print(f"⚠️ {exc}")
            print(
                "💡 Tip: provide your resume on the first run with "
                "--resume-path /path/to/resume.md"
            )
            sys.exit(1)
        except FileNotFoundError as exc:
            print(f"⚠️ Resume file not found: {exc}")
            sys.exit(1)
        except (ResumeMemoryError, ValidationError, sqlite3.Error) as exc:
            print(f"⚠️ Failed to resolve original resume: {exc}")
            sys.exit(1)

        # --- Run the tailoring workflow ---
        workflow = ResumeTailorWorkflow()
        result = await workflow.run(
            resolved.cv, job_content_file_path=job_content_file_path
        )

        # --- Persist and report results ---
        if result.passed:
            fingerprint = _job_fingerprint(job_content_file_path)

            try:
                tailored_cv = CV.model_validate_json(result.tailored_resume)
                audit = AuditResult.model_validate(result.audit_report)
                memory_service.save_tailored_resume(
                    source_id=resolved.source.id,
                    job_fingerprint=fingerprint,
                    company_name=result.company_name,
                    job_title=result.job_title,
                    tailored_cv=tailored_cv,
                    audit_result=audit,
                )
            except (ResumeMemoryError, ValidationError, sqlite3.Error) as exc:
                print(f"\n⚠️ Failed to save tailored resume: {exc}")
                sys.exit(1)

            print("\n✅ Audit Passed. Saving CV...")
            generate_resume(result)
        else:
            print("\n❌ Audit Failed. Please review the feedback and try again.")
            print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")
    finally:
        repo.close()


if __name__ == "__main__":
    asyncio.run(main())
