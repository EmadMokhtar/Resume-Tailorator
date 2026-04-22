from pydantic import BaseModel


class ResumeTailorResult(BaseModel):
    company_name: str
    job_title: str
    tailored_resume: str
    audit_report: dict
    passed: bool
