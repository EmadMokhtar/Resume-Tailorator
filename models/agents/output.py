from pydantic import BaseModel, Field


# --- Model for the Job Analysis ---
class JobAnalysis(BaseModel):
    job_title: str
    company_name: str
    summary: str = Field(
        description="A concise summary of what the role actually entails."
    )
    hard_skills: list[str] = Field(description="Technical skills explicitly required.")
    soft_skills: list[str] = Field(
        description="Cultural or behavioral traits required."
    )
    key_responsibilities: list[str] = Field(description="The top 3-5 main duties.")
    keywords_to_target: list[str] = Field(
        description="Specific ATS keywords found in the text."
    )


# --- Model for the CV ---
class WorkExperience(BaseModel):
    company: str
    role: str
    dates: str
    highlights: list[str] = Field(description="Bullet points of achievements.")


class CV(BaseModel):
    full_name: str
    contact_info: str = Field(default="", description="Email, phone, location, etc.")
    summary: str
    skills: list[str] = Field(description="All technical and soft skills")
    projects: list[str] = Field(
        default_factory=list, description="Project descriptions"
    )
    experience: list[WorkExperience]
    education: list[str]
    certifications: list[str] = Field(
        default_factory=list, description="Professional certifications"
    )
    publications: list[str] = Field(
        default_factory=list, description="Publications, blogs, talks, etc."
    )


# --- Model for the Audit/Validation ---
class AuditIssue(BaseModel):
    severity: str = Field(description="'Critical' for lies, 'Minor' for style.")
    issue: str
    suggestion: str


class AuditResult(BaseModel):
    passed: bool
    hallucination_score: int = Field(description="0-10. 0 means no hallucinations.")
    ai_cliche_score: int = Field(description="0-10. 10 means it sounds very robotic.")
    issues: list[AuditIssue]
    feedback_summary: str


class CoverLetter(BaseModel):
    content: str
    word_count: int


class ReviewResult(BaseModel):
    quality_score: int = Field(..., ge=0, le=10, description="Overall quality score")
    needs_improvement: bool = Field(
        ..., description="Whether another iteration is needed"
    )
    specific_suggestions: list[str] = Field(
        default_factory=list, description="Actionable improvements"
    )
    strengths: list[str] = Field(
        default_factory=list, description="What's working well"
    )
