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


def validate_job_url(job_url):
    """Validate job URL format.

    Args:
        job_url: The URL to validate.

    Returns:
        bool: True if URL is valid, False otherwise.

    Raises:
        ValueError: If URL is invalid.
    """
    if not job_url:
        return False

    if not job_url.startswith(("http://", "https://")):
        raise ValueError(f"Job URL must start with http:// or https://. Got: {job_url}")

    return True


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
        type=str,
        default=None,
        metavar="URL",
        help=(
            "URL of the job posting to scrape. "
            "Priority: CLI > JOB_URL env var > markdown file. "
            "Must start with http:// or https://."
        ),
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

    valid_job = validate_file(job_posting_path, "Job posting file", job_defaults)

    # Handle job URL (CLI > env var > None)
    job_url = args.job_url or os.getenv("JOB_URL")

    if job_url:
        try:
            validate_job_url(job_url)
            source = "cli_arg" if args.job_url else "env_var"
            logger.info(f"Job URL provided from {source}: {job_url}")
            print(f"✅ Job URL provided: {job_url}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        logger.info("Job URL not provided. Will use markdown job content from file.")
        print("ℹ️ Job URL not provided. Using markdown job posting file.")

    if args.resume_path is not None:
        valid_resume = validate_file(args.resume_path, "Resume file", resume_defaults)
        if not (valid_resume and valid_job):
            sys.exit(1)
    else:
        if not valid_job:
            sys.exit(1)

    print("✅ Input files validated successfully.")

    # Return tuple with job_url
    return job_posting_path, args.resume_path, job_url


if __name__ == "__main__":
    main()
