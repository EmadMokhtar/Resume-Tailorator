# Fix Bug Prompt

Use this prompt to debug and fix issues systematically.

## Prompt

```
Fix the bug: [BUG_DESCRIPTION]

Debugging Process:
1. Understand the Issue
   - What is the expected behavior?
   - What is the actual behavior?
   - How to reproduce?
   - Error messages/stack traces?

2. Investigate Root Cause
   - Check recent changes (git log)
   - Review error logs (structlog output)
   - Add debugging logs if needed
   - Check test failures
   - Verify data/config

3. Identify Solution
   - Minimal change to fix issue
   - Consider edge cases
   - Avoid breaking existing functionality
   - Follow project patterns

4. Implement Fix
   - Follow Hexagonal Architecture
   - Use type hints
   - Add/update error handling
   - Update logging if needed
   - Follow Ruff style rules

5. Test the Fix
   - Write regression test for the bug
   - Ensure existing tests still pass
   - Test edge cases
   - Verify coverage ≥80%
   ```bash
   make tests
   make tests/coverage-check
   ```

6. Document
   - Add inline comments explaining the fix
   - Update CHANGELOG.md
   - Reference issue number in commit

Commit Format:
```
fix([scope]): [brief description]

[Detailed explanation of the bug and fix]

Fixes #[issue_number]
```

Root Cause Analysis Template:
```
## Bug Report
**Issue**: [What went wrong]
**Impact**: [Who/what is affected]
**Severity**: Critical / High / Medium / Low

## Root Cause
**Why it happened**: [Technical explanation]
**Code location**: [File and line number]

## Solution
**What was changed**: [Description of fix]
**Why this approach**: [Rationale]
**Alternatives considered**: [Other options]

## Prevention
**How to prevent**: [Process/check to add]
**Related issues**: [Similar bugs to watch for]
```

Common Issues Checklist:
- [ ] Type errors (run: uv run mypy)
- [ ] Unhandled exceptions
- [ ] Async/await misuse
- [ ] Race conditions
- [ ] Memory leaks
- [ ] Infinite loops
- [ ] Off-by-one errors
- [ ] Null/None references
- [ ] Configuration errors
- [ ] Environment-specific issues
```

## Example Usage

```
Fix the bug: API endpoint returns 500 error when workflow_id is invalid

[... rest of prompt with bug details ...]
```

## Related
- Agent: @senior-software-engineer-implementation
- Instructions: python.instructions.md, api.instructions.md, pytest.instructions.md
