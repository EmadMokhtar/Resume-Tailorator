import asyncio
import os

from utils.markdown_writer import generate_resume
from workflows import ResumeTailorWorkflow


async def main():
    # --- Inputs ---
    files_path = os.path.join(os.getcwd(), "files")
    job_content_file_path = os.path.join(files_path, "job_posting.md")
    resume_file_path = os.path.join(files_path, "resume.md")
    original_cv_text: str = ""

    # Reading the original CV from the file
    # ASSUME: This is markdown file.
    try:
        with open(resume_file_path, "r", encoding="utf-8") as f:
            original_cv_text = f.read()
    except FileNotFoundError:
        print(
            f"⚠️ Resume file not found at {resume_file_path}. Continuing with empty resume."
        )
        original_cv_text = ""
    except Exception as e:
        print(f"⚠️ Error reading resume file: {e}")
        original_cv_text = ""

    # Run the workflow
    workflow = ResumeTailorWorkflow()
    # Task 6 will replace the legacy text-based flow below with:
    # 1. ResumeMemoryService.resolve_original_resume(...)
    # 2. workflow.run(resolved_original.cv, ...)
    # Until then, fail fast with an actionable message rather than silently
    # passing a raw string into workflow.run().
    raise NotImplementedError(
        "Task 6 not yet implemented: the memory service must parse 'original_cv_text' "
        "into a CV object before calling workflow.run().  Wire up Task 6 first."
    )
    result = await workflow.run(
        original_cv_text, job_content_file_path=job_content_file_path
    )

    # If passed, save the file
    if result.passed:
        print("\n✅ Audit Passed. Saving CV...")
        generate_resume(result)

    else:
        print("\n❌ Audit Failed. Please review the feedback and try again.")
        print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")


if __name__ == "__main__":
    asyncio.run(main())
