## v0.2.2 (2026-05-16)

### Fix

- rewrite 18 skipped tests for Typer/_tailor_impl architecture (#27)

## v0.2.1 (2026-05-16)

### Fix

- preserve hyperlinks throughout resume tailoring pipeline (#25)

## v0.2.0 (2026-05-10)

### Feat

- release automation with commitizen and GitHub Actions (#21)
- add --verbose flag for agent streaming output (#17)
- job-specific output directories with configurable naming templates (#12)
- **cli**: rewrite CLI with Typer (tailor + re-tailor commands) (#9)
- Add job URL scraping feature with multi-strategy fallback (#6)
- comprehensive resume tailoring enhancements (format converters, self-review, quality gates) (#5)
- **memory**: wire resume memory into cli (#1)
- add cover image to README.md for enhanced visual appeal
- update README.md to enhance project description, features, and usage instructions
- enhance Makefile with installation and help commands for improved workflow
- add input validation for resume and job posting files
- update .gitignore to include resume and job posting markdown files
- add PDF generation for tailored resumes and update job posting handling
- enhance resume tailoring workflow with job content file input and quality review agent
- add comprehensive GitHub Copilot instructions for Resume Tailorator project
- implement resume tailoring workflow with multi-agent system for parsing, analysis, and auditing
- initialize project structure and add core functionality for AI-powered resume tailoring

### Fix

- add GH_TOKEN for gh CLI and include uv.lock in release commit
- replace cz changelog with awk extraction to avoid missing tag errors
- force-push release branch and update existing PR if one exists
- use PR-based release flow instead of direct push to main
- use version_provider uv so commitizen reads version from pyproject.toml (#23)
- release workflow and post-merge improvements (#22)
- deterministic resume parsing + improved DOCX heading conversion (#18)
- **cli**: correct return tuple structure to match spec
- replace hardcoded job URL with placeholder for improved flexibility
