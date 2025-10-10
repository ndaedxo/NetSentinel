.PHONY: help install build up down test clean logs restart status

help:
	@echo "OpenCanary Hybrid System - Available commands:"
	@echo "  install    Install Python dependencies"
	@echo "  build      Build Docker images"
	@echo "  up         Start all services"
	@echo "  down       Stop all services"
	@echo "  logs       View service logs"
	@echo "  restart    Restart all services"
	@echo "  status     Show service status"
	@echo "  test       Run tests"
	@echo "  clean      Clean build artifacts and containers"

install:
	pip install -r requirements.txt

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting... Access URLs:"
	@echo "  Grafana:     http://localhost:3000 (admin/hybrid-admin-2024)"
	@echo "  Kafka UI:    http://localhost:8080"
	@echo "  Redis Cmdr:  http://localhost:8081"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  Event API:   http://localhost:8082"

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

status:
	docker-compose ps

test:
	python -m pytest opencanary/test/ -v

clean:
	docker-compose down -v --remove-orphans
	docker system prune -f
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete