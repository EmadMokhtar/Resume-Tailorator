import logging
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, ModelRetry, RunContext

from models.agents.output import (
    AuditResult,
    CV,
    JobAnalysis,
    QualityCheckResult,
    ReviewResult,
    FinalReport,
    ScrapedJobPosting,
)
from tools.playwright import read_job_content_file
from tools.job_scraper_helpers import (
    detect_placeholder_content,
)

logger = logging.getLogger(__name__)


class _QualityState(BaseModel):
    """Holds the last output from one pipeline agent for fallback recovery."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    last_output: Any = None


_parser_qs = _QualityState()
_analyst_qs = _QualityState()
_writer_qs = _QualityState()
_auditor_qs = _QualityState()
_cover_qs = _QualityState()

MODEL_NAME = "openai:gpt-5-mini"

# --- Quality Gate Agent ---
# Universal reviewer: scores any pipeline agent's output 0-10 and requests improvements.
quality_gate_agent = Agent(
    MODEL_NAME,
    system_prompt="""You are a strict Quality Gate Reviewer for a resume tailoring pipeline.
Score the output of the agent whose role is specified in the prompt, on a scale of 0 to 10.
Scoring criteria by role:
  - Resume Parser: completeness, no data loss, correctly structured fields
  - Job Analyst: keyword coverage, clear requirement identification, no omissions
  - CV Writer: no hallucinations, ATS keywords incorporated naturally, human tone, no clichés
  - Auditor: thorough hallucination check, specific cliché identification, actionable feedback
  - Cover Letter Writer: authentic human voice, no AI clichés, specific to the role, concise
A score of 9 or 10 means ready to proceed.
A score below 9 means the output must be improved before the pipeline continues.
Always provide a reasoning and list specific improvements when score < 9.""",
    output_type=QualityCheckResult,
    retries=2,
)

# --- Agent 0: The Scraper ---
# Responsibility: Fetch the job posting content.
scraper_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are an expert Technical Recruiter.
    Your job is to analyze a raw job posting and extract structured data.
    Identify the core requirements, not just the 'nice to haves'.
    Look for 'hidden' keywords that ATS systems might scan for.
    """,
    output_type=JobAnalysis,
    tools=[read_job_content_file],
    retries=5,
)

# --- Agent 1: The Job Analyst ---
# Responsibility: Turn Markdown or raw text into a structured JobAnalysis object.
analyst_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are an expert Technical Recruiter.
    Your job is to analyze a raw job posting and extract structured data.
    Identify the core requirements, not just the 'nice to haves'.
    Look for 'hidden' keywords that ATS systems might scan for.
    """,
    output_type=JobAnalysis,
    retries=5,
)

# --- Agent 1.5: The Resume Parser ---
# Responsibility: Parse markdown resume into structured CV object
resume_parser_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are an expert Resume Parser.
    Your job is to parse a resume in Markdown format and extract all information into a structured format.
    
    RULES:
    1. Extract ALL information accurately from the markdown resume
    2. Preserve all skills, experiences, projects, education, and certifications
    3. Do NOT add or modify any information
    4. Maintain the exact wording and details from the original resume
    5. Structure work experience with company, role, dates, and highlight bullets
    6. Extract all technical and soft skills mentioned
    7. Include all projects with their descriptions
    """,
    output_type=CV,
    retries=5,
)

# --- Agent 2: The Writer ---
# Responsibility: Rewrite the CV based on the Analysis.
writer_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are a Senior Resume Writer.
    Input: A structured CV object and a Job Analysis.
    Task: Rewrite the CV to target the Job Analysis while preserving all original information.

    CRITICAL RULES:
    1. ONLY use skills, experiences, and information from the Original CV - DO NOT invent anything
    2. You may REPHRASE existing content to align with job keywords, but DO NOT add new skills or experiences
    3. Highlight relevant experiences that match the job requirements
    4. Use keywords from the job analysis naturally within existing content
    5. Use active voice and quantifiable achievements
    6. Avoid AI clichés like "orchestrated", "spearheaded", "leveraged", "synergy", "tapestry"
    7. Keep a professional but natural tone
    8. Maintain chronological order and accurate dates
    9. If the original CV lacks a required skill, do NOT add it - focus on highlighting transferable skills instead
    10. Group all the skills so that the most relevant skills to the job are at the top of the skills section
    """,
    output_type=CV,
    retries=5,
)

# --- Agent 3: The Auditor ---
# Responsibility: Compare Original vs New to catch lies and AI-speak.
auditor_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are a strict Compliance Auditor and Resume Quality Checker.
    Input: Original CV (structured), New CV (structured), and Job Analysis.

    Your task is to ensure the new CV is honest, professional, and well-targeted.

    VALIDATION CHECKS:
    
    1. HALLUCINATION CHECK (CRITICAL):
       - Verify NO new skills were added that don't exist in the original CV
       - Verify NO new companies, roles, or experiences were invented
       - Verify NO exaggerated dates or responsibilities
       - Each bullet point in the new CV must trace back to the original
       - Score: 0 = perfect, 10 = severe hallucinations
    
    2. AI CLICHÉ CHECK:
       - Flag overused AI phrases: "orchestrated", "spearheaded", "leveraged", "synergy", "tapestry", "dynamic", "innovative" (when overused)
       - Check for robotic or unnatural language
       - Ensure human-like, professional tone
       - Score: 0 = natural, 10 = very robotic
    
    3. RELEVANCE CHECK:
       - Verify the CV highlights experiences matching job requirements
       - Check if job keywords are naturally incorporated
       - Ensure the most relevant skills are prominent
    
    4. QUALITY CHECK:
       - Verify proper structure and formatting
       - Check for clear, quantifiable achievements
       - Ensure consistency in dates and information
    
    PASS CRITERIA:
    - Hallucination score must be 0-2 (minor rephrasing acceptable)
    - AI cliché score must be 0-3 (minimal AI language)
    - All critical issues must be resolved
    
    Return a detailed structured Audit Result with specific issues and actionable suggestions.
    """,
    output_type=AuditResult,
    retries=5,
)

# --- Agent 4: The Cover Letter Writer ---
# Responsibility: Write a personalized, human-sounding cover letter.
cover_letter_writer_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are an experienced Career Coach specializing in authentic, human cover letters.
    Input: A structured CV object and a Job Analysis.
    Task: Write a compelling cover letter that sounds genuinely human, not AI-generated.

    CRITICAL RULES:
    1. Write in a conversational, authentic tone - like a real person explaining why they're interested
    2. AVOID AI clichés at all costs: "leverage", "spearhead", "orchestrate", "passion for", "excited to bring", "dynamic", "synergy", "game-changer", "cutting-edge"
    3. Use simple, direct language - no corporate jargon or buzzwords
    4. Tell a brief, specific story connecting your experience to the role
    5. Reference actual projects or experiences from the CV (don't invent)
    6. Show you understand the company/role without generic flattery
    7. Keep it concise (3-4 short paragraphs max)
    8. Use contractions occasionally (I'm, I've, don't) to sound natural
    9. Vary sentence structure - mix short and longer sentences
    10. End with a simple, confident close (no "I look forward to hearing from you")

    STRUCTURE:
    - Opening: Why this specific role/company interests you (be specific, not generic)
    - Body: 1-2 examples of relevant experience with concrete details
    - Close: Brief statement of fit and next step

    TONE: Professional but personable. Write like you're explaining to a friend why you're applying.
    """,
    output_type=str,  # or create a CoverLetter pydantic model if you want structured output
    retries=5,
)


# --- Agent 3.5: The Reviewer ---
# Responsibility: Review quality and suggest specific improvements
reviewer_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are a Senior Resume Quality Reviewer.
    Input: A tailored CV and Job Analysis.
    Task: Review the CV quality and provide specific, actionable improvement suggestions.

    REVIEW CRITERIA:
    1. KEYWORD OPTIMIZATION:
       - Are critical job keywords naturally incorporated?
       - Are technical skills highlighted effectively?
       
    2. IMPACT & ACHIEVEMENTS:
       - Are accomplishments quantified where possible?
       - Is impact clearly demonstrated?
       
    3. RELEVANCE:
       - Is irrelevant content minimized?
       - Are most relevant experiences prioritized?
       
    4. CLARITY & READABILITY:
       - Is language clear and concise?
       - Are bullet points scannable?
       
    5. ATS COMPATIBILITY:
       - Is formatting ATS-friendly?
       - Are keywords in context?

    Return structured feedback with:
    - quality_score (0-10): Overall quality rating
    - needs_improvement (bool): True if score < 8
    - specific_suggestions (list): Concrete improvements needed
    - strengths (list): What's working well
    """,
    output_type=ReviewResult,  # You'll need to create this model
    retries=5,
)


# --- Agent 5: The Report Writer ---
# Responsibility: Write the narrative section of the self-review report.
# Receives pre-computed CVDiff, GapAnalysis, AuditResult, ReviewResult, and
# JobAnalysis as structured JSON. Produces only narrative fields (factual diff
# and gap data are injected by the workflow, not generated by the LLM).
report_agent = Agent(
    MODEL_NAME,
    system_prompt="""
    You are a Career Advisor writing a clear, honest self-review report.

    You receive pre-computed structured data about:
    - What changed between the original and tailored CV (CVDiff JSON)
    - Skill and keyword gaps vs. job requirements (GapAnalysis JSON)
    - Audit quality scores: hallucination and AI-cliché (AuditResult JSON)
    - Quality review scores (ReviewResult JSON)
    - Job requirements (JobAnalysis JSON)

    Your job is to produce ONLY the following narrative fields:
    1. overall_recommendation: exactly one of "Strong Match", "Partial Match", or "Weak Match"
       - "Strong Match": keyword_coverage_percent >= 80 AND missing_hard_skills <= 1
       - "Partial Match": keyword_coverage_percent >= 50 OR missing_hard_skills <= 3
       - "Weak Match": everything else
    2. match_score (0-100): base it primarily on keyword_coverage_percent,
       subtract 5 points per missing hard skill, subtract 2 per missing soft skill.
    3. suggestions_to_strengthen: 2-4 concrete, actionable items the candidate can do
       to close the gaps (certifications, side projects, courses, etc.)
    4. audit_summary: one paragraph in plain English summarising the hallucination
       score and AI-cliché score from the AuditResult.
    5. recommendation_rationale: one honest paragraph explaining your overall_recommendation.
       Be direct. Do not sugarcoat weak matches.

    CRITICAL RULES:
    - Never use AI clichés: "orchestrated", "spearheaded", "leveraged", "synergy",
      "tapestry", "dynamic", "innovative", "cutting-edge", "game-changer".
    - Do not repeat the raw JSON back. Synthesise it into human-readable text.
    - Be concise: audit_summary and recommendation_rationale should each be 2-4 sentences.

    You also receive raw structured JSON in the user prompt. For the following fields,
    copy them VERBATIM from the JSON input — do NOT reinterpret, summarise, or alter them:
    - what_changed: copy the CVDiff JSON object exactly as provided
    - gaps: copy the GapAnalysis JSON object exactly as provided
    - job_title: copy the job title string exactly as provided
    - company_name: copy the company name string exactly as provided
    - generated_at: copy the ISO 8601 timestamp string exactly as provided

    For the `passed` field: set it to true if BOTH of the following are true:
    - AuditResult.passed is true (hallucination_score <= 2 and clique_score <= 2)
    - overall_recommendation is "Strong Match" or "Partial Match"
    Otherwise set passed to false.
    """,
    output_type=FinalReport,
    retries=5,
)


# ---------------------------------------------------------------------------
# Quality Gate Validators
# ---------------------------------------------------------------------------


@resume_parser_agent.output_validator
async def _validate_resume_parser(ctx: RunContext[None], output: CV) -> CV:
    """Score the resume parser output. Raises ModelRetry if score < 9."""
    _parser_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Resume Parser\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output


@auditor_agent.output_validator
async def _validate_auditor(ctx: RunContext[None], output: AuditResult) -> AuditResult:
    """Score the auditor output. Raises ModelRetry if score < 9."""
    _auditor_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Auditor\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output


# --- Agent: JobScraperAgent ---
# Responsibility: Scrape job postings from URLs and validate extracted content.
job_scraper_agent = Agent(
    "openai:gpt-4o-mini",
    output_type=ScrapedJobPosting,
    retries=3,
)


@job_scraper_agent.system_prompt
async def build_scraper_instructions() -> str:
    """Build system prompt for the job scraper agent."""
    return """You are a job posting scraper and extractor.

Your task: Extract job posting content from HTML and convert to markdown.

CRITICAL RULES:
1. Never hallucinate job requirements, skills, or company info
2. Extract ONLY what is visible in the HTML
3. Use available tools in order:
   a. fetch_webpage(url) - get the HTML
   b. Try markitdown parsing first via extraction attempt
   c. If content looks incomplete, call validate_extraction and retry
4. Target output: Clean markdown with title, company, requirements
5. Stop and report error if content cannot be extracted after retries

QUALITY CHECKLIST:
- Content not placeholder (no error messages, click here, etc)
- Length > 200 chars (substantial job posting)
- Markdown formatted cleanly (no excessive blank lines)
- All required info present
"""


@job_scraper_agent.tool
async def fetch_webpage(ctx: RunContext[None], url: str, timeout: int = 30) -> str:
    """Fetch and execute webpage, returning HTML.

    Uses Playwright to handle JavaScript-heavy job boards.
    Returns raw HTML for parsing.

    Args:
        url: The job posting URL to fetch.
        timeout: Max seconds to wait (default 30).

    Returns:
        HTML content of the page.

    Raises:
        ValueError: If URL is invalid or timeout occurs.
    """
    from playwright.async_api import async_playwright

    logger.info(f"fetch_webpage_start: url={url}, timeout={timeout}")

    try:
        # Validate URL format
        if not url or not isinstance(url, str):
            raise ValueError(f"Invalid URL provided: {url}")

        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # Navigate to URL with timeout
                await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)

                # Wait for body element to ensure content is loaded
                await page.wait_for_selector("body", timeout=timeout * 1000)

                # Get page content
                html_content = await page.content()

                logger.info(
                    f"fetch_webpage_success: url={url}, content_length={len(html_content)}"
                )
                return html_content

            except Exception as e:
                error_msg = f"Error navigating to {url}: {str(e)}"
                logger.error(
                    f"fetch_webpage_error: url={url}, error={str(e)}, error_type={type(e).__name__}"
                )
                raise ValueError(error_msg) from e

            finally:
                await browser.close()

    except ValueError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error fetching webpage {url}: {str(e)}"
        logger.error(
            f"fetch_webpage_unexpected_error: url={url}, error={str(e)}, error_type={type(e).__name__}"
        )
        raise ValueError(error_msg) from e


@job_scraper_agent.tool_plain
def validate_extraction(raw_html: str, extracted_markdown: str) -> dict:
    """Validate extracted content meets quality thresholds.

    Checks:
    - Extracted markdown is not placeholder content (via helper)
    - Markdown length > 200 characters (substantial content)
    - Both source and extraction provided

    Args:
        raw_html: Original HTML content.
        extracted_markdown: Parsed markdown from HTML.

    Returns:
        dict with keys: valid (bool), message (str), quality_score (int, 0-100)

    Raises:
        ModelRetry: If validation fails, signals agent to retry.
    """
    logger.info(
        f"validate_extraction_start: html_length={len(raw_html) if raw_html else 0}, "
        f"markdown_length={len(extracted_markdown) if extracted_markdown else 0}"
    )

    # Check for presence of content
    if not raw_html or not extracted_markdown:
        msg = "Missing source HTML or extracted markdown"
        logger.warning(f"validate_extraction_missing_content: message={msg}")
        raise ModelRetry(msg)

    # Check for placeholder content
    if detect_placeholder_content(extracted_markdown):
        msg = "Extracted content appears to be placeholder/error content"
        logger.warning(
            f"validate_extraction_placeholder_detected: message={msg}, extracted_length={len(extracted_markdown)}"
        )
        raise ModelRetry(msg)

    # Check minimum length threshold
    if len(extracted_markdown.strip()) < 200:
        msg = f"Extracted content too short ({len(extracted_markdown.strip())} chars, need > 200)"
        logger.warning(
            f"validate_extraction_too_short: message={msg}, extracted_length={len(extracted_markdown.strip())}"
        )
        raise ModelRetry(msg)

    # Calculate quality score (0-100)
    markdown_len = len(extracted_markdown.strip())
    content_score = min(
        100, int((markdown_len / 5000) * 100)
    )  # Scale by typical job posting size

    result = {
        "valid": True,
        "message": "Extraction meets quality thresholds",
        "quality_score": content_score,
    }

    logger.info(
        f"validate_extraction_success: quality_score={content_score}, markdown_length={markdown_len}"
    )
    return result


@cover_letter_writer_agent.output_validator
async def _validate_cover_letter_writer(ctx: RunContext[None], output: str) -> str:
    """Score the cover letter output. Raises ModelRetry if score < 9."""
    _cover_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Cover Letter Writer\nOutput:\n{output}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output


@analyst_agent.output_validator
async def _validate_analyst(ctx: RunContext[None], output: JobAnalysis) -> JobAnalysis:
    """Score the job analyst output. Raises ModelRetry if score < 9."""
    _analyst_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Job Analyst\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output


@writer_agent.output_validator
async def _validate_writer(ctx: RunContext[None], output: CV) -> CV:
    """Score the writer output. Raises ModelRetry if score < 9."""
    _writer_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: CV Writer\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
