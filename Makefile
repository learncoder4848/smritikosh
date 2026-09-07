.PHONY: install install-root lock test cov lint fmt check pre-commit-install pre-commit-run help

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo "Available targets:"
	@echo "  install             Install project dependencies with Poetry"
	@echo "  install-root        Install dependencies and the project package"
	@echo "  lock                Generate or update poetry.lock"
	@echo "  test                Run tests"
	@echo "  cov                 Run tests with coverage report"
	@echo "  lint                Run Ruff lint checks"
	@echo "  fmt                 Run Ruff format checks"
	@echo "  check               Run lint and tests with coverage"
	@echo "  pre-commit-install  Install pre-commit hooks"
	@echo "  pre-commit-run      Run pre-commit hooks against all files"

# ── Dependencies ──────────────────────────────────────────────────────────────

install:
	poetry install --no-root

install-root:
	poetry install

lock:
	poetry lock

# ── Test ──────────────────────────────────────────────────────────────────────

test:
	python -m pytest tests/ -v --no-cov

cov:
	python -m pytest tests/ \
	    --cov=smritikosh \
	    --cov-report=term-missing \
	    --cov-report=html:htmlcov \
	    --cov-fail-under=60

# ── Lint / Format ─────────────────────────────────────────────────────────────

lint:
	ruff check smritikosh/ tests/

fmt:
	ruff format smritikosh/ tests/

check: lint cov

# ── Pre-commit ────────────────────────────────────────────────────────────────

pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files
