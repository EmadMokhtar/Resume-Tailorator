import sys
from datetime import datetime, timezone

from pydantic_ai import AgentRunResult
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.usage import RunUsage

from resume_tailorator.models.agents.output import CV, CVDiff, FinalReport, JobAnalysis
from resume_tailorator.models.workflow import ResumeTailorResult
from resume_tailorator.utils.cv_diff import compute_cv_diff, compute_gap_analysis
from resume_tailorator.workflows.agents import (
    USAGE_LIMITS,
    _analyst_qs,
    _auditor_qs,
    _parser_qs,
    _writer_qs,
    analyst_agent,
    auditor_agent,
    report_agent,
    resume_parser_agent,
    reviewer_agent,
    run_agent,
    writer_agent,
    get_model,
    set_model,
)


class ResumeTailorWorkflow:
    MAX_RETRIES = 3
    max_review_iterations = 3
    max_write_attempts = 3

    # Pipeline stages for status tracking
    STAGES = [
        "PARSING_RESUME",
        "ANALYZING_JOB",
        "WRITING_CV",
        "REVIEWING_CV",
        "AUDITING_CV",
        "GENERATING_REPORT",
    ]

    def __init__(self):
        self._current_stage: str | None = None
        self._stage_status: dict[str, str] = {stage: "pending" for stage in self.STAGES}

    def _set_stage(self, stage: str) -> None:
        """Mark current stage as running, previous as done."""
        if self._current_stage and self._current_stage in self._stage_status:
            if self._stage_status[self._current_stage] == "running":
                self._stage_status[self._current_stage] = "done"
        self._current_stage = stage
        if stage in self._stage_status:
            self._stage_status[stage] = "running"

    def _complete_stage(self, stage: str, success: bool = True) -> None:
        """Mark a stage as completed or failed."""
        if stage in self._stage_status:
            self._stage_status[stage] = "failed" if not success else "done"

    def _print_pipeline_status(self) -> None:
        """Print current pipeline status."""
        print("\n" + "=" * 50)
        print("📊 PIPELINE STATUS")
        print("=" * 50)
        icons = {"pending": "⏳", "running": "🔄", "done": "✅", "failed": "❌"}
        labels = {
            "PARSING_RESUME": "Parse Resume",
            "ANALYZING_JOB": "Analyze Job",
            "WRITING_CV": "Write CV",
            "REVIEWING_CV": "Review CV",
            "AUDITING_CV": "Audit CV",
            "GENERATING_REPORT": "Generate Report",
        }
        for stage in self.STAGES:
            status = self._stage_status[stage]
            icon = icons.get(status, "?")
            label = labels.get(stage, stage)
            current_marker = "→" if (stage == self._current_stage and status == "running") else " "
            print(f"  {current_marker}{icon} {label}: {status.upper()}")
        print("=" * 50 + "\n")

    async def run(
        self,
        resume_text: str,
        job_content_file_path: str | None = None,
        job_content: str | None = None,
        model: str | None = None,
        verbose: bool = False,
    ) -> ResumeTailorResult:
        """Run the resume tailoring workflow.

        Args:
            resume_text: The resume content as text.
            job_content_file_path: Path to job posting file (legacy, file-based).
            job_content: Job posting markdown content (new, direct content).
            model: AI model override (e.g., openai:gpt-4o-mini).

        Note:
            If both job_content_file_path and job_content are provided, job_content takes priority.
        """
        # Override model if specified
        if model:
            set_model(model)
            print(f"🤖 Using model: {model}")
        else:
            print(f"🤖 Using model: {get_model()}")

        print("🚀 STARTING MULTI-AGENT PIPELINE\n")
        self._print_pipeline_status()

        total_usage = RunUsage()

        total_usage = RunUsage()

        # --- STEP 0: PARSE ORIGINAL RESUME ---
        self._set_stage("PARSING_RESUME")
        print("🤖 Agent 0 (Parser): Parsing original resume...")
        original_cv_result: AgentRunResult[CV] | None = None
        original_cv: CV | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                original_cv_result = await run_agent(
                    resume_parser_agent,
                    f"Parse this resume into structured format:\n\n{resume_text}",
                    verbose=verbose,
                    agent_label="Parser",
                    usage=total_usage,
                    usage_limits=USAGE_LIMITS,
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

            except UnexpectedModelBehavior:
                if _parser_qs.last_output is not None:
                    print(
                        "⚠️  Resume Parser quality gate exhausted — using best available output"
                    )
                    original_cv = _parser_qs.last_output
                    break
                self._complete_stage("PARSING_RESUME", success=False)
                sys.exit(
                    "❌ Resume Parser quality gate exhausted with no fallback available."
                )
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    self._complete_stage("PARSING_RESUME", success=False)
                    sys.exit("❌ Failed to parse original resume after retries.")

        if original_cv is None:
            if original_cv_result is None or original_cv_result.output is None:
                self._complete_stage("PARSING_RESUME", success=False)
                sys.exit("❌ Failed to parse original resume after retries.")
            original_cv = original_cv_result.output

        self._complete_stage("PARSING_RESUME")
        print(f"   ✅ Resume Parsed: {original_cv.full_name}")
        print(
            f"   📋 Found {len(original_cv.skills)} skills, {len(original_cv.experience)} work experiences\n"
        )

        original_cv_json = original_cv.model_dump_json()

        # --- STEP 1: ANALYZE JOB (Agent 1) ---
        self._set_stage("ANALYZING_JOB")
        print("🤖 Agent 1 (Analyst): Reading job post...")

        # Determine job content source
        if job_content:
            job_analysis_prompt = f"Analyze the following job posting and extract structured job data:\n\n{job_content}"
        elif job_content_file_path:
            job_analysis_prompt = f"Analyze the job content located at this file path {job_content_file_path} and extract structured job data."
        else:
            self._complete_stage("ANALYZING_JOB", success=False)
            sys.exit(
                "❌ No job content provided. Supply either job_content or job_content_file_path."
            )

        job_analysis_result: AgentRunResult[JobAnalysis] | None = None
        job_analysis: JobAnalysis | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                job_analysis_result = await run_agent(
                    analyst_agent,
                    job_analysis_prompt,
                    verbose=verbose,
                    agent_label="Analyst",
                    usage=total_usage,
                    usage_limits=USAGE_LIMITS,
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

            except UnexpectedModelBehavior:
                if _analyst_qs.last_output is not None:
                    print(
                        "⚠️  Job Analyst quality gate exhausted — using best available output"
                    )
                    job_analysis = _analyst_qs.last_output
                    break
                self._complete_stage("ANALYZING_JOB", success=False)
                sys.exit(
                    "❌ Job Analyst quality gate exhausted with no fallback available."
                )
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    self._complete_stage("ANALYZING_JOB", success=False)
                    sys.exit("❌ Failed to get complete job analysis after retries.")

        if job_analysis is None:
            if job_analysis_result is None or job_analysis_result.output is None:
                self._complete_stage("ANALYZING_JOB", success=False)
                sys.exit("❌ Failed to get complete job analysis after retries.")
            job_analysis = job_analysis_result.output

        self._complete_stage("ANALYZING_JOB")
        print(
            f"   ✅ Job Analyzed: {job_analysis.job_title} at {job_analysis.company_name}"
        )
        print(f"   🎯 Keywords found: {job_analysis.keywords_to_target}\n")
        self._print_pipeline_status()

        job_data_json = job_analysis.model_dump_json()

        # --- STEP 2: WRITE + REVIEW + AUDIT LOOP ---
        self._set_stage("WRITING_CV")
        new_cv: CV | None = None
        audit = None
        review = None
        audit_passed = False

        for write_attempt in range(self.max_write_attempts):
            self._set_stage("WRITING_CV")
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
                writer_result = await run_agent(
                    writer_agent,
                    writer_prompt,
                    verbose=verbose,
                    agent_label="Writer",
                    usage=total_usage,
                    usage_limits=USAGE_LIMITS,
                )
                new_cv = writer_result.output or None
            except UnexpectedModelBehavior:
                if _writer_qs.last_output is not None:
                    print(
                        "⚠️  CV Writer quality gate exhausted — using best available output"
                    )
                    new_cv = _writer_qs.last_output
                else:
                    print(
                        "⚠️  CV Writer quality gate exhausted with no fallback — skipping tailoring"
                    )
                    new_cv = None

            if new_cv is None:
                if write_attempt == self.max_write_attempts - 1:
                    self._complete_stage("WRITING_CV", success=False)
                    break  # exhausted retries — report phase still runs below
                continue

            self._complete_stage("WRITING_CV")
            print(f"   ✅ CV Drafted. Summary: {new_cv.summary[:100]}...\n")

            # --- STEP 2.5: QUALITY REVIEW (Agent 2.5) ---
            self._set_stage("REVIEWING_CV")
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
                    review_result = await run_agent(
                        reviewer_agent,
                        review_prompt,
                        verbose=verbose,
                        agent_label="Reviewer",
                        usage=total_usage,
                        usage_limits=USAGE_LIMITS,
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

                        refined_result = await run_agent(
                            writer_agent,
                            improvement_prompt,
                            verbose=verbose,
                            agent_label="Writer (refine)",
                            usage=total_usage,
                            usage_limits=USAGE_LIMITS,
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
            self._set_stage("AUDITING_CV")
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
                audit_result = await run_agent(
                    auditor_agent,
                    audit_prompt,
                    verbose=verbose,
                    agent_label="Auditor",
                    usage=total_usage,
                    usage_limits=USAGE_LIMITS,
                )
                audit = audit_result.output
            except UnexpectedModelBehavior:
                if _auditor_qs.last_output is not None:
                    print(
                        "⚠️  Auditor quality gate exhausted — using best available output"
                    )
                    audit = _auditor_qs.last_output
                else:
                    print(
                        "⚠️  Auditor quality gate exhausted with no fallback — skipping audit"
                    )
                    audit = None

            if audit is None:
                print(f"   ⚠️ Audit result is None on attempt {write_attempt + 1}")
                self._complete_stage("AUDITING_CV", success=False)
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry...\n")
                    continue
                else:
                    self._complete_stage("AUDITING_CV", success=False)
                    print("   ❌ Max attempts reached\n")
                    break

            audit_passed = getattr(audit, "passed", False)
            if audit_passed:
                self._complete_stage("AUDITING_CV")
                print(f"   ✅ Audit passed on attempt {write_attempt + 1}!\n")
                break  # exit loop — report phase runs below
            else:
                print(f"   ⚠️ Audit failed on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry with feedback...\n")
                else:
                    self._complete_stage("AUDITING_CV", success=False)
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
        self._set_stage("GENERATING_REPORT")
        try:
            print("\n🤖 Agent 5 (Report Writer): Generating self-review report...")

            cv_diff = (
                compute_cv_diff(original_cv, new_cv) if new_cv is not None else CVDiff()
            )
            gap_analysis = compute_gap_analysis(
                original_cv,
                new_cv,
                job_analysis_result.output
                if job_analysis_result and job_analysis_result.output
                else JobAnalysis(),
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

            report_result = await run_agent(
                report_agent,
                report_prompt,
                verbose=verbose,
                agent_label="Report",
                usage=total_usage,
                usage_limits=USAGE_LIMITS,
            )
            narrative = report_result.output

            final_report = FinalReport(
                job_title=job_analysis.job_title,
                company_name=job_analysis.company_name,
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
            self._complete_stage("GENERATING_REPORT")
            print("   ✅ Report generated.\n")

        except Exception as e:
            self._complete_stage("GENERATING_REPORT", success=False)
            print(f"   ⚠️ Report generation failed: {e}\n")

        # Print final pipeline status
        self._stage_status["GENERATING_REPORT"] = "done" if final_report else "failed"
        self._print_pipeline_status()

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
            company_name=job_analysis.company_name,
            job_title=job_analysis.job_title,
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