# Write Tests Prompt

Use this prompt to generate comprehensive test suites.

## Prompt

```
Write comprehensive tests for [MODULE/FUNCTION/CLASS] following project standards:

Testing Strategy:
1. Unit tests for business logic (tests/unit/)
2. Integration tests for API endpoints (tests/integration/)
3. Follow AAA pattern: Arrange, Act, Assert
4. Use descriptive test names: test_[function]_[scenario]_[expected]

Test Requirements:
- Coverage ≥80% (verify with: make tests/coverage-check)
- Test success cases, error cases, and edge cases
- **CRITICAL: Use pytest subtests for multiple assertions** (PROJECT STANDARD)
- Use pytest fixtures for setup and teardown
- Mock only external dependencies (Azure SDK, databases, HTTP clients, file system)
- Do NOT mock internal business logic
- All tests must be independent and repeatable

**Subtests (REQUIRED):**
- Always use `pytest.subtest()` for multiple independent assertions
- Ensures all assertions run even if one fails
- Example:
```python
def test_user_validation():
    user = create_user("alice", "alice@example.com", age=25)

    with pytest.subtest("username"):
        assert user.username == "alice"

    with pytest.subtest("email"):
        assert user.email == "alice@example.com"

    with pytest.subtest("age"):
        assert user.age == 25
```

Fixtures:
- Use `yield` with context managers (not `return`)
- Create composable fixtures (one per dependency)
- Put fixtures in conftest.py
- Use `@pytest.fixture` with appropriate scope

Mocking:
✅ Mock these:
- Azure SDK clients (BlobServiceClient, etc.)
- Database connections
- HTTP clients (httpx, requests)
- External APIs
- Time/date functions
- File system operations

❌ Don't mock these:
- Your own business logic
- Pydantic models
- Internal functions

Running Tests:
```bash
make tests                      # Run all tests with coverage
make tests/coverage-check       # Verify coverage ≥80%
uv run pytest tests/unit/       # Run specific directory
uv run pytest -k "test_user"    # Run tests matching pattern
uv run pytest -v                # Verbose output
uv run pytest -x                # Stop on first failure
```

Test Structure:
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_azure_client():
    """Fixture for mocked Azure client."""
    with patch("azure.storage.blob.BlobServiceClient") as mock:
        mock.return_value.get_blob_client.return_value.download_blob = AsyncMock(
            return_value=b"test data"
        )
        yield mock

@pytest.mark.asyncio
async def test_function_success_case(mock_azure_client):
    """Test function succeeds with valid input."""
    # Arrange
    input_data = {"key": "value"}

    # Act
    result = await function_under_test(input_data)

    # Assert
    assert result.status == "success"
    mock_azure_client.assert_called_once()

def test_function_error_case():
    """Test function raises error with invalid input."""
    # Arrange
    invalid_input = None

    # Act & Assert
    with pytest.raises(ValueError, match="Input cannot be None"):
        function_under_test(invalid_input)
```

Generate tests for:
- Success scenarios
- Error scenarios (exceptions, invalid input)
- Edge cases (empty input, boundary values)
- Async operations (if applicable)
```

## Example Usage

```
Write comprehensive tests for src/sidiap_azure_devops_agent/services/workflows_service.py following project standards:
[... rest of prompt ...]
```

## Related
- Agent: @senior-qa-engineer
- Instructions: pytest.instructions.md, python.instructions.md
