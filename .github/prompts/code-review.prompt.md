# Code Review Prompt

Use this prompt to perform comprehensive code reviews.

## Prompt

```
Review the code changes in [FILE/PR] focusing on:

Code Quality:
- [ ] Follows Hexagonal Architecture patterns
- [ ] Python type hints are complete and accurate
- [ ] Functions have Google-style docstrings
- [ ] Code is DRY (no duplication)
- [ ] Single Responsibility Principle applied
- [ ] Error handling is comprehensive
- [ ] Logging uses structlog with proper context

Standards Compliance:
- [ ] Ruff code style rules followed (line length ≤120)
- [ ] No Ruff violations (run: uv run ruff check)
- [ ] Type checking passes (run: uv run mypy)
- [ ] All tests pass (run: make tests)
- [ ] Test coverage ≥80% (run: make tests/coverage-check)

WebAPI Patterns:
- [ ] Async/await used correctly
- [ ] Dependency injection for services
- [ ] Pydantic schemas for validation
- [ ] Proper HTTP status codes
- [ ] Error responses follow RFC 7807
- [ ] OpenAPI documentation is accurate

Security:
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] Authentication/authorization checks
- [ ] Rate limiting where appropriate
- [ ] Sensitive data not logged

Testing:
- [ ] Unit tests for business logic
- [ ] Integration tests for API endpoints
- [ ] Edge cases covered
- [ ] Mocks only external dependencies
- [ ] Tests are independent and repeatable

Documentation:
- [ ] API endpoints documented in OpenAPI
- [ ] Complex logic has inline comments
- [ ] README updated if needed
- [ ] CHANGELOG.md updated

Provide:
1. Summary of changes and their purpose
2. List of issues found (Critical/Major/Minor)
3. Suggestions for improvement
4. Security concerns if any
5. Overall verdict: Approve / Request Changes / Comment
```

## Example Usage

```
Review the code changes in src/sidiap_azure_devops_agent/api/workflows.py focusing on:
[... rest of prompt ...]
```

## Related
- Agent: @senior-software-engineer-reviewer
- Instructions: python.instructions.md, api.instructions.md, pytest.instructions.md
