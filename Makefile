# NetSentinel Development Makefile
# Comprehensive build, test, and development automation

.PHONY: help install install-dev test test-unit test-integration test-e2e lint format clean docs build docker-test

# Default target
help: ## Show this help message
	@echo "NetSentinel Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install NetSentinel in development mode
	pip install -e .

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt
	pip install -e .

install-all: install-dev ## Install all dependencies (dev + runtime)

# Testing
test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests
	pytest netsentinel/tests/unit/ -v --cov=netsentinel --cov-report=term-missing --cov-report=html

test-integration: ## Run integration tests
	pytest netsentinel/tests/integration/ -v --tb=short

test-e2e: ## Run end-to-end tests
	pytest tests/e2e/ -v --tb=short

test-smoke: ## Run smoke tests for CI/CD
	pytest netsentinel/tests/unit/ -k "smoke" -v --tb=short

test-performance: ## Run performance tests
	pytest netsentinel/tests/unit/ -k "performance" -v --tb=short

test-security: ## Run security-related tests
	pytest netsentinel/tests/unit/ -k "security" -v --tb=short

test-ml: ## Run ML-related tests
	pytest netsentinel/tests/unit/ -k "ml" -v --tb=short

test-playwright: ## Run Playwright API tests (if configured)
	pytest tests/playwright/ -v --tb=short

test-all: ## Run all test suites
	pytest netsentinel/tests/ -v --cov=netsentinel --cov-report=term-missing --cov-report=html --durations=10

# Code Quality
lint: ## Run all linting checks
	pre-commit run --all-files

lint-flake8: ## Run flake8 linting
	flake8 netsentinel/

lint-mypy: ## Run mypy type checking
	mypy netsentinel/

lint-bandit: ## Run bandit security linting
	bandit -r netsentinel/

lint-all: lint-flake8 lint-mypy lint-bandit ## Run all linting tools

# Formatting
format: ## Format code with black and isort
	black netsentinel/
	isort netsentinel/

format-check: ## Check code formatting without modifying
	black --check netsentinel/
	isort --check-only netsentinel/

# Testing with different configurations
test-py39: ## Test with Python 3.9
	pytest tests/unit/ -v --cov=netsentinel --python=python3.9

test-py310: ## Test with Python 3.10
	pytest tests/unit/ -v --cov=netsentinel --python=python3.10

test-py311: ## Test with Python 3.11
	pytest tests/unit/ -v --cov=netsentinel --python=python3.11

# Docker testing
docker-build: ## Build NetSentinel Docker images
	docker-compose build

docker-test: ## Run tests in Docker environment
	docker-compose up -d event-processor
	sleep 10
	docker-compose exec -T event-processor pytest tests/unit/ -v --tb=short
	docker-compose down

docker-smoke: ## Run smoke tests in Docker
	docker-compose up -d event-processor
	sleep 10
	docker-compose exec -T event-processor make test-smoke
	docker-compose down

# Development environment
dev-setup: ## Set up development environment
	pre-commit install
	pip install -r requirements-dev.txt
	pip install -e .
	@echo "Development environment ready!"

dev-clean: ## Clean development artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/ .coverage coverage.xml

# Documentation
docs: ## Build documentation
	sphinx-build -b html docs/ docs/_build/html

docs-serve: ## Serve documentation locally
	sphinx-build -b html docs/ docs/_build/html
	cd docs/_build/html && python -m http.server 8000

# Building and packaging
build: ## Build distribution packages
	python -m build

build-sdist: ## Build source distribution
	python setup.py sdist

build-wheel: ## Build wheel distribution
	python setup.py bdist_wheel

# CI/CD simulation
ci: lint test-all ## Run full CI pipeline locally

ci-quick: format-check lint-flake8 test-unit ## Quick CI checks

# Database testing
test-db: ## Run database-related tests
	pytest tests/unit/ -k "database" -v

# Network testing
test-network: ## Run network-related tests
	pytest tests/unit/ -k "network" -v

# Security testing
security-scan: ## Run comprehensive security scans
	bandit -r netsentinel/
	safety check
	@echo "Security scan complete"

# Performance profiling
profile: ## Run performance profiling on key functions
	python -m cProfile -s cumtime -o profile.stats netsentinel/event_processor.py
	snakeviz profile.stats

# Coverage reporting
coverage: ## Generate detailed coverage report
	pytest tests/ --cov=netsentinel --cov-report=html
	open htmlcov/index.html

coverage-console: ## Show coverage report in console
	pytest tests/ --cov=netsentinel --cov-report=term-missing

# Dependency management
deps-update: ## Update dependencies
	pip-tools compile --upgrade
	pip install -r requirements-dev.txt

deps-check: ## Check for outdated dependencies
	pip list --outdated

# Pre-commit hooks
hooks-install: ## Install pre-commit hooks
	pre-commit install

hooks-update: ## Update pre-commit hooks
	pre-commit autoupdate

# Release preparation
release-check: ## Check if ready for release
	@echo "Running release checks..."
	make lint-all
	make test-all
	make build
	@echo "Release checks complete!"

# Development server
serve-dev: ## Start development server with auto-reload
	export FLASK_ENV=development
	python -m netsentinel.event_processor

# Kubernetes testing
k8s-test: ## Test Kubernetes manifests
	kubeval k8s/*.yaml
	kubectl apply --dry-run=client -f k8s/

# Helm testing
helm-test: ## Test Helm charts
	helm lint helm/netsentinel/
	helm template test helm/netsentinel/ --dry-run

# Utility commands
version: ## Show NetSentinel version
	python -c "import netsentinel; print(netsentinel.__version__)"

info: ## Show project information
	@echo "NetSentinel - Advanced Network Anomaly Detection & Mitigation"
	@echo "Version: $(shell python -c "import netsentinel; print(netsentinel.__version__)" 2>/dev/null || echo "unknown")"
	@echo "Python: $(shell python --version)"
	@echo "Platform: $(shell uname -s)"

# Clean all
clean-all: dev-clean ## Clean all artifacts and caches
	rm -rf build/ dist/ *.egg-info/
	rm -rf docs/_build/
	rm -rf .tox/ .eggs/
	rm -rf profile.stats