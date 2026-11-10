# BRIDGE v2 Automation Makefile

.PHONY: help up down migrate seed test lint e2e reset-demo build clean

help:
	@echo "Available commands:"
	@echo "  make up          - Start all containers (db, api, web) via Docker Compose"
	@echo "  make down        - Stop all running containers"
	@echo "  make migrate     - Run Alembic database migrations"
	@echo "  make seed        - Populate demo organization, rules, and telemetry"
	@echo "  make test        - Run backend test suite (RBAC, multi-tenant isolation, audit)"
	@echo "  make lint        - Run linting and TypeScript checks"
	@echo "  make e2e         - Run end-to-end integration test suite"
	@echo "  make reset-demo  - Clean database, re-migrate and re-seed demo data"

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	cd api && alembic upgrade head

seed:
	cd api && python -m app.seed

test:
	pytest tests -v

lint:
	cd web && npm run typecheck

e2e:
	pytest e2e -v

reset-demo: down
	docker compose down -v
	docker compose up -d db
	@echo "Waiting for PostgreSQL to be healthy..."
	sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	docker compose up -d api web
