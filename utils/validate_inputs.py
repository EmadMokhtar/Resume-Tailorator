import argparse
import os
import sys


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

    if args.resume_path is not None:
        valid_resume = validate_file(args.resume_path, "Resume file", resume_defaults)
        if not (valid_resume and valid_job):
            sys.exit(1)
    else:
        if not valid_job:
            sys.exit(1)

    print("✅ Input files validated successfully.")


if __name__ == "__main__":
    main()
