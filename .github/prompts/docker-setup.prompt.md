# Docker Setup Prompt

Use this prompt to create or modify Docker configurations.

## Prompt

```
Create/modify Docker configuration for [COMPONENT]:

Project Docker Patterns:
- Artifactory registry: nn-docker-remote.artifactory.insim.biz
- Make commands: make install/docker, make ${RUN_TARGET}
- ARG RUN_TARGET: Flexible app/worker deployment
- Single-stage inheritance: builder AS runtime
- Observability: Jaeger + OpenTelemetry

Dockerfile Template:
```dockerfile
# Builder stage - install tools
FROM nn-docker-remote.artifactory.insim.biz/python:3.12-slim AS builder
RUN apt-get update && apt-get install -y make curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.artifactory.insim.biz/astral-sh/uv:latest /uv /uvx /bin/

# Runtime stage
FROM builder AS runtime
EXPOSE [PORT]

# Create non-root user and group
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

WORKDIR /api
COPY . ./[project-name]
WORKDIR /api/[project-name]

# Install dependencies using Make
RUN --mount=type=secret,id=artifactory_username \
    --mount=type=secret,id=artifactory_password \
    export UV_INDEX_ARTIFACTORY_USERNAME=$(cat /run/secrets/artifactory_username) && \
    export UV_INDEX_ARTIFACTORY_PASSWORD=$(cat /run/secrets/artifactory_password) && \
    make install/docker

# Parameterize run command
ARG RUN_TARGET=run
ENV RUN_TARGET=${RUN_TARGET}

# Create cache directory with proper permissions
RUN mkdir -p /api/[project-name]/.cache && \
    chown -R appuser:appuser /api

ENV UV_CACHE_DIR=/api/[project-name]/.cache/uv

USER 1000:1000
CMD sh -c "make ${RUN_TARGET}"
```

docker-compose.yml Template (LOCAL DEVELOPMENT ONLY):
**Note:** docker-compose is for local development only. Production deployments use Kubernetes.

```yaml
secrets:
  artifactory_username:
    environment: UV_INDEX_ARTIFACTORY_USERNAME
  artifactory_password:
    environment: UV_INDEX_ARTIFACTORY_PASSWORD

services:
  app:
    container_name: "[project]_api"
    build:
      context: .
      secrets:
        - artifactory_username
        - artifactory_password
      args:
        RUN_TARGET: run
    env_file: .env
    environment:
      DB_DYNAMODB_CONNECTION_STRING: dynamodb://us-east-1/local/local?endpoint=http://dynamodb-local:8000
      UV_INDEX_ARTIFACTORY_USERNAME: ${UV_INDEX_ARTIFACTORY_USERNAME}
      UV_INDEX_ARTIFACTORY_PASSWORD: ${UV_INDEX_ARTIFACTORY_PASSWORD}
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      OBSERVABILITY__OTLP_ENABLED: true
      OBSERVABILITY__OTLP_ENDPOINT: http://jaeger:4317
    ports:
      - "[HOST_PORT]:[CONTAINER_PORT]"
    depends_on:
      - dynamodb-local
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:[PORT]/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - [project]-network

  workers:
    container_name: "[project]_workers"
    build:
      context: .
      secrets:
        - artifactory_username
        - artifactory_password
      args:
        RUN_TARGET: run/workers
    env_file: .env
    environment:
      DB_DYNAMODB_CONNECTION_STRING: dynamodb://us-east-1/local/local?endpoint=http://dynamodb-local:8000
      UV_INDEX_ARTIFACTORY_USERNAME: ${UV_INDEX_ARTIFACTORY_USERNAME}
      UV_INDEX_ARTIFACTORY_PASSWORD: ${UV_INDEX_ARTIFACTORY_PASSWORD}
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      - dynamodb-local
      - redis
    networks:
      - [project]-network

  dynamodb-local:
    container_name: "[project]-dynamodb-local"
    image: nn-docker-remote.artifactory.insim.biz/amazon/dynamodb-local:latest
    command: -jar DynamoDBLocal.jar -sharedDb -dbPath ./data
    user: root
    ports:
      - "8080:8000"
    volumes:
      - dynamodb-data:/home/dynamodblocal/data
    networks:
      - [project]-network

  redis:
    container_name: [project]-redis
    image: nn-docker-remote.artifactory.insim.biz/redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - [project]-network

  jaeger:
    container_name: [project]-jaeger
    image: nn-docker-remote.artifactory.insim.biz/jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC receiver
      - "4318:4318"    # OTLP HTTP receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - [project]-network

networks:
  [project]-network:
    driver: bridge

volumes:
  dynamodb-data:
  redis-data:
```

.dockerignore Template:
```dockerignore
.git
.gitignore
__pycache__
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.vscode/
.idea/
.DS_Store
*.md
docs/
.github/
.env
.env.local
dist/
build/
*.log
logs/
tests/
```

Building and Running:
```bash
# Build with secrets
make docker/build

# Run with docker-compose
make docker/compose-up

# Run with build
make docker/compose-up-with-build

# View logs
docker compose logs -f app

# Stop services
make docker/compose-down
```

Checklist:
- [ ] Use Artifactory registry for all images
- [ ] BuildKit secrets for Artifactory credentials
- [ ] Non-root user (1000:1000)
- [ ] Proper cache directory permissions
- [ ] Make commands for consistency
- [ ] ARG RUN_TARGET for flexibility
- [ ] Health checks defined
- [ ] Named networks for isolation
- [ ] Volume persistence for data
- [ ] .dockerignore to reduce image size
- [ ] Observability configuration
```

## Example Usage

```
Create Docker configuration for a new background worker service
[... rest of prompt ...]
```

## Related
- Agent: @senior-devops-engineer
- Instructions: docker.instructions.md
