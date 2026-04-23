import argparse
import asyncio
import sys
from pathlib import Path

from utils.markdown_writer import generate_resume
from utils.resume_converter import (
    ConversionFailedError,
    EmptyConversionResultError,
    InputConverterRegistry,
    OutputConversionFailedError,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
)
from utils.resume_output_converter import (
    OutputConverterRegistry,
    build_resume_markdown,
)
from workflows import ResumeTailorWorkflow


def create_parser() -> argparse.ArgumentParser:
    """Create and return the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Tailor your resume to a job posting")
    parser.add_argument(
        "--resume",
        type=str,
        default="files/resume.md",
        help="Path to input resume file (DOCX, PDF, or Markdown). "
        "Defaults to files/resume.md",
    )
    parser.add_argument(
        "--output",
        type=str,
        action="append",
        default=None,
        help="Output format(s): md, pdf, or docx (repeatable, case-insensitive). "
        "Defaults to md",
    )
    return parser


async def main_impl(resume_path: str, output_formats: list[str]) -> None:
    """Implementation of main logic.

    Args:
        resume_path: Path to the input resume file.
        output_formats: List of output formats (e.g., ['md', 'pdf', 'docx']).

    Raises:
        SystemExit: On conversion errors or audit failure (with exit code).
    """
    # --- Inputs ---
    files_path = Path.cwd() / "files"
    job_content_file_path = files_path / "job_posting.md"
    original_cv_text: str = ""

    # --- Input Resume Processing ---
    try:
        # Resolve resume path
        resume_path_obj = Path(resume_path)
        if not resume_path_obj.is_absolute():
            resume_file_path = Path.cwd() / resume_path_obj
        else:
            resume_file_path = resume_path_obj

        # Handle different file types
        if resume_file_path.suffix.lower() == ".md":
            # Read Markdown file directly
            if not resume_file_path.exists():
                raise ResumeFileNotFoundError(
                    f"Resume file not found at {resume_file_path}"
                )
            with open(resume_file_path, "r", encoding="utf-8") as f:
                original_cv_text = f.read()
        elif resume_file_path.suffix.lower() in [".docx", ".pdf"]:
            # Convert DOCX/PDF to Markdown using InputConverterRegistry
            if not resume_file_path.exists():
                raise ResumeFileNotFoundError(
                    f"Resume file not found at {resume_file_path}"
                )
            registry = InputConverterRegistry()
            converter = registry.get(resume_file_path.suffix)
            original_cv_text = converter.convert(resume_file_path)
        else:
            raise UnsupportedFormatError(
                f"Unsupported file format: {resume_file_path.suffix}. "
                "Supported: .docx, .pdf, .md"
            )
    except (
        UnsupportedFormatError,
        ConversionFailedError,
        EmptyConversionResultError,
        ResumeFileNotFoundError,
    ) as e:
        print(f"❌ Error processing resume: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error reading resume: {e}")
        sys.exit(1)

    # --- Run Workflow ---
    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        original_cv_text, job_content_file_path=str(job_content_file_path)
    )

    # --- Output Processing ---
    if result.passed:
        print("\n✅ Audit Passed. Saving CV...")

        # For backward compatibility, keep existing generate_resume call
        generate_resume(result)

        # Build Markdown from result
        try:
            markdown_content = build_resume_markdown(result)
        except OutputConversionFailedError as e:
            print(f"❌ Error building resume markdown: {e}")
            sys.exit(1)

        # Convert to requested output formats
        try:
            # Normalize formats to lowercase
            normalized_formats = [fmt.lower() for fmt in output_formats]
            registry = OutputConverterRegistry()
            written_paths = registry.convert_all(
                markdown_content, normalized_formats, files_path
            )
            # Print success message with formats
            file_names = ", ".join(p.name for p in written_paths)
            print(f"✅ Tailored resume saved as: {file_names}")
        except OutputConversionFailedError as e:
            print(f"❌ Error converting resume to output formats: {e}")
            sys.exit(1)
    else:
        print("\n❌ Audit Failed. Please review the feedback and try again.")
        print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")


async def main() -> None:
    """Parse CLI arguments and run main implementation."""
    parser = create_parser()
    args = parser.parse_args()

    # Set default output formats if not provided
    output_formats = args.output if args.output else ["md"]

    await main_impl(resume_path=args.resume, output_formats=output_formats)


if __name__ == "__main__":
    asyncio.run(main())
