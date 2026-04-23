# Docker Development Instructions

**Applies to:** `**/Dockerfile*`, `**/.dockerignore`, `**/docker-compose*.yml`, `**/docker-compose*.yaml`

**Reference:** https://docs.docker.com/build/building/best-practices/

## Core Principles

1. **Minimal images** — only include what the running application needs
2. **Multi-stage builds** — separate build-time from runtime dependencies
3. **Layer cache efficiency** — order instructions from least to most frequently changed
4. **Non-root user** — never run processes as root in production
5. **Reproducible builds** — pin base image digests and lock dependency versions
6. **uv as the installer** — use `uv sync --frozen --no-dev` in production stages

---

## Project Stack

- **Python 3.11+** — use `python:3.11-slim` as runtime base
- **uv** — package installer and virtual environment manager
- **meetingmind** — CLI entrypoint: `uv run meetingmind`
- **pyproject.toml + uv.lock** — locked dependency manifest

---

## Canonical Multi-Stage Dockerfile

```dockerfile
# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — install dependencies with uv
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Install uv (official installer — pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy only the dependency manifests first (maximises cache reuse)
COPY pyproject.toml uv.lock ./

# Install production dependencies into a local .venv
# --frozen  → fail if uv.lock is out of date (never silently update)
# --no-dev  → skip dev/test dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime — slim production image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="MeetingMind" \
      org.opencontainers.image.description="Intelligent transcript processor with AI-powered insights" \
      org.opencontainers.image.source="https://github.com/your-org/meetingmind" \
      org.opencontainers.image.licenses="MIT"

# Create a non-root user with an explicit UID/GID
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-log-init --no-create-home appuser

WORKDIR /app

# Copy the pre-built virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source (after deps — keep this layer last for fast rebuilds)
COPY src/ ./src/
COPY pyproject.toml ./

# Make the venv's Python and scripts the default
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to non-root user before running anything
USER appuser

# Document the port the app listens on (if serving HTTP)
# EXPOSE 8000

ENTRYPOINT ["meetingmind"]
CMD ["watch"]
```

---

## .dockerignore

Always create `.dockerignore` at the project root. It prevents unnecessary files from entering the build context, which speeds up builds and avoids leaking secrets.

```
# Version control
.git
.gitignore

# Python artifacts
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.egg-info
dist/
build/

# Virtual environments
.venv
venv/
env/

# Test / lint artifacts
.pytest_cache
.ruff_cache
.mypy_cache
htmlcov/
.coverage
coverage.xml

# Editor / IDE
.vscode
.idea
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment files — NEVER copy secrets into the image
.env
.env.*
!.env.example

# Docs
docs/
*.md
!README.md

# Docker files themselves (avoid redundant context)
Dockerfile*
docker-compose*.yml
docker-compose*.yaml
```

---

## Dockerfile Instructions Reference

### FROM

- Use **official Docker images** or **Verified Publisher** images as bases.
- Prefer the `slim` variant for runtime stages (`python:3.11-slim`).
- Use `alpine` only when you are certain all native extensions compile correctly under musl libc.
- **Pin to a digest** in production to guarantee reproducible builds:

```dockerfile
# ✅ Digest-pinned (production)
FROM python:3.11-slim@sha256:<digest> AS runtime

# ✅ Tag-pinned (CI/dev — acceptable with --pull on each build)
FROM python:3.11-slim AS runtime

# ❌ Unpinned — "latest" is a footgun
FROM python:latest AS runtime
```

### LABEL

Add OCI-compliant labels so images are discoverable and auditable:

```dockerfile
LABEL org.opencontainers.image.title="MeetingMind" \
      org.opencontainers.image.description="..." \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT"
```

Pass `GIT_SHA` and `BUILD_DATE` as build args from CI:

```bash
docker build \
  --build-arg GIT_SHA=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t meetingmind:latest .
```

### RUN

- **Chain related commands** in a single `RUN` to avoid extra layers.
- Always combine `apt-get update` and `apt-get install` in the same `RUN`.
- Clean the apt cache in the same layer to keep image size small.
- Sort package names alphabetically for readability and diff hygiene.
- Use `--no-install-recommends` to minimise installed packages.

```dockerfile
# ✅ Correct apt-get pattern
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# ❌ Broken — apt-get update alone is cached separately
RUN apt-get update
RUN apt-get install -y curl
```

- Use `set -o pipefail` when piping commands so failures propagate:

```dockerfile
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -fsSL https://example.com/script | bash
```

- Use `--mount=type=cache` for package manager caches (BuildKit):

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
```

### COPY vs ADD

| Instruction | When to use |
|---|---|
| `COPY` | Copying local files/directories into the image — **prefer this** |
| `ADD` | Downloading remote artifacts (HTTP/HTTPS) or auto-extracting tarballs |

```dockerfile
# ✅ Prefer COPY for local files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# ✅ Use --from to copy from another stage
COPY --from=builder /app/.venv /app/.venv

# ✅ ADD for remote artifacts with checksum
ADD --checksum=sha256:<hash> https://example.com/archive.tar.gz /tmp/archive.tar.gz

# ❌ Don't use ADD just to copy local files
ADD . /app
```

- Use bind mounts for build-time-only files to avoid polluting the final image:

```dockerfile
RUN --mount=type=bind,source=pyproject.toml,target=/tmp/pyproject.toml \
    pip install -r /tmp/requirements.txt
```

### ENV

- Use `ENV` for runtime configuration, not for secrets.
- Group related env vars on one line; each `ENV` creates a layer.

```dockerfile
# ✅ Group related settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# ✅ Version pinning via ARG (build-time only, not persisted)
ARG PYTHON_VERSION=3.11
```

- **Never put secrets in `ENV`** — they are visible in `docker inspect` and image layers.
  Use Docker secrets, Vault, or environment injection at runtime instead.

### ARG

Use `ARG` for build-time variables that must NOT persist in the runtime image (e.g., registry credentials):

```dockerfile
ARG ARTIFACTORY_TOKEN
RUN --mount=type=secret,id=pip_token \
    pip install --extra-index-url "https://token:$(cat /run/secrets/pip_token)@artifactory.example.com/pypi/simple" mypackage
```

### ENTRYPOINT and CMD

- `ENTRYPOINT` — the fixed executable (the container's "command").
- `CMD` — default arguments to `ENTRYPOINT`; easily overridden at `docker run`.
- Always use **exec form** (`["executable", "arg"]`), not shell form, so the process receives signals directly.

```dockerfile
# ✅ Exec form — PID 1 receives SIGTERM cleanly
ENTRYPOINT ["meetingmind"]
CMD ["watch"]

# ✅ Override at runtime
# docker run meetingmind:latest process --input /data/transcript.txt

# ❌ Shell form — wraps in /bin/sh -c, signals are not forwarded
ENTRYPOINT meetingmind watch
```

For services, use a shell entrypoint script when startup logic is needed:

```dockerfile
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["meetingmind", "watch"]
```

The script must use `exec "$@"` as its last line so the process becomes PID 1:

```bash
#!/bin/bash
set -e
# pre-flight checks, env validation, etc.
exec "$@"
```

### EXPOSE

Document the ports your container listens on. This is metadata only — actual port mapping happens at `docker run -p`.

```dockerfile
# FastAPI / uvicorn
EXPOSE 8000

# Prometheus metrics
EXPOSE 9090
```

### USER

Never run production containers as root. Create a dedicated user in the **builder** stage and reuse it in the runtime stage.

```dockerfile
# ✅ Explicit UID/GID — deterministic across rebuilds
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-log-init --no-create-home appuser

USER appuser
```

- Use `--no-log-init` to avoid the disk-exhaustion bug with large UIDs.
- Do not install `sudo`; use `gosu` if privilege escalation is truly needed.
- Switch to the non-root user **after** all `RUN` install commands.

### WORKDIR

Always use absolute paths. Never use `RUN cd /some/path && ...`.

```dockerfile
WORKDIR /app
```

### VOLUME

Declare volumes for mutable data that must survive container restarts:

```dockerfile
# Processed transcripts output directory
VOLUME ["/app/output"]

# SQLite or local state
VOLUME ["/app/data"]
```

---

## Multi-Stage Build Patterns

### Pattern 1: Builder + Runtime (standard)

```dockerfile
FROM python:3.11-slim AS builder
# ... install deps with uv ...

FROM python:3.11-slim AS runtime
COPY --from=builder /app/.venv /app/.venv
```

### Pattern 2: Test Stage

Add a `test` stage so CI can run tests inside Docker without polluting the runtime image:

```dockerfile
FROM builder AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen          # include dev deps for testing
COPY tests/ ./tests/
RUN uv run pytest tests/ -v
```

### Pattern 3: Shared Base

```dockerfile
FROM python:3.11-slim AS base
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-log-init --no-create-home appuser
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/
WORKDIR /app

FROM base AS builder
# ...

FROM base AS runtime
# ...
```

---

## uv-Specific Docker Patterns

### Installing uv

Use the official uv Docker image to copy the binary:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/
```

Pin the uv version for reproducible builds (replace `0.5` with the exact version).

### Dependency Installation (Production)

```dockerfile
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
```

- `--frozen` — error if `uv.lock` doesn't match `pyproject.toml` (never silently regenerate)
- `--no-dev` — exclude `[project.optional-dependencies].dev`
- `--mount=type=cache` — reuse the uv download cache across builds (BuildKit)

### Dependency Installation (CI with Tests)

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
```

Omit `--no-dev` to include test/lint tools.

### Running the Application

```dockerfile
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["meetingmind"]
CMD ["watch"]
```

Because the `.venv` is on `PATH`, there is no need for `uv run` at runtime.

---

## Build Commands

```bash
# Standard build
docker build -t meetingmind:latest .

# Always pull fresh base image + no layer cache (for nightly/release builds)
docker build --pull --no-cache -t meetingmind:latest .

# Target a specific stage (e.g., run tests only)
docker build --target test -t meetingmind:test .

# Pass build args for labels
docker build \
  --build-arg GIT_SHA=$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t meetingmind:$(git rev-parse --short HEAD) \
  -t meetingmind:latest \
  .

# BuildKit (enabled by default in Docker 23+, set explicitly for older versions)
DOCKER_BUILDKIT=1 docker build .
```

---

## Build Cache Strategy

Order `Dockerfile` instructions from **least frequently changed** to **most frequently changed**:

```
1. Base image (FROM)              ← changes rarely
2. System packages (RUN apt-get)  ← changes rarely
3. uv binary (COPY --from=uv)     ← changes on uv upgrades
4. pyproject.toml + uv.lock       ← changes on dependency updates
5. uv sync (RUN)                  ← invalidated when step 4 changes
6. Application source (COPY src/) ← changes on every commit  ← keep LAST
```

```dockerfile
# ✅ Cache-optimised order
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY src/ ./src/       # only this layer busts on code changes
```

---

## Security Best Practices

| Practice | Implementation |
|---|---|
| Non-root user | `USER appuser` (UID 1001) |
| No secrets in image | Use Docker secrets or runtime env injection |
| Minimal attack surface | `--no-install-recommends`, slim base |
| Pinned base image | `FROM python:3.11-slim@sha256:<digest>` |
| Read-only filesystem | `docker run --read-only --tmpfs /tmp` |
| No new privileges | `docker run --security-opt=no-new-privileges` |
| Vulnerability scanning | `docker scout cves meetingmind:latest` |
| Supply chain integrity | Lock uv version; verify uv binary checksum |

### Secrets at Build Time (Artifactory / private registries)

```dockerfile
# ✅ Use BuildKit secrets — never bake tokens into the image
RUN --mount=type=secret,id=artifactory_token \
    pip install \
      --index-url "https://token:$(cat /run/secrets/artifactory_token)@artifactory.example.com/pypi/simple" \
      mypackage

# Build command
docker build \
  --secret id=artifactory_token,src=$HOME/.artifactory_token \
  .
```

With uv and a private index:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=artifactory_token \
    UV_INDEX_URL="https://token:$(cat /run/secrets/artifactory_token)@artifactory.example.com/pypi/simple" \
    uv sync --frozen --no-dev
```

---

## Environment Variables Reference

| Variable | Purpose | Default |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE` | Prevent `.pyc` files | `1` |
| `PYTHONUNBUFFERED` | Flush stdout/stderr immediately | `1` |
| `PATH` | Include `.venv/bin` on path | `/app/.venv/bin:$PATH` |
| `UV_NO_PROGRESS` | Quieter uv output in CI | `1` |
| `UV_COMPILE_BYTECODE` | Pre-compile `.pyc` at install time | `1` (optional) |

---

## Quick Reference: Rules

- ✅ Use multi-stage builds — always separate builder from runtime
- ✅ Use `uv sync --frozen --no-dev` in production
- ✅ Use `--mount=type=cache` for uv's download cache
- ✅ Copy `pyproject.toml` + `uv.lock` before `src/` for cache efficiency
- ✅ Run as a non-root user (`USER appuser` with UID 1001)
- ✅ Use exec-form `ENTRYPOINT ["meetingmind"]` not shell form
- ✅ Always have a `.dockerignore` that excludes `.env`, `.git`, `__pycache__`
- ✅ Use `LABEL` with OCI-standard keys
- ✅ Combine `apt-get update && apt-get install` in one `RUN`
- ✅ Pin uv version in `COPY --from=ghcr.io/astral-sh/uv:<version>`
- ❌ Never use `FROM python:latest`
- ❌ Never `COPY . .` before installing dependencies (breaks layer cache)
- ❌ Never store secrets in `ENV`, `ARG`, or `COPY`
- ❌ Never run the app as root
- ❌ Never use shell-form `ENTRYPOINT` for production images
- ❌ Never omit `.dockerignore`
