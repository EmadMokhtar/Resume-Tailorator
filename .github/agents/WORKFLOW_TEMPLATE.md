# Workflow Template - Quick Start

Copy and paste this template to start a new feature development workflow with your custom agents.

---

## 🎯 Feature: [FEATURE NAME]

**Date Started**: [DATE]
**Status**: 🔄 In Progress

---

### Step 1: Design & Planning ✅

**Agent**: `@orchestrator`

**Prompt**:
```
@orchestrator I need to [DESCRIBE FEATURE/PROBLEM].

Requirements:
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

Please provide:
1. Technical design document
2. TODO list with specific agent assignments
3. Data models/schemas needed
4. API specifications (if applicable)
```

**Output**:
- [ ] Technical design received
- [ ] TODO list created
- [ ] Architecture approved

**Design Summary**:
```
[Paste design summary here]
```

**TODO List**:
1. [ ] Task 1
2. [ ] Task 2
3. [ ] Task 3
4. [ ] Task 4

---

### Step 2: Implementation 🔨

**Agent**: `@lead-software-engineer` (complex/critical) OR `@senior-software-engineer-implementation` (standard)

**Prompt (Complex Feature)**:
```
@lead-software-engineer Based on the design above, please implement [CRITICAL/COMPLEX FEATURE]:

This requires:
- [Technical consideration 1]
- [Technical consideration 2]
- [Technical consideration 3]

Follow project standards and security best practices.
```

**Prompt (Standard Feature)**:
```
@senior-software-engineer-implementation Based on the design above, please implement:

TODO List:
[Paste TODO list from Step 1]

Please follow:
- API conventions from .github/instructions/api.instructions.md
- Python best practices from .github/instructions/python.instructions.md
- Existing project structure in src/sidiap_azure_devops_agent/

Files to create/modify:
- [List expected files]
```

**Output**:
- [ ] Implementation complete
- [ ] All TODO items addressed
- [ ] Code follows conventions

**Files Modified**:
- [ ] File 1
- [ ] File 2
- [ ] File 3

---

### Step 3: Quality Review 🔍

**Agent**: `@senior-software-engineer-reviewer`

**Prompt**:
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

**Review #1**:
- **Confidence Score**: __%
- **Date**: [DATE]
- **Issues Found**:
  1. [Issue 1]
  2. [Issue 2]
  3. [Issue 3]
- **Status**: ⚠️ Needs fixes / ✅ Approved

---

### Step 4: Fix Issues (If Needed) 🔧

**Agent**: `@lead-software-engineer` or `@senior-software-engineer-implementation`

**Prompt (Standard)**:
```
@senior-software-engineer-implementation The reviewer found these issues (Confidence: __%).

Issues to fix:
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

Please fix these issues and improve the code.
```

**Prompt (Complex)**:
```
@lead-software-engineer The reviewer found these issues (Confidence: __%).

Issues to fix:
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

Please address these architectural/technical concerns.
```

**Review #2**:
- **Confidence Score**: __%
- **Date**: [DATE]
- **Issues Found**: [List or "None"]
- **Status**: ⚠️ Needs fixes / ✅ Approved

**Review #3** (if needed):
- **Confidence Score**: __%
- **Date**: [DATE]
- **Status**: ✅ Approved (90%+)

---

### Step 5: QA Testing 🧪

**Agent**: `@senior-qa-engineer`

**Prompt**:
```
@senior-qa-engineer The implementation has been reviewed and approved (90%+ confidence).

Please:
1. Analyze the [FEATURE NAME] implementation
2. Write comprehensive tests (unit + integration)
3. Ensure tests follow pytest conventions from .github/instructions/pytest.instructions.md
4. Create test files in appropriate locations
5. Include:
   - Happy path tests
   - Error handling tests
   - Edge cases
   - Validation tests
   - Integration tests (with mocks if needed)

Target: 90%+ test coverage
```

**Output**:
- [ ] Unit tests created
- [ ] Integration tests created
- [ ] Edge cases covered
- [ ] Test coverage ≥ 90%
- [ ] All tests passing

**Test Results**:
- **Coverage**: __%
- **Tests Passing**: __/__
- **Issues Found**: [List or "None"]

---

### Step 6: Fix Test Issues (If Needed) 🔧

**Agent**: `@lead-software-engineer` or `@senior-software-engineer-implementation`

**Prompt (Standard)**:
```
@senior-software-engineer-implementation The QA tests revealed these issues:

Test Failures:
1. [Test 1] - [Error description]
2. [Test 2] - [Error description]
3. [Test 3] - [Error description]

Please fix these issues while maintaining the overall architecture.
```

**Prompt (Complex)**:
```
@lead-software-engineer The QA tests revealed these critical issues:

Test Failures:
1. [Test 1] - [Error description]
2. [Test 2] - [Error description]
3. [Test 3] - [Error description]

Please address these issues.
```

**Re-test Results**:
- **Coverage**: __%
- **Tests Passing**: __/__ ✅
- **Status**: ✅ All tests passing

---

### Step 7: Optional Additions 📚

#### Security Review (Optional)

**Agent**: `@senior-security-engineer`

**Prompt**:
```
@senior-security-engineer Please perform a security review of the [FEATURE NAME] implementation, focusing on:
- Input validation
- Authentication/authorization
- Data exposure risks
- Injection vulnerabilities
- OWASP Top 10 considerations
```

**Output**:
- [ ] Security review complete
- [ ] Issues: [List or "None found"]
- [ ] Status: ✅ Approved

#### Documentation (Optional)

**Agent**: `@technical-writer`

**Prompt**:
```
@technical-writer Please document the new [FEATURE NAME]:
1. Update API documentation in openapi/openapi.yaml
2. Add usage examples to README.md or create new guide
3. Document any configuration needed
4. Add inline code documentation if needed
```

**Output**:
- [ ] API documentation updated
- [ ] Usage examples added
- [ ] Configuration documented
- [ ] README updated

---

### ✅ Completion Checklist

- [ ] Design approved by orchestrator
- [ ] Implementation complete with 90%+ confidence score
- [ ] All tests written and passing
- [ ] Test coverage ≥ 90%
- [ ] Documentation updated (if needed)
- [ ] Security reviewed (if applicable)
- [ ] Code committed following .github/instructions/commit.instructions.md
- [ ] Ready for deployment

---

## 📊 Summary

**Total Time**: [TIME]
**Iterations**:
- Implementation iterations: __
- QA iterations: __

**Final Metrics**:
- Reviewer confidence: __%
- Test coverage: __%
- Security status: [Reviewed/Not applicable]
- Documentation: [Complete/Not needed]

**Status**: ✅ Complete / 🔄 In Progress / ⚠️ Blocked

**Notes**:
```
[Add any additional notes, learnings, or considerations]
```

---

## 🔗 Quick Commands

For next feature, you can say:

- "Use the workflow template for [new feature name]"
- "@orchestrator Start workflow for [feature]"
- "Continue workflow from Step [X]"
