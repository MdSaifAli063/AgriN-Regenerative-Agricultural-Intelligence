# =============================================================================
# KrishiNet-BRICS (AgriN Commons) - Developer Automation Makefile
# =============================================================================

.PHONY: help up down restart logs migrate seed test lint shell clean federation-up federation-down federation-demo test-federation

help:
	@echo "KrishiNet-BRICS Control Commands:"
	@echo "  make up               - Build and start base services via Docker Compose"
	@echo "  make down             - Stop and remove all base containers"
	@echo "  make federation-up    - Start 3 sovereign nodes (IND, BRA, ZAF) + Registry"
	@echo "  make federation-down  - Stop all federation containers and networks"
	@echo "  make federation-demo  - Execute automated 8-step live demonstration script"
	@echo "  make test-federation  - Execute all Parts 7A-7F federation test suites"
	@echo "  make test             - Execute automated pytest test suite"
	@echo "  make lint             - Check code formatting and type safety"
	@echo "  make clean            - Remove python caches and temporary build artifacts"

up:
	docker compose up -d --build
	@echo "Services started. Swagger UI available at: http://localhost:8000/docs"
	@echo "MinIO Console at: http://localhost:9001 (minio_admin / KrishiMinio2026!)"
	@echo "Keycloak Admin at: http://localhost:8080 (admin / admin)"

down:
	docker compose down -v

federation-up:
	docker compose --profile federation up -d --build
	@echo "BRICS Federation cluster active:"
	@echo "  - India Node (KrishiNet):        http://localhost:8000"
	@echo "  - Brazil Node (Embrapa):          http://localhost:8001"
	@echo "  - South Africa Node (ARC):        http://localhost:8002"
	@echo "  - BRICS Commons Registry:         http://localhost:8010"

federation-down:
	docker compose --profile federation down -v

federation-demo:
	python federation_demo.py

test-federation:
	pytest services/api/tests -k federation -v

restart:
	docker compose restart

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

seed:
	python scripts/seed.py

test:
	pytest services/api/tests -v

lint:
	python -m pycodestyle services/api/src || true

shell:
	docker compose exec api /bin/bash

clean:
	rm -rf .pytest_cache services/api/.pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

