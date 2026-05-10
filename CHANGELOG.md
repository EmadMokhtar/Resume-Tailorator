## Unreleased

### Feat

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

- resolve 58 test failures across 4 root causes
- deterministic resume parsing + improved DOCX heading conversion (#18)
- **cli**: correct return tuple structure to match spec
- replace hardcoded job URL with placeholder for improved flexibility
