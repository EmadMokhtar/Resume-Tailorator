import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)


def validate_file(filepath, file_description, default_values):
    if not os.path.exists(filepath):
        print(f"❌ Error: {file_description} not found at {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        print(f"❌ Error: {file_description} is empty.")
        return False

    for default in default_values:
        if default in content:
            print(f"❌ Error: {file_description} contains default value: '{default}'")
            print("Please update the file with your actual content.")
            return False

    return True


def validate_job_url(job_url: str) -> None:
    """Validate that a job URL has proper format.

    Args:
        job_url: The URL to validate.

    Raises:
        ValueError: If URL format is invalid.
    """
    if not job_url.startswith(("http://", "https://")):
        raise ValueError(f"Job URL must start with http:// or https://. Got: {job_url}")


def validate_inputs(args) -> tuple[str | None, str, str | None]:
    """Validate CLI inputs and job URL.

    Args:
        args: Parsed arguments from argparse.

    Returns:
        Tuple of (resume_path_or_none, output_formats_str, job_url_or_none)
    """
    # Extract resume path
    resume_path = args.resume_path

    # Extract output formats (default to "md")
    output_formats = ",".join(args.output) if args.output else "md"

    # Job URL handling: check CLI arg first, then environment variable
    job_url = args.job_url or os.getenv("JOB_URL")
    if job_url:
        try:
            validate_job_url(job_url)  # Raises ValueError if invalid
            source = "cli_arg" if args.job_url else "env_var"
            logger.info(f"job_url_provided from {source}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        logger.info("job_url_not_provided")

    # Return the required tuple
    return resume_path, output_formats, job_url


def main():
    parser = argparse.ArgumentParser(
        description="Validate input files for the Resume Tailorator."
    )
    parser.add_argument(
        "--resume-path",
        default=None,
        metavar="PATH",
        help=(
            "Path to your original resume (Markdown). "
            "When provided, the file is validated before the run. "
            "When omitted, resume validation is skipped (the memory service "
            "will resolve the latest stored resume at runtime)."
        ),
    )
    parser.add_argument(
        "--job-url",
        default=None,
        metavar="URL",
        help=(
            "URL of the job posting to scrape. "
            "When provided, the URL is fetched and converted to Markdown. "
            "Takes precedence over files/job_posting.md if both exist. "
            "Can also be set via JOB_URL environment variable."
        ),
    )
    parser.add_argument(
        "--output",
        action="append",
        choices=["md", "pdf", "docx"],
        metavar="FORMAT",
        help="Output format: md, pdf, or docx. Repeatable. Default: md.",
    )
    args = parser.parse_args()

    base_dir = os.getcwd()
    files_dir = os.path.join(base_dir, "files")
    job_posting_path = os.path.join(files_dir, "job_posting.md")

    # Define default values that should trigger an error
    resume_defaults = [
        "PASTE YOUR RESUME HERE",
        "<!-- REPLACE WITH YOUR RESUME -->",
        "[Your Name]",
        "[Your Contact Information]",
    ]

    job_defaults = [
        "PASTE JOB POSTING HERE",
        "<!-- REPLACE WITH JOB POSTING -->",
        "[Job Title]",
        "[Company Name]",
    ]

    # Only validate job posting file if URL not provided
    if args.job_url is None and os.getenv("JOB_URL") is None:
        valid_job = validate_file(job_posting_path, "Job posting file", job_defaults)
        if not valid_job:
            sys.exit(1)
    else:
        print("⏭️  Job URL provided; skipping job_posting.md validation")

    if args.resume_path is not None:
        valid_resume = validate_file(args.resume_path, "Resume file", resume_defaults)
        if not valid_resume:
            sys.exit(1)

    print("✅ Input validation successful.")


if __name__ == "__main__":
    main()
