.PHONY: dev test docker lint migrate clean help e2e

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

dev: ## Start backend with hot reload
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

test: ## Run pytest with coverage report
	cd backend && pytest --cov=app --cov-report=term-missing --cov-report=html

e2e: ## Run end-to-end integration tests
	ENV=test cd backend && pytest tests/test_e2e.py -v -s

docker: ## Build and start with docker-compose
	docker-compose up --build

lint: ## Run ruff and black check on backend
	cd backend && ruff check app/
	cd backend && black --check app/

migrate: ## Create MongoDB indexes
	cd backend && python -c "import asyncio; from app.services.database import connect_to_mongo, create_indexes; asyncio.run(connect_to_mongo())"

clean: ## Remove __pycache__, .pyc, logs
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
	rm -rf backend/logs/* 2>/dev/null || true
	@echo "Clean complete"
