.PHONY: help lint type test cover dev migrate clean install-hooks

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

lint: ## Run ruff linter
	ruff check src/ tests/

type: ## Run mypy type checker on services
	mypy src/services/event_bus.py src/services/alerting.py

test: ## Run all tests (parallel)
	pytest tests/ -n auto --ignore=tests/e2e/test_live_pipeline.py

cover: ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=term --ignore=tests/e2e/test_live_pipeline.py

dev: ## Install dev dependencies
	pip install -e ".[dev]"

migrate: ## Run alembic migrations
	alembic upgrade heads

clean: ## Remove __pycache__ directories
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

install-hooks: ## Install pre-commit hooks
	bash scripts/install-hooks.sh
