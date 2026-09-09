.PHONY: install install-root lock test cov check-wheel lint fmt check pre-commit-install pre-commit-run help

# ── Tool selection ─────────────────────────────────────────────────────────────
# Override on the command line:  make install TOOL=uv  or  export TOOL=uv
TOOL ?= poetry

ifeq ($(TOOL),uv)
  _install      := uv sync --no-install-project
  _install_root := uv sync
  _lock         := uv lock
else
  POETRY ?= poetry
  _install      := $(POETRY) install --no-root
  _install_root := $(POETRY) install
  _lock         := $(POETRY) lock
endif

# Call the venv's binaries directly so targets work without activating it.
VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python

# Suites that run without loading the embedding model. Named once because both
# test and cov need the list; add new directories here.
FAST_TESTS := tests/engine/ tests/models/ tests/adapters/vector_store/ \
	tests/adapters/file_source/ tests/queries/ tests/indexing/

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo "Available targets:"
	@echo "  install             Install project dependencies (TOOL=poetry|uv)"
	@echo "  install-root        Install dependencies and the project package (TOOL=poetry|uv)"
	@echo "  lock                Generate or update the lock file (TOOL=poetry|uv)"
	@echo "  test                Run tests"
	@echo "  cov                 Run tests with coverage report"
	@echo "  check-wheel         Verify the built wheel carries the tags.scm files"
	@echo "  lint                Run Ruff lint checks"
	@echo "  fmt                 Run Ruff format checks"
	@echo "  check               Run lint and tests with coverage"
	@echo "  pre-commit-install  Install pre-commit hooks"
	@echo "  pre-commit-run      Run pre-commit hooks against all files"

# ── Dependencies ──────────────────────────────────────────────────────────────

install:
	$(_install)

install-root:
	$(_install_root)

lock:
	$(_lock)

# ── Test ──────────────────────────────────────────────────────────────────────

test:
	$(PY) -m pytest $(FAST_TESTS) -v --no-cov

cov:
	$(PY) -m pytest $(FAST_TESTS) \
	    --cov=smritikosh \
	    --cov-report=term-missing \
	    --cov-report=html:htmlcov \
	    --cov-fail-under=75

# The language directories under smritikosh/queries/ are not packages, so the
# .scm files reach the wheel only through a package-data glob. Nothing in the
# test suite would notice if that glob stopped matching, hence this check.
check-wheel:
	@rm -rf dist/wheel-check
	@$(PY) -m build --wheel --outdir dist/wheel-check >/dev/null
	@found=$$(unzip -l dist/wheel-check/*.whl | grep -c 'queries/.*/tags\.scm'); \
	if [ "$$found" -ne 7 ]; then \
	    echo "ERROR: expected 7 tags.scm files in the wheel, found $$found."; \
	    echo "Check [tool.setuptools.package-data] in pyproject.toml."; \
	    rm -rf dist/wheel-check; exit 1; \
	fi; \
	rm -rf dist/wheel-check; \
	echo "Wheel carries all 7 tags.scm files."

# ── Lint / Format ─────────────────────────────────────────────────────────────

lint:
	$(VENV)/bin/ruff check smritikosh/ tests/

fmt:
	$(VENV)/bin/ruff format smritikosh/ tests/

check: lint cov

# ── Pre-commit ────────────────────────────────────────────────────────────────

pre-commit-install:
	$(VENV)/bin/pre-commit install

pre-commit-run:
	$(VENV)/bin/pre-commit run --all-files
