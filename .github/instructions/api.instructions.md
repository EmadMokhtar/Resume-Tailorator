# WebAPI Development Instructions

**Applies to:** `**/*router*.py`, `**/*api*.py`, `**/main.py`, `**/schemas.py`, `**/models.py`, `**/service*.py`, `**/dependencies.py`

## Ruff WebAPI Rules (REQUIRED)

**These rules are enforced by the linter. Follow them strictly.**

### Recommended Ruff Configuration for WebAPI

```toml
# pyproject.toml - Add these to your lint.select
[tool.ruff]
line-length = 120
lint.select = [
    # ... base rules from python.instructions.md ...
    "FAST",   # WebAPI-specific rules (CRITICAL)
    "ASYNC",  # Async/await best practices (CRITICAL for WebAPI)
]
```

### FAST001: Redundant response_model

Don't duplicate the return type annotation in both the decorator and function signature.

```python
# ❌ WRONG: Redundant response_model
@router.get("/users/{id}", response_model=UserResponse)
async def get_user(id: str) -> UserResponse:  # Duplicate!
    return await service.get_user(id)

# ✅ CORRECT: Return type annotation only
@router.get("/users/{id}")
async def get_user(id: str) -> UserResponse:
    return await service.get_user(id)
```

### FAST002: Use Annotated for Dependencies

Use `Annotated` type hints for dependency injection instead of default arguments.

```python
from typing import Annotated
from web_api import Depends

# ❌ WRONG: Old-style dependency injection
@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    ...

# ✅ CORRECT: Modern Annotated style
DbSession = Annotated[Session, Depends(get_db)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

@router.get("/users")
async def list_users(db: DbSession, service: UserServiceDep):
    ...
```

### FAST003: Unused Path Parameters

Path parameters must be used in the function signature.

```python
# ❌ WRONG: Path parameter not in signature
@router.get("/users/{user_id}/orders/{order_id}")
async def get_order(order_id: str):  # Missing user_id!
    ...

# ✅ CORRECT: All path params in signature
@router.get("/users/{user_id}/orders/{order_id}")
async def get_order(user_id: str, order_id: str):
    ...
```

## Async Rules (ASYNC) - Critical for WebAPI

**Never use blocking calls in async functions!**

| Rule | Description |
|------|-------------|
| ASYNC100 | Cancel scope without await |
| ASYNC210 | Blocking HTTP call in async function |
| ASYNC230 | Blocking `open()` in async function |
| ASYNC251 | `time.sleep()` in async function |

```python
import asyncio
import httpx
import aiofiles

# ❌ WRONG: Blocking HTTP in async function (ASYNC210)
async def fetch_external_data(url: str):
    response = requests.get(url)  # Blocks event loop!
    return response.json()

# ✅ CORRECT: Use async HTTP client
async def fetch_external_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# ❌ WRONG: Blocking sleep (ASYNC251)
async def delayed_operation():
    time.sleep(5)  # Blocks event loop!
    await do_something()

# ✅ CORRECT: Use asyncio.sleep
async def delayed_operation():
    await asyncio.sleep(5)
    await do_something()

# ❌ WRONG: Blocking file I/O (ASYNC230)
async def read_config():
    with open("config.json") as f:  # Blocks!
        return json.load(f)

# ✅ CORRECT: Use aiofiles
async def read_config():
    async with aiofiles.open("config.json") as f:
        content = await f.read()
        return json.loads(content)
```

## B008 Exception for WebAPI Depends()

**Note:** Rule B008 (function call in default argument) has an exception for WebAPI's `Depends()`:

```python
# ✅ OK: WebAPI's Depends() is designed for this pattern
@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    ...

# ✅ BETTER: Use Annotated (FAST002 compliant)
DbSession = Annotated[Session, Depends(get_db)]

@router.get("/users")
async def list_users(db: DbSession):
    ...
```

## Project Structure

Organize by domain (feature), not file type.

```
src/
├── config/
│   └── settings.py                 # Application settings (Pydantic Settings)
├── sidiap_azure_devops_agent/                  # Main application package
│   ├── main.py                     # WebAPI app initialization
│   ├── config.py                   # Configuration loader
│   ├── log.py                      # Logging setup (structlog)
│   ├── api/                        # API layer (HTTP endpoints)
│   │   ├── __init__.py
│   │   ├── health.py               # Health check endpoints
│   │   └── workflows.py            # Workflow endpoints
│   ├── schemas/                    # Pydantic models (request/response)
│   │   ├── __init__.py
│   │   ├── requests.py             # Request schemas
│   │   └── responses.py            # Response schemas
│   ├── models/                     # Domain models (business logic models)
│   │   ├── __init__.py
│   │   ├── workflow.py             # Workflow domain model
│   │   ├── analysis_result.py      # Analysis result model
│   │   ├── parsed_document.py      # Parsed document model
│   │   ├── review_feedback.py      # Review feedback model
│   │   ├── final_report.py         # Final report model
│   │   ├── file_input.py           # File input model
│   │   └── claims_handling_workflow.py  # Claims workflow model
│   ├── services/                   # Service layer (business logic)
│   │   ├── service_factory.py      # Service factory pattern
│   │   └── workflows_service.py    # Workflow service
│   ├── ports/                      # Port interfaces (Hexagonal Architecture)
│   │   └── workflows_repository.py # Repository interface (ABC)
│   ├── adapters/                   # Adapter implementations (data access)
│   │   └── dynamodb/
│   │       ├── __init__.py
│   │       ├── client.py           # DynamoDB client
│   │       ├── workflows_repository.py  # Repository implementation
│   │       └── models/             # DynamoDB-specific models
│   │           ├── __init__.py
│   │           ├── workflow_dynamodb_model.py
│   │           └── activity_dynamodb_model.py
│   ├── agents/                     # AI agents (LangChain/LLM)
│   │   ├── __init__.py
│   │   ├── get_model.py            # Model factory
│   │   ├── document_parser.py      # Document parsing agent
│   │   ├── content_analyzer.py     # Content analysis agent
│   │   ├── quality_reviewer.py     # Quality review agent
│   │   └── report_generator.py     # Report generation agent
│   └── workers/                    # Background workers (Celery)
│       ├── celery/                 # Celery configuration
│       └── activities/             # Celery task activities
│           └── analyze_and_review.py
├── tests/                          # Test suite (mirrors src structure)
│   ├── conftest.py                 # Shared fixtures
│   ├── api/                        # API tests
│   ├── services/                   # Service tests
│   ├── adapters/                   # Adapter tests
│   ├── models/                     # Model tests
│   └── workers/                    # Worker tests
```

**Key Architectural Patterns:**

- **Hexagonal Architecture (Ports & Adapters)**: Ports define interfaces, adapters implement them
- **Clean Architecture Layers**:
  - `api/` - Presentation layer (HTTP/REST)
  - `services/` - Application/business logic layer
  - `ports/` - Domain interfaces (abstract base classes)
  - `adapters/` - Infrastructure layer (DynamoDB, external services)
  - `models/` - Domain models (business entities)
  - `schemas/` - Data transfer objects (DTOs)
- **Dependency Direction**: api → services → ports ← adapters
- **Agents**: AI/LLM-based processing components
- **Workers**: Asynchronous task processing with Celery

**Import Convention:**

```python
from config.settings import Settings
from sidiap_azure_devops_agent.schemas import requests, responses
from sidiap_azure_devops_agent.models.workflow import Workflow
from sidiap_azure_devops_agent.services.workflows_service import WorkflowsService
from sidiap_azure_devops_agent.ports.workflows_repository import IWorkflowsRepository
from sidiap_azure_devops_agent.adapters.dynamodb.workflows_repository import DynamoDBWorkflowsRepository
from sidiap_azure_devops_agent.agents.document_parser import DocumentParserAgent
```

## SOLID Principles

### Single Responsibility Principle (SRP)
- Repository handles ALL database operations
- Service contains ALL business logic
- Router only handles HTTP concerns
- Easy to test each layer independently

```python
# repository.py
class UserRepository:
    """Repository for user data access.

    Attributes:
        db_session: Database session for queries.
    """

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address.

        Returns:
            User if found, None otherwise.
        """
        pass

    async def create(self, user_data: UserCreate) -> int:
        """Create a new user.

        Args:
            user_data: User creation data.

        Returns:
            The created user's ID.
        """
        pass


# service.py
class UserService:
    """Service for user business logic.

    Attributes:
        user_repository: Repository for user data access.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        """Initialize the user service.

        Args:
            user_repository: Repository for user persistence.
        """
        self.user_repository = user_repository

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with validation.

        Args:
            user_data: User creation data.

        Returns:
            The created user.

        Raises:
            UserAlreadyExistsError: If email already exists.
        """
        await self._validate_user_data(user_data)
        await self._check_user_exists(user_data.email)
        user_id = await self.user_repository.create(user_data)
        return await self.user_repository.get_by_id(user_id)


# router.py
@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(user: UserCreate, service: UserService = Depends(get_service)):
    return await service.create_user(user)
```

### Dependency Inversion Principle (DIP)
- Depend on abstractions (interfaces), not concrete implementations
- Use ABC for interfaces, concrete classes implement them

```python
from abc import ABC, abstractmethod


class IUserRepository(ABC):
    """Interface for user repository.

    Defines the contract for user data access operations.
    """

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address.

        Returns:
            User if found, None otherwise.
        """
        pass


class UserRepository(IUserRepository):
    """Concrete implementation of user repository.

    Attributes:
        db_session: Database session for queries.
    """

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: User's email address.

        Returns:
            User if found, None otherwise.
        """
        # Implementation
        pass


class UserService:
    """Service for user operations.

    Attributes:
        user_repository: Repository for user data access (abstraction).
    """

    def __init__(self, user_repository: IUserRepository) -> None:  # Depends on abstraction
        """Initialize the user service.

        Args:
            user_repository: Repository implementing IUserRepository.
        """
        self.user_repository = user_repository
```

## Design Patterns

### Repository Pattern
Encapsulates all data access logic.

```python
class UserRepository:
    """Repository for user data persistence.

    Attributes:
        db_session: Database session for executing queries.
    """

    def __init__(self, db_session) -> None:
        """Initialize the repository.

        Args:
            db_session: Database session instance.
        """
        self.db_session = db_session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User's unique identifier.

        Returns:
            User if found, None otherwise.
        """
        return await self.db_session.get(User, user_id)

    async def create(self, user_data: UserCreate) -> User:
        """Create a new user.

        Args:
            user_data: User creation data.

        Returns:
            The created user entity.
        """
        db_user = User(**user_data.model_dump())
        self.db_session.add(db_user)
        await self.db_session.commit()
        await self.db_session.refresh(db_user)
        return db_user
```

### Service Layer Pattern
Contains business logic, orchestrates operations.

```python
class UserService:
    """Service for user business operations.

    Orchestrates user creation with validation and notifications.

    Attributes:
        user_repository: Repository for user data access.
        email_service: Service for sending emails.
    """

    def __init__(
        self, user_repository: IUserRepository, email_service: IEmailService
    ) -> None:
        """Initialize the user service.

        Args:
            user_repository: Repository for user persistence.
            email_service: Service for email notifications.
        """
        self.user_repository = user_repository
        self.email_service = email_service

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user and send welcome email.

        Args:
            user_data: User creation data.

        Returns:
            The created user.

        Raises:
            UserAlreadyExistsError: If email already exists.
        """
        await self._validate_unique_email(user_data.email)
        user = await self.user_repository.create(user_data)
        await self.email_service.send_welcome_email(user.email)
        return user
```

## REST API Best Practices

### HTTP Verbs
| Verb | Purpose | Example |
|------|---------|---------|
| GET | Read | `GET /users` |
| POST | Create | `POST /users` |
| PUT | Full update | `PUT /users/{id}` |
| PATCH | Partial update | `PATCH /users/{id}` |
| DELETE | Remove | `DELETE /users/{id}` |

### Naming Conventions
```python
# ✅ Good - Plural nouns, lowercase
GET /users
GET /users/{user_id}
POST /users
GET /users/{user_id}/posts

# ❌ Bad
GET /getUsers
POST /createUser
```

### Status Codes
```python
from web_api import status

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    pass

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    pass
```

## Response Envelope Pattern (REQUIRED)

**CRITICAL: All API responses MUST use the standard envelope pattern.**

### Envelope Structure

All API responses are wrapped in a consistent envelope with:
- `success`: Boolean indicating request success
- `data`: The actual response payload (null on error)
- `meta`: Response metadata (timestamp, request_id, version)
- `errors`: List of errors (empty on success)

### Response Schemas

```python
from datetime import datetime, UTC
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata for API responses.

    Attributes:
        timestamp: When the response was generated (ISO 8601).
        request_id: Correlation ID for request tracing.
        version: API version.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str | None = None
    version: str = "1.0.0"


class ErrorDetail(BaseModel):
    """Details about an error.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable error message.
        field: Field that caused the error (for validation errors).
        details: Additional error context.
    """

    code: str
    message: str
    field: str | None = None
    details: dict | None = None


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    Attributes:
        success: Whether the request was successful.
        data: The response payload (null on error).
        meta: Response metadata.
        errors: List of errors (empty on success).
    """

    success: bool
    data: T | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    errors: list[ErrorDetail] = Field(default_factory=list)

    @classmethod
    def ok(cls, data: T, request_id: str | None = None) -> "APIResponse[T]":
        """Create a successful response."""
        return cls(success=True, data=data, meta=ResponseMeta(request_id=request_id))

    @classmethod
    def fail(cls, errors: list[ErrorDetail], request_id: str | None = None) -> "APIResponse[T]":
        """Create an error response."""
        return cls(success=False, errors=errors, meta=ResponseMeta(request_id=request_id))
```

### Usage in Endpoints

```python
from sidiap_azure_devops_agent.schemas.responses import APIResponse

@router.get("/users/{user_id}")
async def get_user(user_id: str, request: Request) -> APIResponse[UserResponse]:
    """Get user by ID.

    Args:
        user_id: User's unique identifier.
        request: WebAPI request object.

    Returns:
        APIResponse envelope containing UserResponse data.
    """
    request_id = getattr(request.state, "correlation_id", None)
    user = await service.get_user(user_id)
    return APIResponse.ok(data=user, request_id=request_id)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, request: Request) -> APIResponse[UserResponse]:
    """Create a new user.

    Args:
        user: User creation data.
        request: WebAPI request object.

    Returns:
        APIResponse envelope containing created UserResponse.
    """
    request_id = getattr(request.state, "correlation_id", None)
    created_user = await service.create_user(user)
    return APIResponse.ok(data=created_user, request_id=request_id)
```

### Response Examples

**Success Response:**
```json
{
    "success": true,
    "data": {
        "id": "123",
        "username": "alice",
        "email": "alice@example.com"
    },
    "meta": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "version": "1.0.0"
    },
    "errors": []
}
```

**Error Response:**
```json
{
    "success": false,
    "data": null,
    "meta": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "version": "1.0.0"
    },
    "errors": [
        {
            "code": "USER_NOT_FOUND",
            "message": "User with ID 123 not found",
            "field": null,
            "details": null
        }
    ]
}
```

### Envelope Rules

- ✅ All endpoints return `APIResponse[T]` wrapper
- ✅ Use `APIResponse.ok()` for successful responses
- ✅ Use `APIResponse.fail()` for error responses
- ✅ Include `request_id` from correlation middleware
- ✅ `meta.timestamp` is always UTC ISO 8601 format
- ❌ Never return raw data without envelope
- ❌ Never omit the `errors` field (use empty list)

## Pagination (REQUIRED for List Endpoints)

**CRITICAL: All list endpoints MUST implement pagination with 50 items as default.**

### Pagination Schema (with Envelope)

```python
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses.

    Attributes:
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        total_items: Total number of items.
        total_pages: Total number of pages.
        has_next: Whether there is a next page.
        has_previous: Whether there is a previous page.
    """

    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    has_next: bool
    has_previous: bool

    @classmethod
    def create(cls, page: int, page_size: int, total_items: int) -> "PaginationMeta":
        """Create pagination metadata from basic parameters."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response envelope.

    Attributes:
        success: Whether the request was successful.
        data: List of items for the current page.
        meta: Response metadata.
        pagination: Pagination metadata.
        errors: List of errors (empty on success).
    """

    success: bool = True
    data: list[T] = Field(default_factory=list)
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    pagination: PaginationMeta
    errors: list[ErrorDetail] = Field(default_factory=list)

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_items: int,
        request_id: str | None = None,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        return cls(
            data=items,
            meta=ResponseMeta(request_id=request_id),
            pagination=PaginationMeta.create(page, page_size, total_items),
        )
```

### List Endpoint Implementation

```python
from web_api import APIRouter, Query, Request

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
    service: UserService = Depends(get_user_service),
) -> PaginatedResponse[UserResponse]:
    """List all users with pagination.

    Args:
        request: WebAPI request object.
        page: Page number (default: 1).
        page_size: Items per page (default: 50, max: 100).
        service: User service dependency.

    Returns:
        PaginatedResponse envelope with list of users.
    """
    request_id = getattr(request.state, "correlation_id", None)
    users, total = await service.list_users(
        skip=(page - 1) * page_size,
        limit=page_size,
    )

    return PaginatedResponse.create(
        items=users,
        page=page,
        page_size=page_size,
        total_items=total,
        request_id=request_id,
    )
```

### Paginated Response Example

```json
{
    "success": true,
    "data": [
        {"id": "1", "username": "alice"},
        {"id": "2", "username": "bob"}
    ],
    "meta": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "version": "1.0.0"
    },
    "pagination": {
        "page": 1,
        "page_size": 50,
        "total_items": 150,
        "total_pages": 3,
        "has_next": true,
        "has_previous": false
    },
    "errors": []
}
```

### Pagination Rules

- ✅ Default page size: **50 items**
- ✅ Maximum page size: **100 items**
- ✅ Always return total count in pagination metadata
- ✅ Include `has_next` and `has_previous` flags
- ✅ Use `PaginatedResponse.create()` factory method
- ❌ Never return unbounded lists
- ❌ Never allow page_size > 100

## Route Definitions

### Router Setup
```python
from web_api import APIRouter, HTTPException, status, Depends

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User not found"}},
)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """Get user by ID."""
    user = await fetch_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    return user

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate) -> UserResponse:
    """Create a new user."""
    if await user_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {user.email} already exists"
        )
    return await create_user_in_db(user)
```

### Router Registration
```python
from web_api import WebAPI
from app.api import users, orders

app = WebAPI(title="My API", version="1.0.0")

# Register routers
app.include_router(users.router)
app.include_router(orders.router)

# Or with version prefix
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(users.router)
app.include_router(api_v1)
```

## Pydantic Best Practices

### Built-in Validators
```python
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(min_length=8)
    age: int = Field(ge=18, le=120)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        return v
```

### Request/Response Models
```python
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None

class UserRead(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### Settings
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "WebAPI App"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

settings = Settings()
```

## Dependency Injection

### Basic Usage
```python
from web_api import Depends

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await db.execute(select(User))
    return users.scalars().all()
```

### Validation Dependencies
```python
async def valid_user_id(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    """Validate user exists and return it."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user

@router.get("/users/{user_id}")
async def get_user(user: User = Depends(valid_user_id)):
    return user
```

### Chain Dependencies
```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = jwt.decode(token, SECRET_KEY)
    user = await db.get(User, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401)
    return user

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: User = Depends(get_current_admin_user)):
    await service.delete_user(user_id)
```

## Async/Await

### When to Use Async
```python
# ✅ Use async for I/O-bound operations
@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()

# ✅ Use sync for CPU-bound/blocking operations
@router.get("/compute")
def compute_result():
    return heavy_computation()  # Runs in threadpool automatically
```

### Avoid Blocking
```python
# ❌ BAD: Blocking call in async
@router.get("/bad")
async def bad():
    time.sleep(10)  # Blocks entire event loop!

# ✅ GOOD: Non-blocking async
@router.get("/good")
async def good():
    await asyncio.sleep(10)

# ✅ GOOD: Sync function for blocking
@router.get("/also-good")
def sync_endpoint():
    time.sleep(10)  # Runs in threadpool
```

### Using Sync Libraries
```python
from web_api.concurrency import run_in_threadpool
import requests

@router.get("/external")
async def call_external_api():
    response = await run_in_threadpool(
        requests.get,
        "https://api.example.com/data"
    )
    return response.json()
```

## Error Handling

### Domain-Specific Exceptions
Don't use HTTPException in business logic.

```python
# exceptions.py
class AppException(Exception):
    """Base exception for application errors.

    Attributes:
        message: Error description.
    """

    pass


class UserNotFoundError(AppException):
    """Raised when a user cannot be found.

    Attributes:
        user_id: The ID of the user that was not found.
    """

    pass


class UserAlreadyExistsError(AppException):
    """Raised when attempting to create a user that already exists.

    Attributes:
        email: The email address that already exists.
    """

    pass


# service.py
class UserService:
    """Service for user operations.

    Attributes:
        repository: User data repository.
    """

    async def create_user(self, user_data: UserCreate) -> User:
        existing = await self.repository.get_by_email(user_data.email)
        if existing:
            raise UserAlreadyExistsError(f"Email {user_data.email} already exists")
        return await self.repository.create(user_data)
```

### Global Exception Handlers
Map domain exceptions to HTTP responses.

```python
from web_api import WebAPI, Request
from web_api.responses import JSONResponse

app = WebAPI()

@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc), "error_code": "USER_NOT_FOUND"}
    )

@app.exception_handler(UserAlreadyExistsError)
async def user_exists_handler(request: Request, exc: UserAlreadyExistsError):
    return JSONResponse(
        status_code=409,
        content={"message": str(exc), "error_code": "USER_ALREADY_EXISTS"}
    )
```

## Testing

### Async Test Client
```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/users",
        json={"username": "testuser", "email": "test@example.com", "password": "Pass123"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
```

### Override Dependencies
```python
@pytest.fixture
async def client():
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

### Parametrized Tests
```python
@pytest.mark.parametrize(
    "user_data,expected_status",
    [
        ({"username": "valid", "email": "test@example.com", "password": "Pass123"}, 201),
        ({"username": "a", "email": "test@example.com", "password": "Pass123"}, 422),
        ({"username": "valid", "email": "invalid", "password": "Pass123"}, 422),
    ],
)
@pytest.mark.asyncio
async def test_user_creation(client: AsyncClient, user_data: dict, expected_status: int):
    response = await client.post("/users", json=user_data)
    assert response.status_code == expected_status
```

## Quick Reference

| Scenario | Solution |
|----------|---------|
| Structure | Domain-based (auth/, users/, posts/) |
| Data access | Repository pattern (DAO) |
| Business logic | Service layer |
| Abstractions | Interface classes (ABC) |
| Non-blocking I/O | `async def` with `await` |
| Blocking I/O | `def` (sync route) |
| Sync lib in async | `run_in_threadpool()` |
| Validation | Pydantic models + Dependencies |
| Error handling | Domain exceptions + handlers |
| Testing | AsyncClient with dependency overrides |

## Best Practices Summary

### Architecture
- ✅ Organize by domain, not file type
- ✅ Use Repository pattern for data access
- ✅ Use Service layer for business logic
- ✅ Depend on interfaces (ABC), not implementations
- ✅ Keep routers thin - delegate to services
- ✅ Use dependency injection everywhere

### Pydantic
- ✅ Use built-in validators (EmailStr, Field)
- ✅ Separate models: Create, Update, Read, Internal
- ✅ Add examples for documentation

### Dependencies
- ✅ Use for validation, not just DI
- ✅ Chain dependencies for complex checks
- ✅ Remember dependencies are cached per request

### Async
- ✅ Use `async def` only with `await`
- ✅ Use `def` for blocking operations
- ✅ Wrap sync libraries with `run_in_threadpool()`
- ✅ Never block the event loop

### Error Handling
- ✅ Create domain-specific exceptions
- ✅ Use global exception handlers
- ✅ Don't use HTTPException in business logic

### Testing
- ✅ Use AsyncClient for integration tests
- ✅ Override dependencies with test doubles
- ✅ Mock external dependencies only
