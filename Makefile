.PHONY: help lint type test cover dev migrate clean install-hooks web-dev web-build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

lint: ## Run ruff linter
	ruff check src/ tests/

type: ## Run mypy type checker on services
	mypy src/services

test: ## Run all tests (parallel, exclude slow/live)
	ulimit -n 4096 && pytest tests/ -n auto -m "not slow and not live" --ignore=tests/e2e/test_backtest_flow.py --timeout=120

test-all: ## Run all tests including slow
	ulimit -n 4096 && pytest tests/ -n auto --ignore=tests/e2e/test_backtest_flow.py --timeout=300

cover: ## Run tests with coverage report
	ulimit -n 4096 && pytest tests/ --cov=src --cov-report=term -m "not slow and not live" --ignore=tests/e2e/test_backtest_flow.py --timeout=120

dev: ## Install dev dependencies
	pip install -e ".[dev]"

migrate: ## Run alembic migrations
	alembic upgrade heads

clean: ## Remove __pycache__ directories
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

install-hooks: ## Install pre-commit hooks
	bash scripts/install-hooks.sh

web-dev: ## Start web dev server
	cd web && pnpm dev

web-build: ## Build web for production
	cd web && pnpm build
