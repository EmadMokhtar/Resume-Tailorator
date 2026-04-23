# Write Documentation Prompt

Use this prompt to create comprehensive project documentation.

## Prompt

```
Write documentation for [MODULE/FEATURE/API]:

Documentation Types:
1. **API Documentation** (OpenAPI/Swagger)
   - Endpoint descriptions
   - Request/response examples
   - Status codes
   - Error responses
   - Authentication requirements

2. **Code Documentation** (Docstrings)
   - Google-style docstrings
   - Function/class purpose
   - Parameters with types
   - Return values
   - Exceptions raised
   - Usage examples

3. **User Documentation** (README/Guides)
   - Feature overview
   - Getting started
   - Configuration
   - Usage examples
   - Troubleshooting

4. **Developer Documentation** (Architecture)
   - System architecture
   - Design decisions
   - Module structure
   - Data flow
   - Integration points

Docstring Template (Google Style):
```python
def process_workflow(
    workflow_id: str,
    options: WorkflowOptions | None = None,
) -> WorkflowResult:
    """Process a workflow with the given options.

    This function orchestrates the workflow processing pipeline,
    including validation, execution, and result collection.

    Args:
        workflow_id: Unique identifier for the workflow to process.
        options: Optional configuration for workflow processing.
            Defaults to standard options if not provided.

    Returns:
        WorkflowResult containing the processing outcome and metadata.

    Raises:
        WorkflowNotFoundError: If workflow_id doesn't exist.
        ValidationError: If workflow data is invalid.
        ProcessingError: If workflow execution fails.

    Example:
        >>> result = process_workflow(
        ...     workflow_id="wf-123",
        ...     options=WorkflowOptions(timeout=30)
        ... )
        >>> print(result.status)
        'completed'

    Note:
        This operation is idempotent. Reprocessing a completed
        workflow will return cached results.
    """
```

API Endpoint Documentation:
```python
@router.post(
    "/workflows/{workflow_id}/process",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Process a workflow",
    description="Execute workflow processing with optional configuration",
    responses={
        200: {
            "description": "Workflow processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "workflow_id": "wf-123",
                        "status": "completed",
                        "result": {"score": 0.95}
                    }
                }
            }
        },
        404: {
            "description": "Workflow not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Workflow wf-123 not found"
                    }
                }
            }
        },
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    },
    tags=["workflows"]
)
async def process_workflow_endpoint(
    workflow_id: str,
    request: ProcessWorkflowRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowResponse:
    """Process a workflow endpoint handler."""
```

README Template:
```markdown
# [Feature Name]

## Overview
Brief description of what this feature does and why it exists.

## Prerequisites
- Python 3.12+
- uv installed
- Docker (optional)

## Installation
\`\`\`bash
make install/dev
\`\`\`

## Configuration
Required environment variables:
- `VAR_NAME`: Description
- `ANOTHER_VAR`: Description

## Usage

### Basic Example
\`\`\`python
from sidiap_azure_devops_agent.services import WorkflowService

service = WorkflowService()
result = await service.process("wf-123")
print(result.status)
\`\`\`

### Advanced Example
\`\`\`python
options = WorkflowOptions(timeout=60, retries=3)
result = await service.process("wf-123", options=options)
\`\`\`

## API Endpoints

### POST /workflows/{workflow_id}/process
Process a workflow.

**Request:**
\`\`\`json
{
  "options": {
    "timeout": 30
  }
}
\`\`\`

**Response:**
\`\`\`json
{
  "workflow_id": "wf-123",
  "status": "completed"
}
\`\`\`

## Testing
\`\`\`bash
make tests
\`\`\`

## Troubleshooting

### Issue: Workflow processing times out
**Solution**: Increase timeout in options

### Issue: Authentication fails
**Solution**: Verify credentials in .env

## Further Reading
- [Architecture Documentation](docs/architecture.md)
- [API Reference](docs/api.md)
```

Documentation Checklist:
- [ ] All public functions have docstrings
- [ ] API endpoints documented in OpenAPI
- [ ] Examples are working and tested
- [ ] Error cases documented
- [ ] Configuration options explained
- [ ] Prerequisites listed
- [ ] Troubleshooting section included
- [ ] Links to related docs
```

## Example Usage

```
Write documentation for src/sidiap_azure_devops_agent/api/workflows.py:
[... rest of prompt ...]
```

## Related
- Agent: @technical-writer
- Instructions: python.instructions.md, api.instructions.md
