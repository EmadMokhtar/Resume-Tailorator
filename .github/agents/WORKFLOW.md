# Iterative Development Workflow

This document provides a step-by-step guide for the iterative development workflow using custom GitHub Copilot agents.

## 🎯 Workflow Overview

```
Orchestrator → Lead/Implementation → Reviewer → [Loop until 90%] → QA → [Fix if needed] → ✅ Complete
```

## 📋 Workflow Steps

### Step 1: Design & Planning (Orchestrator)

**Agent**: `@orchestrator`

**Goal**: Create technical design and TODO list with agent assignments

**Instructions**:
1. Describe the feature or problem to the orchestrator
2. Request a technical design document
3. Ask for a detailed TODO list with agent assignments

**Example Prompt**:
```
@orchestrator I need to add a new endpoint for user profile management.
The endpoint should:
- Support CRUD operations for user profiles
- Include validation for email and phone fields
- Store data in DynamoDB
- Follow the existing architecture pattern

Please provide:
1. Technical design document
2. TODO list with specific agent assignments
```

**Expected Output**:
- Architecture diagram or description
- Data models and schemas
- API endpoint specifications
- TODO list with numbered tasks and agent assignments
- Considerations for security, testing, and documentation

**Next Step**: Orchestrator delegates to appropriate agents

---

### Step 2: Implementation (Lead Engineer or Implementation Engineer)

**Agents**: `@lead-software-engineer` or `@senior-software-engineer-implementation`

**Goal**: Implement the feature based on design and TODO list

**When to Use Each**:
- Use `@lead-software-engineer` for: complex features, critical systems, security-sensitive code
- Use `@senior-software-engineer-implementation` for: standard CRUD, routine features, well-defined tasks

**Instructions**:
1. Orchestrator delegates based on complexity
2. Engineer implements following the design
3. Follows project conventions and patterns

**Example Prompt (Complex Feature)**:
```
@lead-software-engineer Based on the design above, please implement the authentication system.

This is critical and requires:
- OAuth2 flow implementation
- JWT token generation and validation
- Integration with Azure AD
- Secure session management

Please follow security best practices and project standards.
```

**Example Prompt (Standard Feature)**:
```
@senior-software-engineer-implementation Based on the design above, please implement:

TODO List:
1. Create UserProfile model in models/user_profile.py
2. Implement DynamoDB adapter for profile storage
3. Create API endpoints in api/user_profiles.py
4. Add Pydantic schemas for request/response validation
5. Implement business logic in services/user_profiles_service.py

Please follow:
- API conventions from .github/instructions/api.instructions.md
- Python best practices from .github/instructions/python.instructions.md
- Existing project structure in src/sidiap_azure_devops_agent/
```

**Expected Output**:
- Complete implementation of all TODO items
- Clean, well-structured code
- Following project conventions
- Error handling and validation

**Next Step**: Click "🔍 Request Review" or invoke reviewer agent

---

### Step 3: Quality Review (Reviewer)

**Agent**: `@senior-software-engineer-reviewer`

**Goal**: Review implementation and provide confidence score

**Instructions**:
1. Ask reviewer to analyze the implementation
2. Request a confidence score (0-100%)
3. Get specific feedback on issues found

**Example Prompt**:
```
@senior-software-engineer-reviewer Please review the implementation above and provide:

1. Confidence score (0-100%) - we need 90%+ to proceed to QA
2. List of issues found (if any)
3. Suggestions for improvement
4. Whether it follows best practices and project conventions

Focus on:
- Code quality and maintainability
- Error handling
- Consistency with existing codebase
- Best practices from instruction files
```

**Expected Output**:
- **Confidence Score**: X%
- **Issues Found**: List of specific problems
- **Improvements**: Actionable suggestions
- **Best Practices**: Compliance check

**Decision Point**:
- **If confidence < 90%**: Go to Step 4 (Fix & Re-review)
- **If confidence ≥ 90%**: Go to Step 5 (QA Testing)

---

### Step 4: Fix Issues & Re-review (Loop)

**Agent**: `@lead-software-engineer` or `@senior-software-engineer-implementation` → `@senior-software-engineer-reviewer`

**Goal**: Address reviewer feedback and iterate until 90%+ confidence

**Instructions**:
1. Provide reviewer feedback to the appropriate implementation engineer
2. Ask to fix specific issues
3. Request review again
4. Repeat until confidence ≥ 90%

**Example Prompt to Implementation**:
```
@senior-software-engineer-implementation The reviewer found these issues:

Confidence Score: 75%

Issues:
1. Missing error handling for DynamoDB connection failures
2. Email validation regex doesn't handle all edge cases
3. Missing logging for profile updates
4. Inconsistent naming: use snake_case for all functions

Please fix these issues and improve the code.
```

**Or for Complex Features**:
```
@lead-software-engineer The reviewer found these architectural issues:

Confidence Score: 70%

Issues:
1. Authentication flow doesn't handle token refresh properly
2. Session state not being persisted correctly
3. Need circuit breaker for Azure AD calls
4. Missing rate limiting on auth endpoints

Please address these issues.
```

**Then Review Again**:
```
@senior-software-engineer-reviewer Please review the updated implementation and provide a new confidence score.
```

**Loop Until**: Confidence score ≥ 90%

**Next Step**: Once 90%+ achieved, go to Step 5

---

### Step 5: QA Testing (QA Engineer)

**Agent**: `@senior-qa-engineer`

**Goal**: Write comprehensive tests and verify code quality

**Instructions**:
1. Ask QA to analyze the implementation
2. Request comprehensive test suite
3. Get test coverage report

**Example Prompt**:
```
@senior-qa-engineer The implementation has been reviewed and approved (90%+ confidence).

Please:
1. Analyze the user profile management implementation
2. Write comprehensive tests (unit + integration)
3. Ensure tests follow pytest conventions from .github/instructions/pytest.instructions.md
4. Create test files in tests/api/test_user_profiles.py and tests/services/test_user_profiles_service.py
5. Include:
   - Happy path tests
   - Error handling tests
   - Edge cases
   - Validation tests
   - DynamoDB integration tests using mocks

Target: 90%+ test coverage
```

**Expected Output**:
- Complete test suite (unit + integration tests)
- Test coverage report
- Test documentation
- Any issues found during testing

**Decision Point**:
- **If tests reveal issues**: Go to Step 6 (Fix Test Issues)
- **If all tests pass**: Go to Step 7 (Complete)

---

### Step 6: Fix Test Issues (Implementation)

**Agent**: `@lead-software-engineer` or `@senior-software-engineer-implementation`

**Goal**: Fix bugs and issues discovered during testing

**Instructions**:
1. Provide QA test results and failures to appropriate engineer
2. Ask to fix failing tests and issues
3. Re-run tests with QA engineer
4. Repeat until all tests pass

**Example Prompt (Standard)**:
```
@senior-software-engineer-implementation The QA tests revealed these issues:

Test Failures:
1. test_create_profile_with_invalid_email - Email validation not working correctly
2. test_update_profile_nonexistent - Returns 500 instead of 404
3. test_concurrent_updates - Race condition in DynamoDB update

Please fix these issues while maintaining the overall architecture.
```

**Example Prompt (Complex)**:
```
@lead-software-engineer The QA tests revealed these critical issues:

Test Failures:
1. test_token_refresh - Refresh token flow fails after 30 minutes
2. test_concurrent_auth - Race condition in session management
3. test_azure_ad_failover - Circuit breaker not working correctly

Please fix these issues.
```

**Then Verify with QA**:
```
@senior-qa-engineer Please run the test suite again and verify all tests pass.
```

**Loop Until**: All tests pass with good coverage

**Next Step**: Once all tests pass, go to Step 7

---

### Step 7: Complete ✅

**Goal**: Finalize and document the implementation

**Optional - Documentation**:
```
@technical-writer Please document the new user profile management endpoints:
1. Update API documentation in openapi/openapi.yaml
2. Add usage examples to README.md or a new guide
3. Document any configuration needed
```

**Optional - Security Review**:
```
@senior-security-engineer Please perform a security review of the user profile implementation, focusing on:
- Input validation
- Authentication/authorization
- Data exposure risks
- Injection vulnerabilities
```

**Final Checklist**:
- ✅ Design approved by lead engineer
- ✅ Implementation complete with 90%+ reviewer confidence
- ✅ All tests written and passing
- ✅ Test coverage ≥ 90%
- ✅ Documentation updated (if needed)
- ✅ Security reviewed (if needed)
- ✅ Ready for deployment

---

## 🔄 Quick Reference

| Step | Agent | Action | Success Criteria |
|------|-------|--------|------------------|
| 1 | Orchestrator | Design & assign tasks | Clear design + agent assignments |
| 2 | Lead/Implementation | Code feature | Working implementation |
| 3 | Reviewer | Review code | Confidence score + feedback |
| 4 | Lead/Implementation | Fix issues | Loop until 90%+ confidence |
| 5 | QA Engineer | Write tests | Comprehensive test suite |
| 6 | Lead/Implementation | Fix bugs | All tests passing |
| 7 | Complete | Finalize | Production ready |

## 💡 Tips for Success

### 1. **Be Specific in Prompts**
- Provide clear requirements
- Reference existing files and patterns
- Mention relevant instruction files

### 2. **Provide Context**
```
@agent-name Context: [situation]
Task: [what to do]
Requirements: [specific needs]
Constraints: [limitations]
Expected Output: [what you want]
```

### 3. **Use Handoff Buttons**
VS Code Copilot provides handoff buttons between agents - use them for smoother workflow transitions.

### 4. **Track Progress**
Keep a running list of:
- Current step in workflow
- Confidence scores from each review
- Outstanding issues
- Test results

### 5. **Iterate Fearlessly**
The workflow is designed for iteration. Don't expect perfection on the first pass.

## 📊 Example Full Workflow

### Feature: Add Rate Limiting to API

**Step 1 - Design**:
```
@orchestrator Design a rate limiting solution for our API application:
- Support different limits per endpoint
- Use Redis for distributed rate limiting
- Include configuration in settings.py
- Provide TODO list with agent assignments
```

**Step 2 - Implementation (Delegated by Orchestrator)**:
```
@lead-software-engineer Implement the rate limiting system from above. This is critical infrastructure:
1. Rate limiter middleware in middleware/rate_limiter.py
2. Redis client configuration with connection pooling
3. Decorator for applying rate limits
4. Circuit breaker for Redis failures
5. Update existing endpoints to use rate limiting
```

**Step 3 - Review**:
```
@senior-software-engineer-reviewer Review the rate limiting implementation. Provide confidence score (need 90%+) and any issues.
```

Result: 78% - Missing error handling, Redis connection not properly managed

**Step 4 - Fix & Re-review**:
```
@lead-software-engineer Fix the issues:
1. Add proper Redis connection error handling
2. Implement connection pooling with retry logic
3. Add graceful degradation if Redis is unavailable
4. Add circuit breaker pattern
```

Then:
```
@senior-software-engineer-reviewer Review the updated implementation.
```

Result: 92% ✅ - Ready for QA

**Step 5 - QA**:
```
@senior-qa-engineer Write comprehensive tests for the rate limiting implementation:
- Test rate limit enforcement
- Test different endpoint limits
- Test Redis connection failures
- Test concurrent requests
- Integration tests with actual endpoints
```

Result: All tests pass, 94% coverage ✅

**Step 7 - Documentation**:
```
@technical-writer Document the rate limiting feature:
- Update README with configuration instructions
- Add API documentation for rate limit headers
- Create troubleshooting guide
```

**Complete!** ✅

## 🚨 Common Issues

### Issue: Low Confidence Score
**Solution**: Ask reviewer for specific feedback, fix issues one by one

### Issue: Tests Failing
**Solution**: Provide exact error messages to implementation engineer, fix systematically

### Issue: Stuck in Review Loop
**Solution**: Escalate to orchestrator or lead engineer for architectural guidance

### Issue: Unclear Requirements
**Solution**: Go back to orchestrator for clarification and redesign

## 📖 Related Resources

- [Agent README](README.agent.md) - Overview of all agents
- [Individual Agent Files](.github/agents/) - Detailed agent capabilities
- [Project Instructions](.github/instructions/) - Coding standards and best practices
- [GitHub Copilot Docs](https://docs.github.com/copilot) - Official documentation

---

**Remember**: The goal is high-quality, tested, production-ready code. Take the time to iterate through the workflow properly! 🚀
