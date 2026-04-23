# Pytest Testing Instructions

**Applies to:** `**/test_*.py`, `**/*_test.py`, `**/tests/**/*.py`, `**/conftest.py`

## Testing Philosophy

- Test only public interfaces (not private methods)
- Patch only external dependencies (Azure SDK, databases, APIs, HTTP clients)
- One behavior per test, small and focused
- **Use pytest subtests for multiple independent assertions** (PROJECT STANDARD)
- Use fixtures for setup and dependency injection
- Keep tests independent (run in isolation)
- **Use descriptive test names**: `test_{scenario}_when_{condition}_then_{expected_result}`
- Follow AAA pattern: Arrange, Act, Assert

## Running Tests

> ⛔ **NEVER run pytest directly. ALWAYS use `make test` or `uv run pytest`.**

### Command Priority

1. **ALWAYS: Use Make** — `make test` or `make tests` (REQUIRED)
2. **FALLBACK: Use UV** — `uv run pytest` only if Make unavailable
3. **⛔ NEVER: Direct execution** — `python -m pytest`, `pytest`, `python pytest` are PROHIBITED

```bash
# ✅ REQUIRED: Use Make commands
make test                       # Run all tests
make tests                      # Same as make test
make tests/coverage-check       # Verify coverage >= 80%

# ✅ ACCEPTABLE: Use UV only if Make command doesn't exist
uv run pytest                   # Run all tests
uv run pytest tests/unit/       # Run specific directory
uv run pytest -k "test_user"    # Run tests matching pattern
uv run pytest -v                # Verbose output

# ❌ NEVER USE (BLOCKED):
pytest                                         # ❌ PROHIBITED — missing UV isolation
python -m pytest tests/api/test_users.py -v    # ❌ PROHIBITED — wrong Python version
python -m pytest                               # ❌ PROHIBITED
python pytest                                  # ❌ PROHIBITED
```

**Why `make test` is required:**
- ✅ Pre-configured with correct flags and coverage settings
- ✅ Ensures consistent test execution across all developers
- ✅ Manages virtual environment automatically
- ✅ Configured with project-specific settings
- ❌ `python -m pytest` bypasses project configuration
- ❌ Direct `pytest` won't work - must run via uv or make

## Basic Test Structure

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_user(client: AsyncClient) -> None:
    """Test getting a user by ID."""
    response = await client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["username"] == "test_user"
```

## Naming Conventions

**REQUIRED: Use descriptive test method names following the pattern:**

```
test_{scenario}_when_{condition}_then_{expected_result}
```

### Examples

```python
# ✅ CORRECT: Descriptive names with pattern
def test_create_user_when_valid_data_then_returns_201():
    ...

def test_create_user_when_email_already_exists_then_returns_409():
    ...

def test_get_user_when_user_not_found_then_returns_404():
    ...

def test_delete_user_when_soft_delete_then_sets_deleted_at():
    ...

def test_list_users_when_page_2_requested_then_returns_paginated_results():
    ...

async def test_update_order_when_status_invalid_then_raises_validation_error():
    ...

# ❌ WRONG: Vague or non-descriptive names
def test_user():  # What about the user?
    ...

def test_create():  # Create what? What's expected?
    ...

def test_error():  # Which error? Under what condition?
    ...

def test_it_works():  # What works? How?
    ...
```

### Pattern Breakdown

| Part | Description | Example |
|------|-------------|---------|
| `test_` | Required pytest prefix | `test_` |
| `{scenario}` | Action or feature being tested | `create_user`, `get_order`, `delete_item` |
| `when_` | Condition or input state | `when_valid_data`, `when_not_found`, `when_unauthorized` |
| `then_` | Expected outcome | `then_returns_201`, `then_raises_error`, `then_sets_deleted_at` |

### Async Test Naming

Same pattern applies to async tests:

```python
@pytest.mark.asyncio
async def test_fetch_data_when_api_timeout_then_raises_timeout_error():
    ...

@pytest.mark.asyncio
async def test_process_batch_when_items_exceed_limit_then_returns_paginated():
    ...
```

## Fixtures

### Fixture with `yield` for Context Managers

**Always use `yield` with context managers** - `return` exits immediately, breaking mocks:

```python
import pytest
from unittest.mock import patch

# Correct - keeps context manager alive
@pytest.fixture
def mock_database():
    with patch("app.database.get_connection") as mock:
        yield mock  # Test runs here, cleanup after
```

### Basic Fixture Example

```python
@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

### Fixture Scopes

| Scope | Lifecycle | Use Case |
|-------|-----------|----------|
| `function` (default) | Per test | Test data, temporary resources |
| `module` | Per file | Database connections per file |
| `session` | Entire test run | App config, expensive setup |

## Mocking with Fixtures

### Basic Mock Fixture

```python
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_azure_client():
    with patch("app.services.blob_storage.BlobServiceClient", autospec=True) as mock:
        mock_instance = MagicMock()
        mock_instance.upload_blob.return_value = {"blob_url": "https://example.com/blob"}
        mock.return_value = mock_instance
        yield mock
```

### Async Mock Example

```python
from unittest.mock import patch, AsyncMock

@pytest.fixture
def mock_database():
    with patch("app.database.get_session", autospec=True) as mock:
        mock_session = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_session
        yield mock_session
```

### Fixture Composition (Tests Declare Mocks Needed)

```python
@pytest.fixture
def mock_database():
    with patch("app.database.get_session") as mock:
        yield AsyncMock()

@pytest.fixture
def mock_email_service():
    with patch("app.services.email.send_email") as mock:
        mock.return_value = {"message_id": "test-123"}
        yield mock

# Test declares only needed mocks
def test_create_user(mock_database):
    user = create_user("alice", "alice@example.com")
    assert user.username == "alice"

def test_create_user_with_email(mock_database, mock_email_service):
    user = create_user_and_send_welcome("bob", "bob@example.com")
    mock_email_service.assert_called_once()
```

### Mocking HTTP Requests

```python
@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient", autospec=True) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(
            return_value=AsyncMock(status_code=200, json=lambda: {"data": "test"})
        )
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance
```

### Mocking Azure Blob Storage

```python
@pytest.fixture
def mock_blob_service_client():
    with patch("azure.storage.blob.BlobServiceClient", autospec=True) as mock:
        mock_instance = MagicMock()
        mock_blob = MagicMock()
        mock_blob.upload_blob.return_value = None
        mock_instance.get_blob_client.return_value = mock_blob
        mock.from_connection_string.return_value = mock_instance
        yield mock
```

## Parametrization

### Basic Parametrization

```python
@pytest.mark.parametrize("input,expected", [
    ("3+5", 8),
    ("2+4", 6),
])
def test_eval(input, expected):
    assert eval(input) == expected
```

### Custom Test IDs and Marks

```python
@pytest.mark.parametrize("username,email,valid", [
    pytest.param("alice", "alice@example.com", True, id="valid"),
    pytest.param("", "bob@example.com", False, id="empty_username"),
    pytest.param("admin", "admin@example.com", True, marks=pytest.mark.slow, id="admin"),
])
def test_user_validation(username, email, valid):
    assert validate_user(username, email) == valid
```

### Indirect Parametrization (Fixture as Parameter)

```python
@pytest.fixture
def user_factory(request):
    user_type = request.param
    return create_admin_user() if user_type == "admin" else create_regular_user()

@pytest.mark.parametrize("user_factory", ["admin", "regular"], indirect=True)
def test_user_permissions(user_factory):
    assert user_factory.can_login() is True
```

### Testing Success and Exceptions

```python
from contextlib import nullcontext as does_not_raise

@pytest.mark.parametrize("value,expectation", [
    (5, does_not_raise()),
    (-1, pytest.raises(ValueError)),
])
def test_validate_age(value, expectation):
    with expectation:
        validate_age(value)
```

## Best Practices

### Test Public Interface Only

✅ **Good** - Test public methods:
```python
def test_create_user():
    service = UserService()
    user = service.create_user("alice", "alice@example.com")
    assert user.username == "alice"
```

❌ **Bad** - Don't test private methods:
```python
def test_validate_email():
    service = UserService()
    service._validate_email("test@example.com")  # Don't test private methods
```

### Patch External Dependencies Only

**Mock these:**
- Azure SDK, databases, HTTP clients, file system, time/date, external APIs

✅ **Good** - Mock external dependency:
```python
@pytest.fixture
def mock_blob_client():
    with patch("azure.storage.blob.BlobServiceClient") as mock:
        yield mock
```

❌ **Bad** - Don't mock your own business logic:
```python
@patch("app.services.user_service.validate_email")  # Don't mock your own code
def test_create_user(mock_validate):
    # Defeats purpose of testing
```

### Keep Tests Small and Focused

✅ **Good** - One behavior per test:
```python
def test_user_creation_with_valid_data():
    user = create_user("alice", "alice@example.com")
    assert user.username == "alice"

def test_user_creation_with_invalid_email():
    with pytest.raises(ValidationError):
        create_user("bob", "invalid-email")
```

❌ **Bad** - Testing too much:
```python
def test_user_operations():
    # Create, update, delete in one test - split into 3 tests
```

## Subtests for Multiple Assertions (PROJECT STANDARD)

**CRITICAL: Always use pytest subtests for multiple independent assertions.**

This is our project standard for handling multiple assertions in a single test.

### Why Subtests?

✅ **All assertions execute** - Even if one fails, others still run
✅ **Clear failure messages** - Shows exactly which assertion failed
✅ **Better debugging** - See all failures at once, not just the first
✅ **Independent checks** - Each assertion is isolated

### Basic Usage

```python
import pytest

def test_user_validation_multiple_fields():
    """Test user validation with subtests for each field."""
    user = create_user("alice", "alice@example.com", age=25)

    # ✅ CORRECT: Use subtests for independent assertions
    with pytest.subtest("username"):
        assert user.username == "alice"

    with pytest.subtest("email"):
        assert user.email == "alice@example.com"

    with pytest.subtest("age"):
        assert user.age == 25
```

**Without subtests** (❌ WRONG):
```python
def test_user_validation_multiple_fields():
    user = create_user("alice", "alice@example.com", age=25)

    # ❌ BAD: If first assert fails, others don't run
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.age == 25
```

### Common Use Cases

**1. API Response Validation**
```python
def test_api_response_structure():
    response = client.get("/api/users/1")
    data = response.json()

    with pytest.subtest("status_code"):
        assert response.status_code == 200

    with pytest.subtest("user_id"):
        assert data["id"] == 1

    with pytest.subtest("username"):
        assert data["username"] == "alice"

    with pytest.subtest("email_format"):
        assert "@" in data["email"]
```

**2. Object Property Validation**
```python
def test_pydantic_model_validation():
    user = UserModel(name="Alice", email="alice@test.com", age=30)

    with pytest.subtest("name"):
        assert user.name == "Alice"

    with pytest.subtest("email"):
        assert user.email == "alice@test.com"

    with pytest.subtest("age"):
        assert user.age == 30

    with pytest.subtest("computed_field"):
        assert user.display_name == "Alice (alice@test.com)"
```

**3. Multiple Validation Rules**
```python
def test_password_validation_rules():
    password = "MyP@ssw0rd123"

    with pytest.subtest("length"):
        assert len(password) >= 12

    with pytest.subtest("uppercase"):
        assert any(c.isupper() for c in password)

    with pytest.subtest("lowercase"):
        assert any(c.islower() for c in password)

    with pytest.subtest("digit"):
        assert any(c.isdigit() for c in password)

    with pytest.subtest("special_char"):
        assert any(c in "!@#$%^&*()" for c in password)
```

### When to Use Subtests

✅ **Use subtests when:**
- Testing multiple independent properties of a single object
- Validating multiple fields in API response
- Checking multiple validation rules
- Verifying multiple computed values
- Testing multiple format requirements

❌ **Don't use subtests when:**
- Testing different behaviors → Split into separate tests
- Assertions are dependent on each other → Keep sequential
- Testing different scenarios → Use parametrize instead

### Installation

Subtests require the `pytest-subtests` plugin (already in project dependencies):

```bash
# Already installed via pyproject.toml
uv sync
```
- Assertions depend on each other → Use regular asserts

### Organize with conftest.py

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures for all tests
├── unit/
│   ├── conftest.py          # Unit test-specific fixtures
│   └── test_user_service.py
└── integration/
    ├── conftest.py          # Integration test-specific fixtures
    └── test_api_endpoints.py
```

**Always put fixtures in conftest.py** - pytest auto-discovers them, no imports needed.

### Key Principles Summary

1. Use `yield` in fixtures with context managers (not `return`)
2. Mock at boundary (external clients, not your code)
3. One fixture per dependency (composable)
4. Tests declare only needed mocks
5. Use `autospec=True` (prevents mocking non-existent methods)
6. Assert mock calls (verify interactions)
7. All fixtures in conftest.py (not in test files)
8. Test behavior, not implementation

## Quick Reference

### Common Patterns

| Pattern | Use Case |
|---------|----------|
| `@pytest.fixture` | Reusable test setup |
| `@pytest.mark.parametrize` | Multiple test inputs |
| `@pytest.mark.asyncio` | Async test functions |
| `pytest.raises()` | Assert exception raised |
| `mock.assert_called_once()` | Verify mock called |
| `mock.assert_called_with()` | Verify call arguments |
| `yield` in fixture | Context manager cleanup |
| `indirect=True` | Fixture as parameter |
| `pytest.param(..., marks=...)` | Conditional test execution |

### Assertions

```python
# Basic
assert x == y
assert x is None
assert x in collection

# Exceptions
with pytest.raises(ValueError):
    function_that_raises()

with pytest.raises(ValueError, match="message"):
    function_with_message()

# Approximate
assert value == pytest.approx(expected, rel=1e-3)
```

### Mock Assertions

```python
mock.assert_called()
mock.assert_called_once()
mock.assert_called_with(arg1, arg2)
mock.assert_called_once_with(arg1, arg2)
mock.assert_not_called()
args, kwargs = mock.call_args
```

### Mock Creation

```python
from unittest.mock import patch, MagicMock, AsyncMock

# Patch function
with patch("module.function") as mock:
    mock.return_value = "test"

# AsyncMock for async
mock = AsyncMock(return_value="result")
```
