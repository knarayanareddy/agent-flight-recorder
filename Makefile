.PHONY: help setup dev test lint verify gate clean

help:
	@echo "Available commands for agent-flight-recorder:"
	@echo "  make setup   - Create venv and install dependencies"
	@echo "  make dev     - Run FastAPI development server on port 8000"
	@echo "  make test    - Run pytest test suite"
	@echo "  make lint    - Run code linting"
	@echo "  make verify  - Run contract integrity manifest verification"
	@echo "  make gate    - Run release gate verification"
	@echo "  make clean   - Remove cache files"

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v tests/

lint:
	flake8 src tests || true

verify:
	python scripts/verify_manifest.py

gate:
	python scripts/release_gate.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +

test-baseline:
	pytest -v tests/test_baseline.py

product-smoke:
	python scripts/product_smoke.py

product-acceptance:
	python scripts/product_acceptance.py

product-journeys:
	python scripts/product_journeys.py
