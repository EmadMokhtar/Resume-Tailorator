# Add Monitoring Prompt

Use this prompt to add observability and monitoring to components.

## Prompt

```
Add monitoring and observability to [COMPONENT]:

Observability Stack (Project):
- **OpenTelemetry**: Distributed tracing
- **Jaeger**: Trace visualization (http://localhost:16686)
- **Prometheus**: Metrics collection
- **Structlog**: Structured logging

Implementation Steps:

1. **Distributed Tracing (OpenTelemetry)**
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.web_api import APIInstrumentor
import structlog

logger = structlog.get_logger(__name__)

# Configure OpenTelemetry
def configure_tracing(app):
    """Configure OpenTelemetry tracing."""
    if not settings.observability.otlp_enabled:
        logger.info("OTLP tracing disabled")
        return

    provider = TracerProvider()
    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=settings.observability.otlp_endpoint,
            insecure=True  # Use TLS in production
        )
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument WebAPI
    APIInstrumentor.instrument_app(app)

    logger.info(
        "OpenTelemetry tracing configured",
        endpoint=settings.observability.otlp_endpoint
    )

# Use in service
tracer = trace.get_tracer(__name__)

async def process_workflow(workflow_id: str) -> WorkflowResult:
    """Process workflow with tracing."""
    with tracer.start_as_current_span("process_workflow") as span:
        span.set_attribute("workflow.id", workflow_id)

        try:
            logger.info("Processing workflow", workflow_id=workflow_id)

            # Business logic with child spans
            with tracer.start_as_current_span("fetch_workflow"):
                workflow = await self._repository.get(workflow_id)
                span.set_attribute("workflow.status", workflow.status)

            with tracer.start_as_current_span("execute_workflow"):
                result = await self._execute(workflow)
                span.set_attribute("workflow.result", result.status)

            span.set_attribute("workflow.success", True)
            return result

        except Exception as e:
            span.set_attribute("workflow.success", False)
            span.set_attribute("error", str(e))
            logger.error("Workflow processing failed", error=str(e))
            raise
```

2. **Prometheus Metrics**
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
workflow_counter = Counter(
    'workflow_processed_total',
    'Total number of workflows processed',
    ['status']
)

workflow_duration = Histogram(
    'workflow_processing_duration_seconds',
    'Time spent processing workflows',
    ['workflow_type']
)

active_workflows = Gauge(
    'workflow_active_count',
    'Number of workflows currently being processed'
)

# Use in service
async def process_workflow(workflow_id: str) -> WorkflowResult:
    """Process workflow with metrics."""
    active_workflows.inc()
    start_time = time.time()

    try:
        result = await self._execute(workflow_id)
        workflow_counter.labels(status='success').inc()
        return result

    except Exception as e:
        workflow_counter.labels(status='error').inc()
        raise

    finally:
        duration = time.time() - start_time
        workflow_duration.labels(workflow_type='standard').observe(duration)
        active_workflows.dec()

# Expose metrics endpoint
from web_api import WebAPI
from prometheus_client import make_asgi_app

app = WebAPI()
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

3. **Structured Logging (Structlog)**
```python
import structlog
from pythonjsonlogger import jsonlogger

# Configure structlog
def configure_logging():
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Use in service
logger = structlog.get_logger(__name__)

async def process_workflow(workflow_id: str) -> WorkflowResult:
    """Process workflow with structured logging."""
    logger.info(
        "Workflow processing started",
        workflow_id=workflow_id,
        user_id=current_user.id,
        timestamp=datetime.utcnow().isoformat()
    )

    try:
        result = await self._execute(workflow_id)

        logger.info(
            "Workflow processing completed",
            workflow_id=workflow_id,
            status=result.status,
            duration_ms=result.duration_ms
        )

        return result

    except Exception as e:
        logger.error(
            "Workflow processing failed",
            workflow_id=workflow_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

4. **Health Check Endpoint**
```python
from web_api import APIRouter, status
from pydantic import BaseModel

router = APIRouter()

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    dependencies: dict[str, str]

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    tags=["system"]
)
async def health_check() -> HealthResponse:
    """Check application health and dependencies."""
    dependencies = {
        "database": "healthy",
        "redis": "healthy",
        "jaeger": "healthy"
    }

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        dependencies=dependencies
    )

@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness() -> dict:
    """Liveness probe."""
    return {"status": "alive"}

@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness() -> dict:
    """Readiness probe."""
    # Check dependencies are ready
    return {"status": "ready"}
```

5. **docker-compose Configuration**
```yaml
services:
  app:
    environment:
      OBSERVABILITY__OTLP_ENABLED: true
      OBSERVABILITY__OTLP_ENDPOINT: http://jaeger:4317
      LOG_LEVEL: INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  jaeger:
    container_name: sidiap_azure_devops_agent-jaeger
    image: nn-docker-remote.artifactory.insim.biz/jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

Monitoring Checklist:
- [ ] OpenTelemetry tracing configured
- [ ] Jaeger connected and traces visible
- [ ] Prometheus metrics exposed at /metrics
- [ ] Structured logging with context
- [ ] Health check endpoints implemented
- [ ] Error tracking with span attributes
- [ ] Performance metrics collected
- [ ] Distributed tracing across services
- [ ] Log correlation with trace IDs
- [ ] Alerts configured for errors

Verification:
```bash
# Start services
make docker/compose-up

# Check health
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics

# Open Jaeger UI
open http://localhost:16686

# View logs
docker compose logs -f app
```
```

## Example Usage

```
Add monitoring and observability to src/sidiap_azure_devops_agent/services/workflows_service.py
[... rest of prompt ...]
```

## Related
- Agent: @senior-devops-engineer
- Instructions: docker.instructions.md, python.instructions.md, api.instructions.md
