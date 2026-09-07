.PHONY: check format help install install-root lint lock pre-commit-install pre-commit-run test

POETRY ?= poetry

help:
	@echo "Available targets:"
	@echo "  install             Install project dependencies with Poetry"
	@echo "  install-root        Install dependencies and the project package"
	@echo "  lock                Generate or update poetry.lock"
	@echo "  test                Run tests"
	@echo "  lint                Run Ruff lint checks"
	@echo "  format              Run Ruff format checks"
	@echo "  check               Run lint, format, and tests"
	@echo "  pre-commit-install  Install pre-commit hooks"
	@echo "  pre-commit-run      Run pre-commit hooks against all files"

install:
	$(POETRY) install --with dev --no-root

install-root:
	$(POETRY) install --with dev

lock:
	$(POETRY) lock

test:
	$(POETRY) run python -m pytest -v

lint:
	$(POETRY) run ruff check .

format:
	$(POETRY) run ruff format --check .

check: lint format test

pre-commit-install:
	$(POETRY) run pre-commit install

pre-commit-run:
	$(POETRY) run pre-commit run --all-files
