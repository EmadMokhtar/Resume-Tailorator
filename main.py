import asyncio
import os

from workflows import ResumeTailorWorkflow


async def main():
    # --- Inputs ---
    # TODO: Pass the job file content path as CLI argument.
    files_path = os.path.join(os.getcwd(), "files")
    job_content_file_path = os.path.join(files_path, "job_posting.md")
    resume_file_path = os.path.join(files_path, "resume.md")
    original_cv_text: str = ""

    # Reading the original CV from the file
    # ASSUME: This is markdown file.
    # TODO: Pass the file as a CLI argument.
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
    result = await workflow.run(
        original_cv_text, job_content_file_path=job_content_file_path
    )

    # If passed, save the file
    if result.passed:
        print("\n✅ Audit Passed. Saving CV...")
        output_path = os.path.join(
            files_path, f"tailored_resume_{result.company_name}.md"
        )

        # Parse the CV JSON back to CV object
        import json

        cv_data = json.loads(result.tailored_resume)

        with open(output_path, "w", encoding="utf-8") as f:
            # Simple Markdown serialization
            f.write(f"# {cv_data.get('full_name', 'N/A')}\n")

            # Contact info
            if cv_data.get("contact_info"):
                f.write(f"{cv_data.get('contact_info')}\n")
            f.write("\n")

            # Summary
            f.write(f"## Professional Summary\n{cv_data.get('summary', '')}\n\n")

            # Skills
            f.write("## Skills\n")
            for skill in cv_data.get("skills", []):
                f.write(f"- {skill}\n")

            # Projects
            if cv_data.get("projects"):
                f.write("\n## Projects\n")
                for project in cv_data.get("projects", []):
                    f.write(f"{project}\n\n")

            # Experience
            f.write("\n## Work Experience\n")
            for exp in cv_data.get("experience", []):
                f.write(
                    f"### {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('dates', '')})\n"
                )
                for hl in exp.get("highlights", []):
                    f.write(f"- {hl}\n")
                f.write("\n")

            # Education
            f.write("## Education\n")
            for edu in cv_data.get("education", []):
                f.write(f"- {edu}\n")

            # Certifications
            if cv_data.get("certifications"):
                f.write("\n## Certifications\n")
                for cert in cv_data.get("certifications", []):
                    f.write(f"- {cert}\n")

            # Publications
            if cv_data.get("publications"):
                f.write("\n## Publications\n")
                for pub in cv_data.get("publications", []):
                    f.write(f"- {pub}\n")

        print(f"✅ Tailored CV saved to: {output_path}")
    else:
        print("\n❌ Audit Failed. Please review the feedback and try again.")
        print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")


if __name__ == "__main__":
    asyncio.run(main())
