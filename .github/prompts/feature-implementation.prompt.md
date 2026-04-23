# Feature Implementation Prompt

Use this prompt when implementing new features following project standards.

## Prompt

```
Implement [FEATURE_NAME] with the following requirements:

Requirements:
- [List functional requirements]
- [List non-functional requirements]

Implementation Guidelines:
1. Follow Hexagonal Architecture (api → services → ports ← adapters)
2. Use Python type hints for all function signatures
3. Apply Google docstring style for documentation
4. Use Pydantic for request/response schemas
5. Implement proper error handling with structlog
6. Add comprehensive tests (unit + integration, coverage ≥80%)
7. Follow Ruff code style rules
8. Use conventional commits for all changes

Structure:
- API layer: Create endpoint in `src/sidiap_azure_devops_agent/api/[domain].py`
- Service layer: Business logic in `src/sidiap_azure_devops_agent/services/[domain]_service.py`
- Schemas: Request/response models in `src/sidiap_azure_devops_agent/schemas/`
- Tests: Unit tests in `tests/unit/`, integration in `tests/integration/`

Testing Requirements:
- Write tests first (TDD approach)
- Mock external dependencies only (Azure SDK, DB, HTTP)
- Use pytest fixtures for setup
- Test success cases, error cases, and edge cases
- Run tests with: make tests

Commit Format:
feat([scope]): [description]

[body explaining what and why]

BREAKING CHANGE: [if applicable]
```

## Example Usage

```
Implement user authentication feature with the following requirements:

Requirements:
- JWT-based authentication
- Token refresh mechanism
- Rate limiting on login endpoint
- Audit logging for auth events

[... rest of prompt ...]
```

## Related
- Agent: @senior-software-engineer-implementation
- Instructions: python.instructions.md, api.instructions.md, pytest.instructions.md
