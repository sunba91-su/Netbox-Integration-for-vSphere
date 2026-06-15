.PHONY: install install-dev lint format typecheck test test-cov check run clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck:
	pyright src/ tests/

test:
	python -m pytest tests/ -v --tb=short

test-cov:
	python -m pytest tests/ --cov=netbox_vsphere_sync --cov-report=term-missing --cov-fail-under=80

check: lint typecheck test

run:
	python -m netbox_vsphere_sync

clean:
	rm -rf build/ dist/ *.egg-info .mypy_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
