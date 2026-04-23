# Create API Endpoint Prompt

Use this prompt to create new WebAPI endpoints following project patterns.

## Prompt

```
Create a new API endpoint for [FEATURE]:

Endpoint Specification:
- Method: GET / POST / PUT / DELETE / PATCH
- Path: /[resource]/[action]
- Purpose: [What this endpoint does]
- Authentication: Required / Not Required
- Rate Limit: [requests per minute]

**CRITICAL: If this is a GET list endpoint (e.g., GET /resources/), you MUST implement pagination!**

Implementation Steps:

1. **Define Schemas** (src/sidiap_azure_devops_agent/schemas/)
```python
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")

# REQUIRED: Pagination schema for ALL list endpoints
class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

class CreateResourceRequest(BaseModel):
    """Request schema for creating a resource."""

    name: str = Field(..., min_length=1, max_length=100, description="Resource name")
    description: str | None = Field(None, max_length=500, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Resource",
                "description": "A sample resource"
            }
        }

class ResourceResponse(BaseModel):
    """Response schema for resource data."""

    id: str = Field(..., description="Resource identifier")
    name: str = Field(..., description="Resource name")
    status: str = Field(..., description="Resource status")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
```

2. **Create Service Method** (src/sidiap_azure_devops_agent/services/)
```python
from sidiap_azure_devops_agent.schemas.requests import CreateResourceRequest
from sidiap_azure_devops_agent.schemas.responses import ResourceResponse
import structlog

logger = structlog.get_logger(__name__)

class ResourceService:
    """Service for resource management."""

    def __init__(self, repository: ResourceRepository) -> None:
        """Initialize service with repository."""
        self._repository = repository

    async def create_resource(
        self,
        request: CreateResourceRequest
    ) -> ResourceResponse:
        """Create a new resource.

        Args:
            request: Resource creation request data.

        Returns:
            Created resource data.

        Raises:
            ResourceExistsError: If resource already exists.
            ValidationError: If request data is invalid.
        """
        logger.info(
            "Creating resource",
            resource_name=request.name
        )

        # Business logic here
        resource = await self._repository.create(request)

        logger.info(
            "Resource created successfully",
            resource_id=resource.id
        )

        return ResourceResponse(
            id=resource.id,
            name=resource.name,
            status="active",
            created_at=resource.created_at.isoformat()
        )
```

3. **Create API Endpoint** (src/sidiap_azure_devops_agent/api/)
```python
from web_api import APIRouter, Depends, status
from web_api.responses import JSONResponse
from sidiap_azure_devops_agent.schemas.requests import CreateResourceRequest
from sidiap_azure_devops_agent.schemas.responses import ResourceResponse
from sidiap_azure_devops_agent.services.resource_service import ResourceService
from sidiap_azure_devops_agent.api.dependencies import get_resource_service
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/resources", tags=["resources"])

@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new resource",
    description="Create a resource with the provided data",
    responses={
        201: {
            "description": "Resource created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "res-123",
                        "name": "My Resource",
                        "status": "active",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request data"},
        409: {"description": "Resource already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def create_resource(
    request: CreateResourceRequest,
    service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    """Create a new resource endpoint."""
    try:
        logger.info("Received create resource request", resource_name=request.name)
        result = await service.create_resource(request)
        return result

    except ResourceExistsError as e:
        logger.warning("Resource already exists", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except ValidationError as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error("Unexpected error creating resource", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create resource"
        )

# ✅ REQUIRED: List endpoint WITH pagination (default: 50 items)
@router.get(
    "",
    response_model=PaginatedResponse[ResourceResponse],
    summary="List all resources",
    description="Get a paginated list of resources",
)
async def list_resources(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page (default: 50, max: 100)"),
    service: ResourceService = Depends(get_resource_service),
) -> PaginatedResponse[ResourceResponse]:
    """List resources with pagination."""
    resources, total = await service.list_resources(
        skip=(page - 1) * page_size,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=resources,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

# ❌ WRONG: List endpoint WITHOUT pagination - NEVER DO THIS
# @router.get("", response_model=list[ResourceResponse])
# async def list_resources() -> list[ResourceResponse]:
#     return await service.get_all()  # BAD - unbounded list!
```

4. **Register Router** (src/sidiap_azure_devops_agent/main.py)
```python
from sidiap_azure_devops_agent.api import resources

app.include_router(resources.router)
```

5. **Write Tests** (tests/integration/api/)
```python
import pytest
from httpx import AsyncClient
from web_api import status

@pytest.mark.asyncio
async def test_create_resource_success(client: AsyncClient):
    """Test creating resource with valid data."""
    response = await client.post(
        "/resources",
        json={"name": "Test Resource", "description": "Test"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Resource"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_resource_duplicate(client: AsyncClient):
    """Test creating duplicate resource returns 409."""
    # Create first resource
    await client.post("/resources", json={"name": "Test"})

    # Try to create duplicate
    response = await client.post("/resources", json={"name": "Test"})

    assert response.status_code == status.HTTP_409_CONFLICT

@pytest.mark.asyncio
async def test_create_resource_invalid_data(client: AsyncClient):
    """Test creating resource with invalid data returns 422."""
    response = await client.post(
        "/resources",
        json={"name": ""}  # Empty name
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

Requirements Checklist:
- [ ] Pydantic schemas with validation
- [ ] OpenAPI documentation complete
- [ ] Async/await used correctly
- [ ] Dependency injection for services
- [ ] Proper HTTP status codes
- [ ] Error handling with try/except
- [ ] Structlog logging with context
- [ ] Type hints on all signatures
- [ ] Integration tests written
- [ ] API documented in OpenAPI
```

## Example Usage

```
Create a new API endpoint for workflow submission:

Method: POST
Path: /workflows/{workflow_id}/submit
Purpose: Submit a workflow for processing
Authentication: Required
Rate Limit: 10 requests per minute

[... rest of prompt ...]
```

## Related
- Agent: @senior-software-engineer-implementation
- Instructions: api.instructions.md, python.instructions.md, pytest.instructions.md
