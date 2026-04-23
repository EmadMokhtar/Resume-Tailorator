import sys
from datetime import datetime, timezone

from pydantic_ai import AgentRunResult
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.usage import RunUsage

from models.agents.output import CV, CVDiff, FinalReport, JobAnalysis
from models.workflow import ResumeTailorResult
from utils.cv_diff import compute_cv_diff, compute_gap_analysis
from workflows.agents import (
    _analyst_qs,
    _auditor_qs,
    _parser_qs,
    _writer_qs,
    analyst_agent,
    auditor_agent,
    report_agent,
    resume_parser_agent,
    reviewer_agent,
    writer_agent,
)


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

        total_usage = RunUsage()

        # --- STEP 0: PARSE ORIGINAL RESUME ---
        print("🤖 Agent 0 (Parser): Parsing original resume...")
        original_cv_result: AgentRunResult[CV] | None = None
        original_cv: CV | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                original_cv_result = await resume_parser_agent.run(
                    f"Parse this resume into structured format:\n\n{resume_text}",
                    usage=total_usage,
                )

                if original_cv_result.output is None:
                    raise ValueError("Resume parsing returned None")

                if (
                    original_cv_result.output.full_name
                    and original_cv_result.output.experience
                ):
                    break

                print(
                    f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete resume parse, retrying..."
                )

            except UnexpectedModelBehavior as e:
                if _parser_qs.last_output is not None:
                    print("⚠️  Resume Parser quality gate exhausted — using best available output")
                    original_cv = _parser_qs.last_output
                    break
                sys.exit("❌ Resume Parser quality gate exhausted with no fallback available.")
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to parse original resume after retries.")

        if original_cv is None:
            if original_cv_result is None or original_cv_result.output is None:
                sys.exit("❌ Failed to parse original resume after retries.")
            original_cv = original_cv_result.output

        print(f"   ✅ Resume Parsed: {original_cv.full_name}")
        print(
            f"   📋 Found {len(original_cv.skills)} skills, {len(original_cv.experience)} work experiences\n"
        )

        original_cv_json = original_cv.model_dump_json()

        # --- STEP 1: ANALYZE JOB (Agent 1) ---
        print("🤖 Agent 1 (Analyst): Reading job post...")
        job_analysis_result: AgentRunResult[JobAnalysis] | None = None
        job_analysis: JobAnalysis | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                job_analysis_result = await analyst_agent.run(
                    f"Analyze the job content located at this file path {job_content_file_path} and extract structured job data.",
                    usage=total_usage,
                )

                print(f"   [Debug] Job Data: {job_analysis_result.output}")

                if job_analysis_result.output is None:
                    raise ValueError("Job analysis data is None")

                if (
                    job_analysis_result.output.job_title
                    and job_analysis_result.output.company_name
                ):
                    break

                print(
                    f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete job data, retrying..."
                )

            except UnexpectedModelBehavior as e:
                if _analyst_qs.last_output is not None:
                    print("⚠️  Job Analyst quality gate exhausted — using best available output")
                    job_analysis = _analyst_qs.last_output
                    break
                sys.exit("❌ Job Analyst quality gate exhausted with no fallback available.")
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to get complete job analysis after retries.")

        if job_analysis is None:
            if job_analysis_result is None or job_analysis_result.output is None:
                sys.exit("❌ Failed to get complete job analysis after retries.")
            job_analysis = job_analysis_result.output

        print(
            f"   ✅ Job Analyzed: {job_analysis.job_title} at {job_analysis.company_name}"
        )
        print(
            f"   🎯 Keywords found: {job_analysis.keywords_to_target}\n"
        )

        job_data_json = job_analysis.model_dump_json()

        # --- STEP 2: WRITE + REVIEW + AUDIT LOOP ---
        new_cv: CV | None = None
        audit = None
        review = None
        audit_passed = False

        for write_attempt in range(self.max_write_attempts):
            print(
                f"🤖 Agent 2 (Writer): Tailoring CV (Attempt {write_attempt + 1}/{self.max_write_attempts})..."
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

            try:
                writer_result = await writer_agent.run(writer_prompt, usage=total_usage)
                new_cv = writer_result.output or None
            except UnexpectedModelBehavior as e:
                if _writer_qs.last_output is not None:
                    print("⚠️  CV Writer quality gate exhausted — using best available output")
                    new_cv = _writer_qs.last_output
                else:
                    print("⚠️  CV Writer quality gate exhausted with no fallback — skipping tailoring")
                    new_cv = None

            if new_cv is None:
                if write_attempt == self.max_write_attempts - 1:
                    break  # exhausted retries — report phase still runs below
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
                    review_result = await reviewer_agent.run(
                        review_prompt, usage=total_usage
                    )
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

                        suggestions_text = "\n".join(
                            f"- {s}" for s in review.specific_suggestions
                        )

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

                        refined_result = await writer_agent.run(
                            improvement_prompt, usage=total_usage
                        )
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

            # --- STEP 3: AUDIT (Agent 3) ---
            new_cv_json = (
                new_cv.model_dump_json()
                if hasattr(new_cv, "model_dump_json")
                else str(new_cv)
            )

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
            try:
                audit_result = await auditor_agent.run(audit_prompt, usage=total_usage)
                audit = audit_result.output
            except UnexpectedModelBehavior as e:
                if _auditor_qs.last_output is not None:
                    print("⚠️  Auditor quality gate exhausted — using best available output")
                    audit = _auditor_qs.last_output
                else:
                    print("⚠️  Auditor quality gate exhausted with no fallback — skipping audit")
                    audit = None

            if audit is None:
                print(f"   ⚠️ Audit result is None on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry...\n")
                    continue
                else:
                    print("   ❌ Max attempts reached\n")
                    break

            audit_passed = getattr(audit, "passed", False)
            if audit_passed:
                print(f"   ✅ Audit passed on attempt {write_attempt + 1}!\n")
                break  # exit loop — report phase runs below
            else:
                print(f"   ⚠️ Audit failed on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry with feedback...\n")
                else:
                    print("   ❌ Max attempts reached\n")

        # Print audit report regardless of pass/fail
        print("\n" + "=" * 30)
        print("📋 FINAL AUDIT REPORT")
        print("=" * 30)

        if audit is None:
            print("⚠️ Warning: No audit result available")
        else:
            passed_display = getattr(audit, "passed", None)
            hallucination_score = getattr(audit, "hallucination_score", None)
            ai_cliche_score = getattr(audit, "ai_cliche_score", None)
            feedback_summary = getattr(audit, "feedback_summary", "")

            print(f"Passed: {passed_display}")
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

        # === REPORT PHASE — always runs ===
        final_report: FinalReport | None = None
        try:
            print("\n🤖 Agent 5 (Report Writer): Generating self-review report...")

            cv_diff = (
                compute_cv_diff(original_cv, new_cv) if new_cv is not None else CVDiff()
            )
            gap_analysis = compute_gap_analysis(
                original_cv,
                new_cv,
                job_analysis_result.output,
            )

            review_json = review.model_dump_json() if review is not None else "N/A"
            audit_json = audit.model_dump_json() if audit is not None else "N/A"

            report_prompt = f"""
CV Diff: {cv_diff.model_dump_json()}
Gap Analysis: {gap_analysis.model_dump_json()}
Audit Result: {audit_json}
Review Result: {review_json}
Job Analysis: {job_data_json}
"""

            report_result = await report_agent.run(report_prompt, usage=total_usage)
            narrative = report_result.output

            final_report = FinalReport(
                job_title=job_analysis_result.output.job_title,
                company_name=job_analysis_result.output.company_name,
                generated_at=datetime.now(timezone.utc).isoformat(),
                overall_recommendation=narrative.overall_recommendation,
                match_score=narrative.match_score,
                what_changed=cv_diff,
                gaps=gap_analysis,
                suggestions_to_strengthen=narrative.suggestions_to_strengthen,
                audit_summary=narrative.audit_summary,
                recommendation_rationale=narrative.recommendation_rationale,
                passed=audit_passed,
            )
            print("   ✅ Report generated.\n")

        except Exception as e:
            print(f"   ⚠️ Report generation failed: {e}\n")

        # Build audit_report dict for backward compatibility
        audit_report_dict: dict = {
            "passed": audit_passed,
            "hallucination_score": getattr(audit, "hallucination_score", None)
            if audit
            else None,
            "ai_cliche_score": getattr(audit, "ai_cliche_score", None)
            if audit
            else None,
            "feedback_summary": getattr(audit, "feedback_summary", "") if audit else "",
            "issues": [
                {
                    "severity": getattr(i, "severity", "Unknown"),
                    "issue": getattr(i, "issue", str(i)),
                    "suggestion": getattr(i, "suggestion", ""),
                }
                for i in (getattr(audit, "issues", []) or [])
            ],
        }

        return ResumeTailorResult(
            company_name=job_analysis_result.output.company_name,
            tailored_resume=(
                new_cv.model_dump_json()
                if new_cv and hasattr(new_cv, "model_dump_json")
                else str(new_cv)
                if new_cv
                else ""
            ),
            audit_report=audit_report_dict,
            passed=audit_passed,
            final_report=final_report,
        )
