# ---------- Config ----------
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# ---------- Default ----------
.DEFAULT_GOAL := help

# ---------- Help ----------
help:
	@echo "Targets:"
	@echo "  make init        - First-time project setup (checks uv, syncs environment, and provides next steps)"
	@echo "  make venv        - Create virtual environment"
	@echo "  make sync        - Sync dependencies using uv"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run ruff"
	@echo "  make typecheck   - Run mypy"
	@echo "  make build       - Build wheel and sdist"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make requirements - Export dependencies to requirements.txt"
	@echo "  make requirements-dev - Export dev dependencies to requirements-dev.txt"
	@echo "  make ci          - Run the CI checks locally (no Docker)"
	@echo "  make ci-act      - Run the CI workflow in Docker via act"
	@echo "  make ci-act-list - List workflow jobs act would run"
	@echo ""	@echo "Use 'make <target>' to run a specific target. For example: 'make test' to run tests."

# ---------- First-time project setup ----------
init:
	@command -v uv >/dev/null 2>&1 || { \
		echo "❌ uv is not installed. Install from: https://github.com/astral-sh/uv"; \
		exit 1; \
	}
	@echo "▶ Syncing environment with uv..."
	uv sync
	@echo ""
	@echo "✅ Project ready."
	@echo "Run tests with: make test"

# ---------- Environment ----------
# venv:
# 	uv venv $(VENV)

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "▶ Virtual environment not found. Running uv sync..."; \
		uv sync; \
	fi
	@echo "Run: source $(VENV)/bin/activate"

sync:
	uv sync

# ---------- Development ----------
test: sync
	uv run pytest -v

lint: sync
	uv run ruff check .

lint-fix: sync
	uv run ruff check . --fix

lint-format: sync
	uv run ruff format .

typecheck: sync
	uv run mypy src

# ---------- Local CI ----------
# Mirrors .github/workflows/ci.yml step-for-step, without Docker.
ci: sync
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest -v

# Runs the real workflow in a container via act (https://github.com/nektos/act).
ci-act:
	@command -v act >/dev/null 2>&1 || { \
		echo "❌ act is not installed. Install with: brew install act"; \
		exit 1; \
	}
	@docker info >/dev/null 2>&1 || { \
		echo "❌ Docker daemon is not running. Start Docker Desktop/OrbStack first."; \
		exit 1; \
	}
	act pull_request -W .github/workflows/ci.yml

ci-act-list:
	act -l

# ---------- Build ----------
build: clean lint-fix lint-format sync
	uv build

# ---------- Cleanup ----------
# clean:
# 	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
# 	find . -type d -name "__pycache__" -exec rm -rf {} +

clean:
	@echo "Cleaning build artifacts and caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@rm -rf build dist *.egg-info

requirements: sync
	uv export --format requirements-txt -o requirements.txt

requirements-dev: sync
	uv export --format requirements-txt --dev -o requirements-dev.txt