.PHONY: help install/uv install install/dev test tests run

help:  ## Show this help
	@echo "🆘 Showing help"
	@grep -E '^[a-zA-Z0-9_./-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install/uv:  ## Ensure uv is installed: curl locally, pip in CI
	@echo "🔧 Ensuring uv is installed"
	@command -v uv >/dev/null 2>&1 || { \
		echo "📥 uv not found. Installing uv via curl..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}

install: install/uv  ## Install deps (excluding dev) with uv
	@echo "📦 Installing production dependencies"
	@uv sync
	@echo "✅ Done"

install/dev: install/uv  ## Install dev deps with uv
	@echo "📦 Installing development dependencies"
	@uv sync --dev
	@echo "✅ Done"

test: install/dev ## Run the test suite
	@echo "🧪 Running tests..."
	@uv run pytest

tests: test ## Alias for test

run: install ## Run the resume tailorator agentic workflow
	@echo "🚀 Running Resume Tailorator..."
	@uv run python utils/validate_inputs.py $(if $(RESUME_PATH),--resume-path "$(RESUME_PATH)")
	@uv run python main.py $(if $(RESUME_PATH),--resume-path "$(RESUME_PATH)")
