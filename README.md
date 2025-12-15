#  📄 Resume Tailorator

Resume Tailorator is a sophisticated multi-agent AI system designed to analyze job postings and tailor your resume to match specific job requirements. It ensures authenticity, avoids AI clichés, and optimizes for Applicant Tracking Systems (ATS).

## 🚀 Features

- **Multi-Agent Architecture**: Uses specialized agents for analyzing, writing, and auditing.
- **Automated Job Analysis**: Extracts key requirements and skills from job postings.
- **Authentic Tailoring**: Rephrases your experience to match the job without inventing skills.
- **Hallucination & Cliché Detection**: Built-in auditor to ensure quality and "human" tone.
- **Dual Output**: Generates both Markdown (`.md`) and PDF (`.pdf`) versions of the tailored resume.
- **Input Validation**: Ensures your input files are correctly formatted before processing.
- **Self-Correcting Workflow**: The writer agent iterates based on feedback from the auditor.

## 🛠️ Architecture

The system employs a sequential pipeline of AI agents:

1.  **Analyst Agent**: Extracts structured job requirements.
2.  **Resume Parser Agent**: Parses your Markdown resume into structured data.
3.  **Writer Agent**: Tailors the CV to match job requirements.
4.  **Auditor Agent**: Validates for hallucinations and AI clichés.
5.  **Reviewer Agent**: Provides quality feedback.

## 📋 Prerequisites

- **Python 3.13+**
- **[uv](https://github.com/astral-sh/uv)** (Fast Python package installer and resolver)
- **OpenAI API Key** (or compatible LLM provider configured in environment)

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/EmadMokhtar/resume_tailorator
    cd resume_tailorator
    ```

2.  **Install dependencies**:
    This project uses `uv` for dependency management.
    ```bash
    uv sync
    ```

3.  **Set up Environment Variables**:
    Export your OpenAI API key (or other provider keys):
    ```bash
    export OPENAI_API_KEY=your_api_key_here
    ```

## 🏃 Usage

1.  **Prepare Input Files**:
    Navigate to the `files/` directory and update the following files:
    *   `resume.md`: Paste your current resume in Markdown format.
    *   `job_posting.md`: Paste the job description you want to apply for.

    *Note: Do not leave the default placeholder text in these files.*

2.  **Run the Application**:
    Use the Makefile command to validate inputs and run the workflow:
    ```bash
    make run
    ```

3.  **View Results**:
    Upon successful completion, the tailored resume will be saved in the `files/` directory:
    *   `tailored_resume_<Company_Name>.md`
    *   `tailored_resume_<Company_Name>.pdf`

## 🛠️ Make Commands

This project uses a `Makefile` to simplify common tasks. Here are the available commands:

| Command            | Description                                                     |
|--------------------|-----------------------------------------------------------------|
| `make help`        | Show available commands and descriptions.                       |
| `make install`     | Install production dependencies using `uv`.                     |
| `make install/dev` | Install development dependencies using `uv`.                    |
| `make run`         | Validate inputs and run the resume tailorator workflow.         |
| `make install/uv`  | Ensure `uv` is installed (automatically run by other commands). |

## 📂 Project Structure

```
resume_tailorator/
├── files/                  # Input and output files
│   ├── resume.md           # Your source resume
│   └── job_posting.md      # Target job description
├── models/                 # Pydantic data models
├── tools/                  # Helper tools (Playwright, etc.)
├── utils/                  # Utilities (PDF generation, validation)
├── workflows/              # Agent definitions and workflow logic
├── main.py                 # Entry point
├── Makefile                # Command shortcuts
└── pyproject.toml          # Project configuration
```

## 🛡️ Safety & Quality

- **Anti-Hallucination**: The system is strictly instructed never to invent skills or experiences.
- **Cliché Filter**: Avoids terms like "spearheaded", "synergy", and "game-changer".
- **Validation**: The `make run` command checks that your input files are not empty or containing default placeholders before starting the expensive AI process.

## 🤝 Contributing

Contributions are welcome! Please ensure you follow the coding guidelines and add tests for new features.
