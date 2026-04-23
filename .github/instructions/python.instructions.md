# Python Development Instructions

**Applies to:** `**/*.py`, `**/pyproject.toml`, `**/Makefile`

## Technologies

- **WebAPI**: Web framework for APIs
- **Pydantic**: Data validation and settings
- **Pytest**: Testing framework
- **structlog**: Structured logging
- **uv**: Package installer
- **Ruff**: Linter and formatter (line length: 120)
- **mypy**: Type checker
- **Prometheus**: Metrics (prometheus-client)

## Ruff Rules (REQUIRED)

**All Python code MUST follow these Ruff rules. The linter will enforce them.**

### Currently Enabled Rules

```toml
# pyproject.toml
[tool.ruff]
line-length = 120
lint.select = ["E", "F", "W", "I", "UP"]
```

| Code | Category | Description |
|------|----------|-------------|
| **E** | pycodestyle errors | PEP 8 style errors |
| **F** | Pyflakes | Logical errors (unused imports, undefined names) |
| **W** | pycodestyle warnings | PEP 8 style warnings |
| **I** | isort | Import sorting |
| **UP** | pyupgrade | Python version upgrade suggestions |

### Recommended Additional Rules

**Enable these rules for better code quality:**

```toml
# Recommended pyproject.toml configuration
[tool.ruff]
line-length = 120
lint.select = [
    "E",      # pycodestyle errors
    "F",      # Pyflakes
    "W",      # pycodestyle warnings
    "I",      # isort
    "UP",     # pyupgrade
    "B",      # flake8-bugbear (common bugs)
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez (timezone-aware datetimes)
    "S",      # flake8-bandit (security)
    "ANN",    # flake8-annotations (type hints)
    "LOG",    # flake8-logging
    "G",      # flake8-logging-format
    "A",      # flake8-builtins (shadowing)
    "PT",     # flake8-pytest-style
    "RUF",    # Ruff-specific rules
]
lint.ignore = [
    "ANN101",  # Missing type annotation for self (removed)
    "ANN102",  # Missing type annotation for cls (removed)
]
```

**Note:** For WebAPI-specific rules (FAST, ASYNC), see `api.instructions.md`.

### Key Rules You MUST Follow

#### DateTime Rules (DTZ) - Enforces ISO 8601

| Rule | Description |
|------|-------------|
| DTZ001 | `datetime()` without tzinfo |
| DTZ003 | `datetime.utcnow()` is deprecated |
| DTZ005 | `datetime.now()` without tz argument |

```python
# ❌ WRONG: DTZ003 - utcnow() is deprecated
created_at = datetime.utcnow()

# ❌ WRONG: DTZ005 - now() without timezone
created_at = datetime.now()

# ✅ CORRECT: Always use timezone
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)
```

#### Bugbear Rules (B) - Common Bugs

| Rule | Description |
|------|-------------|
| B006 | Mutable default argument |
| B008 | Function call in default argument |
| B904 | Raise without `from` in except |

```python
# ❌ WRONG: B006 - Mutable default
def add_item(items: list = []):  # Shared mutable default!
    items.append("new")
    return items

# ✅ CORRECT: Use None default
def add_item(items: list | None = None):
    if items is None:
        items = []
    items.append("new")
    return items

# ❌ WRONG: B008 - Function call in default
def process(data: dict = get_defaults()):  # Called once at import!
    ...

# ✅ CORRECT: Call inside function
def process(data: dict | None = None):
    if data is None:
        data = get_defaults()
    ...

# ❌ WRONG: B904 - Missing raise from
try:
    operation()
except ValueError as e:
    raise RuntimeError("Failed")  # Loses original traceback

# ✅ CORRECT: Chain exceptions
try:
    operation()
except ValueError as e:
    raise RuntimeError("Failed") from e
```

#### Security Rules (S) - flake8-bandit

| Rule | Description |
|------|-------------|
| S101 | Use of `assert` (disabled in optimized mode) |
| S105-S107 | Hardcoded passwords |
| S608 | SQL injection via string formatting |

```python
# ❌ WRONG: S608 - SQL injection risk
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ CORRECT: Use parameterized queries
query = "SELECT * FROM users WHERE id = :id"
result = await db.execute(query, {"id": user_id})
```

#### Pytest Rules (PT) - Test Best Practices

| Rule | Description |
|------|-------------|
| PT001 | Use `@pytest.fixture` not `@pytest.fixture()` |
| PT006 | Wrong type in `@pytest.mark.parametrize` |
| PT018 | Composite assertions should use subtests |

### Running Ruff

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check specific rules
uv run ruff check --select DTZ,B,S .
```

## Project Standards

### Date/Time Format (ISO 8601)

**CRITICAL: All dates must use ISO 8601 format.**

```python
from datetime import datetime, timezone

# ✅ CORRECT: ISO 8601 format
created_at: datetime = datetime.now(timezone.utc)  # 2024-01-15T10:30:00+00:00
date_string = datetime.now(timezone.utc).isoformat()  # "2024-01-15T10:30:00+00:00"

# For Pydantic models
class UserResponse(BaseModel):
    created_at: datetime  # Automatically serializes to ISO 8601
    updated_at: datetime | None = None

# ❌ WRONG: Custom date formats
date_string = datetime.now().strftime("%d/%m/%Y")  # BAD
date_string = datetime.now().strftime("%m-%d-%Y")  # BAD
```

**Rules:**
- Always use `datetime` with timezone (prefer UTC)
- Use `datetime.now(timezone.utc)` not `datetime.utcnow()` (deprecated)
- Pydantic automatically serializes to ISO 8601
- Store dates in UTC, convert to local time only for display

### Soft Delete (Required)

**CRITICAL: Always implement soft delete for data entities.**

```python
from datetime import datetime, timezone

class BaseModel(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None  # Soft delete marker
    is_deleted: bool = False

# In repository
async def delete(self, id: str) -> None:
    # ✅ CORRECT: Soft delete
    await self.update(id, {
        "deleted_at": datetime.now(timezone.utc),
        "is_deleted": True
    })

# ❌ WRONG: Hard delete
async def delete(self, id: str) -> None:
    await self.collection.delete_one({"id": id})  # BAD - data lost forever
```

**Rules:**
- Add `deleted_at: datetime | None` and `is_deleted: bool` to all entities
- Never permanently delete data (use soft delete)
- Filter out soft-deleted records in queries by default
- Only hard delete for GDPR compliance or explicit data purge requirements

## Clean Code Principles

- **DRY**: Extract common logic into functions/classes
- **Single Responsibility**: Functions do one thing only
- **Limit Arguments**: Max 3 parameters; use Pydantic models for more
- **No Boolean Flags**: Create separate functions instead
- **Avoid Deep Nesting**: Max 1-2 levels; use early returns
- **Pythonic Code**: Use comprehensions, built-ins, and idioms
- **Polymorphism**: Prefer inheritance over if/else chains
- **Named Constants**: Replace magic numbers with explanatory variables

```python
# Good patterns
def process_order(order: dict) -> None:
    validate_order(order)
    total = calculate_order_total(order)
    send_order_confirmation(total)

class UserData(BaseModel):
    name: str
    email: str

def create_user(data: UserData) -> User:
    pass

# Early returns
if not user or not user.is_authenticated:
    return
if user.has_permission('edit'):
    edit_data(user)
```

## Google Python Style Guide

### Imports

**CRITICAL: All imports must be at the top of the file.**

- All imports at the very top of the file (after module docstring)
- Standard library imports first, then third-party, then local
- Use `import x` for packages/modules, not individual classes
- Use `from x import y` where `x` is package, `y` is module
- No relative imports; use full package names
- Exception: Type annotations can be imported directly
- **Never import inside functions** (except for circular import resolution)

```python
# ✅ CORRECT: All imports at top
"""Module docstring."""
import json
from datetime import datetime
from typing import Any, Callable

from web_api import APIRouter
from pydantic import BaseModel

from sidiap_azure_devops_agent.models import workflow
from sidiap_azure_devops_agent.services import user_service


def process_data():
    # Function code here
    pass


# ❌ WRONG: Import inside function
def process_data():
    import json  # BAD - import at top instead
    from sidiap_azure_devops_agent.models import workflow  # BAD
    pass
```

### Exceptions

- Never use bare `except:`
- Use specific exception types
- Minimize code in try blocks
- Never use `assert` for validation (use `if`/`raise`)

```python
# Good
try:
    value = risky_operation()
except (SpecificError, AnotherError) as e:
    logger.error("Operation failed", error=str(e))
    raise
```

### Mutable Defaults

Never use mutable objects as defaults:

```python
# Bad
def add_item(item, items=[]):
    items.append(item)

# Good
def add_item(item, items: list | None = None):
    if items is None:
        items = []
    items.append(item)
```

### Mutable Global State

Avoid mutable globals. Use constants or classes:

```python
# Bad
_active_connections = []

# Good
class ConnectionPool:
    def __init__(self):
        self._connections = []
```

### True/False Evaluations

- Use implicit false: `if not users:`
- Always use `is None` or `is not None`
- Never compare booleans with `==`

```python
# Good
if not users:
    handle_empty()
if value is None:
    value = default

# Bad
if len(users) == 0:
    handle_empty()
if value == None:
    value = default
```

### Comprehensions

Simple cases only; prefer clarity over brevity:

```python
# Good
result = [item.process() for item in items if item.is_valid()]

# Bad - too complex
result = [(x, y) for x in range(10) for y in range(5) if x * y > 10]
```

### Properties

Use for trivial, cheap operations only. No I/O or expensive computations:

```python
# Good
@property
def fahrenheit(self) -> float:
    return self._celsius * 9/5 + 32

# Bad - expensive operation
@property
def content(self) -> str:
    return self._fetch_from_database()
```

### Lambda Functions

Max one line; use regular functions for complex logic:

```python
# Good
multiply = lambda x, y: x * y

# Bad - too complex
func = lambda x: [y for y in x if y % 2 == 0]
```

### Decorators

Use `functools.wraps` to preserve function metadata:

```python
from functools import wraps

def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

## Style Rules

### Line Length

- Max 120 characters (enforced by Ruff)
- Break long lines at logical points

### Indentation

- 4 spaces per level
- Continuation lines: 4 spaces or hanging indent

### Trailing Commas

Use for multi-line collections:

```python
FILES = [
    'setup.cfg',
    'tox.ini',
]
```

### Blank Lines

- 2 blank lines between top-level definitions
- 1 blank line between method definitions
- 1 blank line between logical sections in functions

### Whitespace

```python
# Good
spam(ham[1], {eggs: 2})
if x == 4:
    print(x, y)

# Bad
spam( ham[ 1 ], { eggs: 2 } )
```

### Main Guard

```python
def main():
    pass

if __name__ == '__main__':
    main()
```

### Function Length

Prefer functions under 40 lines. Long functions OK if clear and focused.

### Accessors

Use direct attributes or properties. No Java-style getters/setters:

```python
# Good
class Person:
    def __init__(self):
        self.name = None

# Good - property for validation
class Person:
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not value:
            raise ValueError("Name cannot be empty")
        self._name = value
```

## Import Ordering

1. Standard library
2. Third-party packages
3. Local application/library

```python
import os
import sys

from web_api import WebAPI
from pydantic import BaseModel

from sidiap_azure_devops_agent.models import workflow
from sidiap_azure_devops_agent.services import workflows_service
```

## Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Module | lowercase_with_underscores | `my_module.py` |
| Package | lowercase | `mypackage` |
| Class | CapWords | `MyClass` |
| Exception | CapWords (suffix: Error) | `ValidationError` |
| Function/Method | lowercase_with_underscores | `my_function()` |
| Constant | UPPER_WITH_UNDERSCORES | `MAX_VALUE` |
| Variable | lowercase_with_underscores | `my_var` |
| Private | _leading_underscore | `_internal` |
| Type Variable | CapWords | `T`, `RequestT` |

**Avoid:** Single letters (except i, j, k for loops; e for exceptions; f for files), dashes, trailing underscores

**Predicates:** `is_valid`, `has_permission`, `can_edit`
**Converters:** `to_dict`, `from_json`, `as_string`

## Error Handling

### Catch Specific Exceptions

```python
# Good
try:
    data = fetch_data(url)
except (HTTPError, TimeoutError) as e:
    logger.error("Fetch failed", url=url, error=str(e))
    raise
```

### Custom Exceptions

```python
class ValidationError(Exception):
    """Raised when validation fails."""
    pass

def validate_data(data: dict) -> None:
    if 'required_field' not in data:
        raise ValidationError("Missing required_field")
```

## Comments

**Use when:**
- Complex algorithms
- Non-obvious workarounds
- Future improvements (TODO)

**Don't use when:**
- Stating the obvious
- Explaining bad code (refactor instead)
- Outdated (keep in sync or remove)

## Documentation

### Docstrings (Google Style - REQUIRED)

**CRITICAL: Always use Google-style docstrings for ALL modules, classes, and functions.**

Required sections by element type:

| Element | Required Sections |
|---------|-------------------|
| Module | Summary, optional detailed description |
| Class | Summary, `Attributes:` (for public attributes) |
| Function/Method | Summary, `Args:`, `Returns:`, `Raises:` (as applicable) |

#### Function Docstrings

```python
def fetch_workflow(workflow_id: str) -> Workflow:
    """Fetch workflow by ID.

    Args:
        workflow_id: Unique workflow identifier.

    Returns:
        Workflow object.

    Raises:
        NotFoundError: Workflow doesn't exist.
    """
    pass
```

#### Class Docstrings

**CRITICAL: All classes MUST have an `Attributes:` section documenting public attributes.**

```python
class WorkflowService:
    """Service for workflow operations.

    Handles workflow creation, retrieval, and lifecycle management
    with support for async operations.

    Attributes:
        repository: Workflow data repository.
        cache: Optional cache for workflow lookups.
        timeout: Default timeout for operations in seconds.
    """

    def __init__(self, repository: IWorkflowRepository) -> None:
        """Initialize the workflow service.

        Args:
            repository: Repository for workflow persistence.
        """
        self.repository = repository
        self.cache: dict[str, Workflow] = {}
        self.timeout = 30.0
```

#### Exception Class Docstrings

```python
class WorkflowNotFoundError(Exception):
    """Raised when a workflow cannot be found.

    Attributes:
        workflow_id: The ID of the workflow that was not found.
        message: Error description.
    """

    def __init__(self, workflow_id: str) -> None:
        """Initialize the error.

        Args:
            workflow_id: The ID of the workflow that was not found.
        """
        self.workflow_id = workflow_id
        self.message = f"Workflow {workflow_id} not found"
        super().__init__(self.message)
```

#### Pydantic Model Docstrings

```python
class UserCreate(BaseModel):
    """Request model for user creation.

    Attributes:
        username: Unique username (3-50 characters).
        email: Valid email address.
        password: Password (minimum 8 characters).
    """

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
```

#### Enum Docstrings

```python
class OrderStatus(StrEnum):
    """Order status values.

    Represents the lifecycle states of an order in the system.

    Attributes:
        PENDING: Order is awaiting processing.
        PROCESSING: Order is being processed.
        COMPLETED: Order has been fulfilled.
        CANCELLED: Order was cancelled.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

#### Module Docstrings

```python
"""Workflow service module.

This module provides the WorkflowService class for managing workflow
operations including creation, retrieval, and lifecycle management.

Example:
    from app.services.workflow import WorkflowService

    service = WorkflowService(repository)
    workflow = await service.create(data)
"""
```

## Strings and Resources

### String Formatting

Prefer f-strings:

```python
# Good
message = f"User {user.name} has {count} items"

# Acceptable for templates
message = "User {} has {} items".format(user.name, count)
```

### Logging

Use structlog with structured data:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("workflow_created", workflow_id=workflow.id, user_id=user.id)
logger.error("validation_failed", errors=errors, data=data)
```

**Levels:** DEBUG → INFO → WARNING → ERROR → CRITICAL

### Files and Resources

Always use context managers:

```python
# Good
with open('file.txt') as f:
    data = f.read()

# Good - async
async with aiofiles.open('file.txt') as f:
    data = await f.read()
```

### TODO Comments

```python
# TODO(username): Brief description
# TODO(username): #123 - Link to issue
```

### Multi-line Strings

```python
# Good for code
long_string = (
    "This is a long string that "
    "spans multiple lines."
)

# Good for docstrings
docstring = """This is a docstring.

It can span multiple lines.
"""
```

### Raw Strings

Use for regex and Windows paths:

```python
pattern = r'\d{3}-\d{3}-\d{4}'
path = r'C:\Users\Documents'
```

## Type Hints

### General Rules

- Use for all public functions, methods, and class attributes
- Use `|` syntax for unions (Python 3.10+)
- Use built-in generics: `list[str]`, `dict[str, int]`

```python
def process_items(items: list[str]) -> dict[str, int]:
    """Process items and return counts."""
    pass

def get_user(user_id: str) -> User | None:
    """Get user by ID or None if not found."""
    pass
```

### Type Aliases

```python
from typing import TypeAlias

UserId: TypeAlias = str
ItemCount: TypeAlias = dict[str, int]

def count_items(user_id: UserId) -> ItemCount:
    pass
```

### Generics

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def get(self, id: str) -> T | None:
        pass

    def list(self) -> list[T]:
        pass
```

### Conditional Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidiap_azure_devops_agent.models import LargeModel
```

### Forward References

Use string quotes for forward references:

```python
class Node:
    def __init__(self, value: int):
        self.value = value
        self.next: 'Node | None' = None
```

### Pydantic Models (V2 REQUIRED)

**CRITICAL: Always use Pydantic V2 syntax. V1 syntax is deprecated.**

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

class WorkflowCreate(BaseModel):
    """Request model for workflow creation."""

    # ✅ V2: Use model_config with ConfigDict
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    tags: list[str] = []

    # ✅ V2: Use @field_validator with @classmethod
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v
```

### Pydantic V2 Migration Guide

| V1 (DEPRECATED) | V2 (REQUIRED) |
|-----------------|---------------|
| `class Config:` | `model_config = ConfigDict(...)` |
| `@validator` | `@field_validator` with `@classmethod` |
| `@root_validator` | `@model_validator` |
| `orm_mode = True` | `from_attributes=True` |
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.parse_obj()` | `.model_validate()` |
| `.parse_raw()` | `.model_validate_json()` |
| `__fields__` | `model_fields` |
| `update_forward_refs()` | `model_rebuild()` |

### V1 vs V2 Examples

```python
# ❌ WRONG: V1 syntax (DEPRECATED)
class UserV1(BaseModel):
    name: str

    class Config:
        orm_mode = True

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

user_dict = user.dict()
user_json = user.json()
user = User.parse_obj(data)

# ✅ CORRECT: V2 syntax (REQUIRED)
class UserV2(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()

user_dict = user.model_dump()
user_json = user.model_dump_json()
user = User.model_validate(data)
```

### Model Validators (V2)

```python
from pydantic import BaseModel, model_validator

class OrderCreate(BaseModel):
    items: list[str]
    discount: float = 0.0

    # ✅ V2: Use @model_validator for cross-field validation
    @model_validator(mode='after')
    def validate_discount(self) -> 'OrderCreate':
        if self.discount > 0 and len(self.items) < 3:
            raise ValueError('Discount requires at least 3 items')
        return self
```

### Field Serialization (V2)

```python
from pydantic import BaseModel, field_serializer, computed_field

class User(BaseModel):
    first_name: str
    last_name: str
    password: str

    # ✅ V2: Computed fields
    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    # ✅ V2: Custom serialization
    @field_serializer('password')
    def hide_password(self, v: str) -> str:
        return '***HIDDEN***'
```

### Async Type Hints

```python
from collections.abc import Awaitable, AsyncIterator

async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    pass

async def generate_items() -> AsyncIterator[str]:
    """Generate items asynchronously."""
    for i in range(10):
        yield f"item-{i}"
```

## Configuration Management

Use **Pydantic Settings V2** (`pydantic-settings`) for all application configuration.
It reads values from environment variables and `.env` files with full type validation.

### Installation

```bash
uv add pydantic-settings
```

### Core Pattern

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Attributes:
        app_name: Human-readable application name.
        debug: Enable debug mode.
        database_url: Database connection string.
        api_key: External API key (sensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",           # ignore unknown env vars
    )

    app_name: str = "MeetingMind"
    debug: bool = False
    database_url: str
    api_key: str | None = None


# Module-level singleton — import this everywhere
settings = Settings()
```

### Environment Prefix

Use `env_prefix` to namespace all variables and avoid collisions:

```python
class Settings(BaseSettings):
    """Application settings with MYAPP_ prefix.

    Attributes:
        api_key: API key read from MYAPP_API_KEY env var.
        debug: Debug flag read from MYAPP_DEBUG env var.
    """

    model_config = SettingsConfigDict(
        env_prefix="MYAPP_",      # MYAPP_API_KEY, MYAPP_DEBUG, etc.
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    api_key: str
    debug: bool = False
```

### Sensitive Values — Use `SecretStr`

Never store secrets as plain `str`. Use `SecretStr` to prevent accidental logging:

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings with protected secret fields.

    Attributes:
        api_key: API key, masked in logs and repr.
        database_password: Database password, masked in logs and repr.
        debug: Enable debug mode.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_key: SecretStr                  # printed as '**********'
    database_password: SecretStr
    debug: bool = False

    def get_api_key(self) -> str:
        """Return the raw API key value."""
        return self.api_key.get_secret_value()


settings = Settings()
# ✅ Safe — SecretStr hides the value
print(settings.api_key)             # api_key=SecretStr('**********')
# ✅ Only expose when needed
print(settings.get_api_key())       # sk-actual-key-here
```

### Nested Configuration with `BaseModel`

Group related settings into nested `BaseModel` objects:

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database connection configuration.

    Attributes:
        host: Database host.
        port: Database port.
        name: Database name.
        pool_size: Connection pool size.
    """

    host: str = "localhost"
    port: int = 5432
    name: str = "myapp"
    pool_size: int = Field(default=10, ge=1, le=100)


class Settings(BaseSettings):
    """Application settings with nested configuration.

    Attributes:
        debug: Enable debug mode.
        db: Database connection settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="MYAPP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    debug: bool = False
    db: DatabaseConfig = DatabaseConfig()
```

Configure nested fields via env vars using double underscore `__` as separator:

```bash
# .env
MYAPP_DB__HOST=prod-db.example.com
MYAPP_DB__PORT=5432
MYAPP_DB__POOL_SIZE=20
```

### Multiple `.env` Files (dev / prod)

```python
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV = os.getenv("APP_ENV", "development")

class Settings(BaseSettings):
    """Settings loaded from environment-specific .env file.

    Attributes:
        app_name: Application name.
        debug: Enable debug mode.
    """

    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}",    # .env.development or .env.production
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "MeetingMind"
    debug: bool = False
```

### Field Validation

Apply constraints and validators exactly as with regular Pydantic models:

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings.

    Attributes:
        port: Server port (1024–65535).
        log_level: Logging level name (DEBUG, INFO, etc.).
        workers: Number of worker processes.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    port: int = Field(default=8000, ge=1024, le=65535)
    log_level: str = Field(default="INFO")
    workers: int = Field(default=4, ge=1, le=32)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a known Python logging level."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()
```

### Singleton Pattern

Instantiate settings **once at module level** and import the instance everywhere:

```python
# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings singleton.

    Attributes:
        app_name: Application name.
        debug: Enable debug mode.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "MeetingMind"
    debug: bool = False


# Single instance — import this everywhere
settings = Settings()
```

```python
# src/services/my_service.py
from src.config import settings          # ✅ import the singleton

def process():
    if settings.debug:
        print("Debug mode active")
```

**Never import the `Settings` class and instantiate it in multiple places** — you'll get inconsistent values and `.env` read overhead.

### Testing — Override Settings

Use `model_validate` or environment variable patching to override settings in tests:

```python
import pytest
from unittest.mock import patch


@pytest.fixture
def test_settings():
    """Provide test settings with safe defaults."""
    with patch.dict("os.environ", {
        "APP_DEBUG": "true",
        "APP_DATABASE_URL": "sqlite:///:memory:",
        "APP_API_KEY": "test-key",
    }):
        from src.config import Settings
        yield Settings()        # fresh instance with test env


def test_debug_mode(test_settings):
    assert test_settings.debug is True
```

### `.env.example` — Always Provide a Template

Every project **MUST** include `.env.example` committed to version control:

```bash
# .env.example — copy to .env and fill in your values
# Never commit the real .env file

# Application
APP_NAME=MeetingMind
APP_DEBUG=false

# Database
APP_DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# API Keys (required)
APP_API_KEY=your-api-key-here
```

Add `.env` to `.gitignore`, never `.env.example`:
```gitignore
.env
.env.local
.env.*.local
# .env.example  ← do NOT ignore this
```

### Rules

- ✅ Always use `pydantic-settings` — never read `os.environ` directly
- ✅ Use `env_prefix` to namespace all variables
- ✅ Use `SecretStr` for API keys, passwords, and tokens
- ✅ Use `SettingsConfigDict` (V2) — never `class Config:` (V1)
- ✅ Instantiate `settings` once at module level and import the instance
- ✅ Provide a `.env.example` committed to version control
- ✅ Add `.env` to `.gitignore`
- ✅ Use `Field(ge=..., le=...)` for numeric bounds
- ✅ Use `@field_validator` for custom validation
- ❌ Never use `os.environ["KEY"]` — bypasses validation and defaults
- ❌ Never commit `.env` files with real secrets
- ❌ Never instantiate `Settings()` in multiple places

## Logging Setup

Configure structlog at startup:

```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger(__name__)
logger.info("server_started", port=8000)
```

## Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

request_count.labels(method='GET', endpoint='/api/v1/workflows', status='200').inc()
```

## Testing Standards

### Use Subtests for Multiple Assertions (PROJECT STANDARD)

**CRITICAL**: Always use `pytest.subtest()` for multiple independent assertions.

```python
import pytest

def test_user_fields():
    user = create_user("alice", "alice@example.com", age=25)

    # ✅ CORRECT: Use subtests
    with pytest.subtest("username"):
        assert user.username == "alice"

    with pytest.subtest("email"):
        assert user.email == "alice@example.com"

    with pytest.subtest("age"):
        assert user.age == 25

# ❌ WRONG: Sequential assertions (first failure stops test)
def test_user_fields_wrong():
    user = create_user("alice", "alice@example.com", age=25)
    assert user.username == "alice"  # If this fails, others don't run
    assert user.email == "alice@example.com"
    assert user.age == 25
```

**Benefits:**
- All assertions execute even if one fails
- See all failures at once, not just the first
- Better debugging with clear failure messages

For complete guidance, see `pytest.instructions.md`.

## Development Workflow

> 📖 **Official UV CLI Reference**: https://docs.astral.sh/uv/reference/cli/

> ⛔ **NEVER run Python directly. ALWAYS use `make` commands (first) or `uv` commands (fallback).**
> Running `python`, `python3`, `python -m`, bare `pytest`, bare `ruff`, or bare `mypy` directly is PROHIBITED.

### Core Principle: Always Use UV

**CRITICAL**: ALL Python commands MUST be run through `uv`. Never use bare `python`, `pip`, or tool executables directly.

| ❌ NEVER USE | ✅ ALWAYS USE | Purpose |
|---|---|---|
| `python script.py` | `make run` or `uv run python script.py` | Running scripts |
| `python3 script.py` | `make run` or `uv run python script.py` | Running scripts |
| `python -m pytest` | `make test` or `uv run pytest` | Running tests |
| `python -m ruff` | `make lint` or `uv run ruff check .` | Linting |
| `python -m mypy` | `uv run mypy .` | Type checking |
| `pytest` | `make test` or `uv run pytest` | Running tests |
| `ruff check .` | `make lint` or `uv run ruff check .` | Linting |
| `mypy .` | `uv run mypy .` | Type checking |
| `pip install package` | `uv add package` | Adding a dependency |
| `pip install -e ".[dev]"` | `uv sync` | Installing all project dependencies |
| `uvicorn app:main` | `uv run uvicorn app:main` | Running the server |
| `celery worker` | `uv run celery worker` | Running workers |

### Command Priority: Makefile First, UV Second

**CRITICAL: NEVER run `python` directly. The command priority is:**
1. **ALWAYS FIRST: `make <command>`** — Use Makefile targets whenever available
2. **SECOND: `uv run <command>`** — If no Make target exists, wrap with `uv run`
3. **⛔ NEVER: Direct execution** — `python`, `python3`, `python -m`, bare tool names are PROHIBITED

**Why?**
- Make commands are pre-configured with correct flags and environment
- UV ensures correct Python version and dependency isolation
- Direct execution may use wrong Python version or missing dependencies

### Package Management (uv)

Reference: https://docs.astral.sh/uv/reference/cli/#uv-add

```bash
# Project setup
uv init                          # Initialize a new project (not needed for existing projects)
uv sync                          # Install all dependencies (updates lockfile if needed)
uv sync --frozen                 # Install without updating lockfile (use in CI/CD, production)
uv sync --no-dev                 # Install only production dependencies
uv lock                          # Update the lockfile without installing
uv lock --upgrade                # Upgrade all dependencies

# Adding dependencies
uv add package-name              # Add a runtime dependency
uv add "package>=1.0,<2.0"       # Add with version constraint
uv add --dev package-name        # Add a development dependency

# Removing dependencies
uv remove package-name           # Remove a dependency
uv remove --dev package-name     # Remove a dev dependency

# Upgrading a specific package
uv lock --upgrade-package name   # Upgrade a specific package, then uv sync
```

### Python Version Management

Reference: https://docs.astral.sh/uv/reference/cli/#uv-python

```bash
uv python list                   # List available Python versions
uv python install 3.11           # Install a specific Python version
uv python install 3.12           # Install Python 3.12
uv python pin 3.11               # Pin project to a Python version
uv python find                   # Find the current Python interpreter
```

### Running Commands

Reference: https://docs.astral.sh/uv/reference/cli/#uv-run

```bash
# Run any command in the project's virtual environment
uv run python script.py          # Run a Python script
uv run python -c "import sys; print(sys.version)"  # Run inline code
uv run <tool> [args]             # Run any installed tool (pytest, ruff, mypy, etc.)
```

### Testing

> See `pytest.instructions.md` for the complete testing guide including fixtures, mocking, parametrization, and subtests.

```bash
# ✅ PREFERRED: Use Make command
make test                        # Run all tests
make tests                       # Alias for make test

# ✅ ACCEPTABLE: Use UV if Make command doesn't exist
uv run pytest                    # Run all tests
uv run pytest tests/unit/        # Run specific directory
uv run pytest -k "test_user"     # Run tests matching pattern
uv run pytest -v                 # Verbose output
uv run pytest -x                 # Stop on first failure
uv run pytest --cov              # With coverage

# ❌ NEVER USE (PROHIBITED):
pytest                           # ❌ PROHIBITED — missing UV isolation
python -m pytest tests/api/test_users.py -v  # ❌ PROHIBITED — wrong Python version
python -m pytest                 # ❌ PROHIBITED
python pytest                    # ❌ PROHIBITED
```

### Code Quality

**CRITICAL: Always format code before committing.**

```bash
# ✅ OPTION 1: Run pre-commit (PREFERRED - runs all checks)
pre-commit run --all-files

# ✅ OPTION 2: Run tools via UV (if no Make command exists)
uv run ruff format .             # Format code
uv run ruff check --fix .        # Fix linting issues
uv run mypy .                    # Type checking

# ✅ OPTION 3: Use Make commands
make lint                        # Run linter (ruff check)
make format                      # Format code (ruff format + ruff check --fix)

# ❌ NEVER USE (PROHIBITED):
ruff check .                     # ❌ PROHIBITED — missing UV isolation
mypy .                           # ❌ PROHIBITED — missing UV isolation
python -m ruff                   # ❌ PROHIBITED — wrong Python version
python -m mypy                   # ❌ PROHIBITED — wrong Python version
```

**Formatting Rules:**
- Run formatting BEFORE committing (not after)
- Pre-commit runs automatically on `git commit` if hooks are installed
- Fix all issues before pushing
- Never push unformatted code

### Running Application

```bash
# ✅ PREFERRED: Use Make command
make run                         # Run the application watcher

# ✅ ACCEPTABLE: Use UV if Make command doesn't exist
uv run uvicorn app.main:app --reload   # Start FastAPI server
uv run celery -A app.workers worker    # Start Celery worker
uv run meetingmind watch               # Run the MeetingMind watcher

# ❌ NEVER USE (PROHIBITED):
uvicorn app.main:app             # ❌ PROHIBITED — missing UV isolation
python -m uvicorn                # ❌ PROHIBITED — wrong Python version
celery worker                    # ❌ PROHIBITED — missing UV isolation
python -m celery                 # ❌ PROHIBITED — wrong Python version
```

### Tools (Global CLI Tools)

Reference: https://docs.astral.sh/uv/reference/cli/#uv-tool

Use `uv tool` to install standalone CLI tools globally (outside any project):

```bash
uv tool install ruff             # Install ruff globally
uv tool install mypy             # Install mypy globally
uv tool run ruff check .         # Run a tool without installing permanently
uv tool list                     # List installed tools
uv tool upgrade ruff             # Upgrade a tool
uv tool uninstall ruff           # Uninstall a tool
```

> **Note**: Prefer `uv run <tool>` inside a project (uses the project's pinned version). Use `uv tool` only for system-wide CLI tools.

### Virtual Environments

Reference: https://docs.astral.sh/uv/reference/cli/#uv-venv

```bash
uv venv                          # Create .venv in the current directory
uv venv --python 3.11            # Create venv with a specific Python version
```

> **Note**: UV manages the virtual environment automatically when you run `uv sync` or `uv run`. Manual `uv venv` is rarely needed.

### Cache Management

Reference: https://docs.astral.sh/uv/reference/cli/#uv-cache

```bash
uv cache clean                   # Clear the entire UV cache
uv cache prune                   # Remove outdated cache entries (keeps recent versions)
uv cache dir                     # Show the cache directory path
```

**When to use cache commands:**
- Fixing "package not found" or unexpected resolution errors
- After upgrading UV itself
- Freeing disk space on CI runners

### Upgrading UV

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via uv itself (if already installed)
uv self update
```

## Pre-commit Hooks

Configured hooks:
1. Trailing whitespace removal
2. End of file fixer
3. YAML validation
4. Python AST check
5. Docstring first check
6. Debug statement check
7. Ruff check (with auto-fix)
8. Ruff format
9. uv lock
10. mypy type checking
11. Commitizen (commit message validation)

## Commit Messages

Format: `<type>(<scope>): <subject>`

**Types:** feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert

**Examples:**
```
feat(api): add workflow deletion endpoint
fix(auth): resolve token expiration issue
docs(readme): update installation steps
refactor(services): extract common validation logic
```

## Best Practices Summary

1. **Type hints everywhere** - All public functions and methods
2. **Pydantic for validation** - Use models for data validation
3. **Structured logging** - Use structlog with context
4. **Context managers** - Always for files and resources
5. **Specific exceptions** - Never bare except
6. **Early returns** - Avoid deep nesting
7. **Small functions** - One responsibility per function
8. **Immutable defaults** - Never mutable default arguments
9. **Properties wisely** - Only for trivial operations
10. **Test coverage** - Maintain ≥80% coverage
11. **Direct attributes** - No Java-style getters/setters
12. **Import full modules** - Not individual classes (except types)
13. **No relative imports** - Use full package paths
14. **Async for I/O** - Use async/await for I/O operations
15. **No mutable globals** - Use classes or constants

## Zen of Python

Beautiful is better than ugly. Explicit is better than implicit. Simple is better than complex. Flat is better than nested. Readability counts.
