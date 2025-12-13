import sys
from pydantic_ai import AgentRunResult

from workflows.agents import (
    analyst_agent,
    writer_agent,
    auditor_agent,
    resume_parser_agent,
    reviewer_agent,
)
from models.agents.output import JobAnalysis, CV
from models.workflow import ResumeTailorResult


class ResumeTailorWorkflow:
    MAX_RETRIES = 3
    max_review_iterations = 3
    max_write_attempts = 3

    def __init__(self):
        pass

    async def run(
        self, resume_text: str, job_content_file_path: str
    ) -> ResumeTailorResult:
        print("🚀 STARTING MULTI-AGENT PIPELINE\n")

        # --- STEP 0: PARSE ORIGINAL RESUME ---
        print("🤖 Agent 0 (Parser): Parsing original resume...")
        original_cv_result: AgentRunResult[CV] | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                original_cv_result = await resume_parser_agent.run(
                    f"Parse this resume into structured format:\n\n{resume_text}"
                )

                if original_cv_result.output is None:
                    raise ValueError("Resume parsing returned None")

                if (
                    original_cv_result.output.full_name
                    and original_cv_result.output.experience
                ):
                    break  # Success

                print(
                    f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete resume parse, retrying..."
                )

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to parse original resume after retries.")

        if original_cv_result is None or original_cv_result.output is None:
            sys.exit("❌ Failed to parse original resume after retries.")

        original_cv = original_cv_result.output
        print(f"   ✅ Resume Parsed: {original_cv.full_name}")
        print(
            f"   📋 Found {len(original_cv.skills)} skills, {len(original_cv.experience)} work experiences\n"
        )

        # Store original CV as JSON for prompts
        original_cv_json = original_cv.model_dump_json()

        # --- STEP 1: ANALYZE JOB (Agent 1) ---
        print("🤖 Agent 1 (Analyst): Reading job post...")
        job_analysis_result: AgentRunResult[JobAnalysis] | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                job_analysis_result = await analyst_agent.run(
                    f"Analyze the job content located at this file path {job_content_file_path} and extract structured job data.",
                )

                print(f"   [Debug] Job Data: {job_analysis_result.output}")

                if job_analysis_result.output is None:
                    raise ValueError("Job analysis data is None")

                if (
                    job_analysis_result.output.job_title
                    and job_analysis_result.output.company_name
                ):
                    break  # Success

                print(
                    f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete job data, retrying..."
                )

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to get complete job analysis after retries.")

        if job_analysis_result is None or job_analysis_result.output is None:
            sys.exit("❌ Failed to get complete job analysis after retries.")

        print(
            f"   ✅ Job Analyzed: {job_analysis_result.output.job_title} at {job_analysis_result.output.company_name}"
        )
        print(
            f"   🎯 Keywords found: {job_analysis_result.output.keywords_to_target}\n"
        )

        # Prepare a JSON/string representation of the job data for prompts
        job_data_json = job_analysis_result.output.model_dump_json()

        # --- STEP 2: WRITE CV (Agent 2) with AUDIT LOOP ---
        new_cv = None
        audit = None

        for write_attempt in range(self.max_write_attempts):
            print(
                f"🤖 Agent 2 (Writer): Tailoring CV (Attempt {write_attempt + 1}/{max_write_attempts})..."
            )
            if write_attempt == 0:
                print(f"   [Debug] Original CV has {len(original_cv.skills)} skills")
                writer_prompt = f"""
Here is the Job Analysis:
{job_data_json}

Here is the Original CV (structured):
{original_cv_json}

Rewrite the CV to match the Job Analysis. Use ONLY the information from the Original CV.
Rephrase and reorganize to highlight relevant experience, but do NOT add new skills or experiences.
"""
            else:
                # Retry with audit feedback
                print("   🔄 Retrying with audit feedback...")
                issues_text = "\n".join(
                    [
                        f"- [{getattr(i, 'severity', 'Unknown')}] {getattr(i, 'issue', str(i))} -> {getattr(i, 'suggestion', '')}"
                        for i in getattr(audit, "issues", [])
                    ]
                )
                writer_prompt = f"""
The previous CV draft failed the audit. Here is the feedback:

Audit Feedback: {getattr(audit, "feedback_summary", "")}

Issues to fix:
{issues_text}

Here is the Job Analysis:
{job_data_json}

Here is the Original CV (structured):
{original_cv_json}

CRITICAL RULES:
1. ONLY use skills and experience from the Original CV - DO NOT add new skills
2. Fix all the issues mentioned in the audit feedback
3. Ensure all job requirements are addressed using ONLY existing skills from the original CV
4. Avoid AI clichés and use natural language
5. You may rephrase existing content but cannot add new information

Rewrite the CV to match the Job Analysis while addressing all audit feedback.
"""

            writer_result = await writer_agent.run(writer_prompt)

            new_cv = writer_result.output or None
            if new_cv is None:
                if write_attempt == self.max_write_attempts - 1:
                    return ResumeTailorResult(
                        company_name="",
                        tailored_resume="",
                        audit_report={},
                        passed=False,
                    )
                continue

            print(f"   ✅ CV Drafted. Summary: {new_cv.summary[:100]}...\n")

            # --- STEP 2.5: QUALITY REVIEW (Agent 2.5) ---
            for review_iteration in range(self.max_review_iterations):
                print(
                    f"🤖 Agent 2.5 (Reviewer): Checking CV quality (Iteration {review_iteration + 1}/{self.max_review_iterations})..."
                )

                review_prompt = f"""
Review this CV against job requirements:

CV: {new_cv.model_dump_json() if hasattr(new_cv, "model_dump_json") else str(new_cv)}
Job Analysis: {job_data_json}

Assess quality and suggest improvements if needed.
"""

                try:
                    review_result = await reviewer_agent.run(review_prompt)
                    review = review_result.output

                    if review is None:
                        print("   ⚠️ Review returned None, skipping quality check\n")
                        break

                    print(f"   📊 Quality Score: {review.quality_score}/10")

                    if review.strengths:
                        print(f"   ✨ Strengths: {', '.join(review.strengths[:2])}")

                    if (
                        review.needs_improvement
                        and review_iteration < self.max_review_iterations - 1
                    ):
                        print("   🔄 Quality improvements needed, refining...\n")

                        # Prepare suggestions text
                        suggestions_text = "\n".join(
                            f"- {s}" for s in review.specific_suggestions
                        )

                        # Refine CV based on review
                        improvement_prompt = f"""
Improve this CV based on reviewer feedback:

Current CV: {new_cv.model_dump_json() if hasattr(new_cv, "model_dump_json") else str(new_cv)}
Original CV: {original_cv_json}
Job Analysis: {job_data_json}

Specific improvements to address:
{suggestions_text}

CRITICAL RULES:
1. ONLY use information from the Original CV - DO NOT add new skills or experiences
2. Apply the suggestions to improve quality and relevance
3. Maintain accuracy and honesty
4. Use natural language, avoid AI clichés
5. Keep all dates and facts accurate

Focus on better highlighting relevant experience and incorporating job keywords naturally.
"""

                        refined_result = await writer_agent.run(improvement_prompt)
                        if refined_result.output:
                            new_cv = refined_result.output
                            print("   ✅ CV refined based on feedback\n")
                        else:
                            print("   ⚠️ Refinement returned None, keeping current CV\n")
                            break
                    else:
                        if review.needs_improvement:
                            print("   ℹ️ Max review iterations reached\n")
                        else:
                            print("   ✅ Quality check passed!\n")
                        break

                except Exception as e:
                    print(f"   ⚠️ Review failed: {e}, continuing with current CV\n")
                    break

            # For auditor prompt, prepare serializations
            new_cv_json = (
                new_cv.model_dump_json()
                if hasattr(new_cv, "model_dump_json")
                else str(new_cv)
            )

            # --- STEP 3: AUDIT (Agent 3) ---
            print("🤖 Agent 3 (Auditor): Validating for hallucinations and AI-speak...")
            audit_prompt = f"""
ORIGINAL CV (structured):
{original_cv_json}

NEW GENERATED CV (structured):
{new_cv_json}

JOB REQUIREMENTS:
{job_data_json}

Compare the two structured CVs carefully. Ensure that:
1. No new skills appear in the new CV that weren't in the original
2. No new companies or roles were invented
3. All experiences in the new CV can be traced back to the original
4. The language is professional and not AI-generated sounding
5. The new CV properly targets the job requirements using only original information
"""
            audit_result = await auditor_agent.run(audit_prompt)

            audit = audit_result.output
            if audit is None:
                print(f"   ⚠️ Audit result is None on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry...\n")
                    continue
                else:
                    print("   ❌ Max attempts reached\n")
                    # Return failure result
                    return ResumeTailorResult(
                        tailored_resume="",
                        audit_report={
                            "passed": False,
                            "hallucination_score": None,
                            "ai_cliche_score": None,
                            "feedback_summary": "Audit failed to return results after multiple attempts.",
                            "issues": [],
                        },
                        passed=False,
                    )

            # Check if audit passed
            passed = getattr(audit, "passed", False)
            if passed:
                print(f"   ✅ Audit passed on attempt {write_attempt + 1}!\n")
                return ResumeTailorResult(
                    company_name=job_analysis_result.output.company_name,
                    tailored_resume=new_cv.model_dump_json()
                    if new_cv and hasattr(new_cv, "model_dump_json")
                    else str(new_cv),
                    audit_report={
                        "passed": getattr(audit, "passed", None),
                        "hallucination_score": getattr(
                            audit, "hallucination_score", None
                        ),
                        "ai_cliche_score": getattr(audit, "ai_cliche_score", None),
                        "feedback_summary": getattr(audit, "feedback_summary", ""),
                        "issues": [
                            {
                                "severity": getattr(i, "severity", "Unknown"),
                                "issue": getattr(i, "issue", str(i)),
                                "suggestion": getattr(i, "suggestion", ""),
                            }
                            for i in getattr(audit, "issues", []) or []
                        ],
                    },
                    passed=True,
                )
            else:
                print(f"   ⚠️ Audit failed on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry with feedback...\n")
                else:
                    print("   ❌ Max attempts reached\n")

        # --- REPORTING ---
        print("\n" + "=" * 30)
        print("📋 FINAL AUDIT REPORT")
        print("=" * 30)

        # Ensure audit has a value, provide defaults if it's somehow None
        if audit is None:
            print("⚠️ Warning: No audit result available")
            return ResumeTailorResult(
                company_name=job_analysis_result.output.company_name,
                tailored_resume="",
                audit_report={
                    "passed": False,
                    "hallucination_score": None,
                    "ai_cliche_score": None,
                    "feedback_summary": "No audit result available.",
                    "issues": [],
                },
                passed=False,
            )

        passed = getattr(audit, "passed", None)
        hallucination_score = getattr(audit, "hallucination_score", None)
        ai_cliche_score = getattr(audit, "ai_cliche_score", None)
        feedback_summary = getattr(audit, "feedback_summary", "")

        print(f"Passed: {passed}")
        print(f"Hallucination Score (0 is best): {hallucination_score}")
        print(f"AI Cliche Score (0 is best): {ai_cliche_score}")
        print(f"Feedback: {feedback_summary}")

        issues = getattr(audit, "issues", []) or []
        if issues:
            print("\n⚠️ Issues Found:")
            for i in issues:
                sev = getattr(i, "severity", "Unknown")
                issue_text = getattr(i, "issue", str(i))
                suggestion = getattr(i, "suggestion", "")
                print(f" - [{sev}] {issue_text} -> {suggestion}")

        # Return final result (even if audit failed)
        return ResumeTailorResult(
            company_name=job_analysis_result.output.company_name,
            tailored_resume=new_cv.model_dump_json()
            if new_cv and hasattr(new_cv, "model_dump_json")
            else str(new_cv)
            if new_cv
            else "",
            audit_report={
                "passed": passed,
                "hallucination_score": hallucination_score,
                "ai_cliche_score": ai_cliche_score,
                "feedback_summary": feedback_summary,
                "issues": [
                    {
                        "severity": getattr(i, "severity", "Unknown"),
                        "issue": getattr(i, "issue", str(i)),
                        "suggestion": getattr(i, "suggestion", ""),
                    }
                    for i in issues
                ],
            },
            passed=passed or False,
        )
