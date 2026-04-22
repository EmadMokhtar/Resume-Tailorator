from pydantic import BaseModel

from models.agents.output import AuditResult, CV, FinalReport, JobAnalysis, ReviewResult


class ResumeTailorResult(BaseModel):
    company_name: str
    tailored_resume: str
    audit_report: dict
    passed: bool
    final_report: FinalReport | None = None
