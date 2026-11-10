# LogLens developer commands (macOS / Linux). Run `make help` for the list.
SHELL := /bin/bash
PYTHON ?= $(shell command -v python3.12 || command -v python3)
VENV   := backend/.venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
-include .env
export

DB_URL_TEST ?= postgresql+psycopg://$(or $(POSTGRES_USER),loglens):$(or $(POSTGRES_PASSWORD),loglens)@localhost:$(or $(DB_HOST_PORT),5432)/$(or $(POSTGRES_DB),loglens)_test

.DEFAULT_GOAL := help
.PHONY: help setup env venv frontend-install db-up db-down db-reset db-shell migrate seed \
        dev-backend dev-frontend test test-backend test-backend-pg test-frontend e2e lint \
        up down logs demo samples perf clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- setup
setup: env venv frontend-install ## One-time setup: .env, Python venv, npm packages
	@echo "✅ Setup done. Next: make db-up && make migrate && make dev-backend (and make dev-frontend in another terminal)"

env: ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "Created .env")

venv: ## Create backend/.venv and install Python dependencies
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r backend/requirements-dev.txt

frontend-install: ## npm ci in frontend/
	cd frontend && npm ci

# ---------------------------------------------------------------- database
db-up: ## Start only PostgreSQL (Docker)
	docker compose up -d db

db-down: ## Stop PostgreSQL (data kept)
	docker compose stop db

db-reset: ## ⚠️ Delete the database volume and start fresh
	docker compose down -v
	docker compose up -d db

db-shell: ## psql into the dev database
	docker compose exec db psql -U $(or $(POSTGRES_USER),loglens) $(or $(POSTGRES_DB),loglens)

migrate: ## Apply Alembic migrations to the dev database
	cd backend && .venv/bin/alembic upgrade head

seed: ## Load the synthetic sample datasets
	cd backend && .venv/bin/python -m app.scripts.seed_samples

samples: ## Regenerate sample_data/ (deterministic)
	$(PYTHON) scripts/generate_sample_data.py

# ---------------------------------------------------------------- run (hot reload)
dev-backend: ## FastAPI with auto-reload on http://localhost:8000 (docs: /docs)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port $(or $(API_HOST_PORT),8000)

dev-frontend: ## Vite dev server on http://localhost:5173
	cd frontend && npm run dev

# ---------------------------------------------------------------- quality
test: test-backend test-frontend ## Backend + frontend unit/integration tests

test-backend: ## Pytest (SQLite, no services needed)
	cd backend && .venv/bin/pytest

test-backend-pg: ## Pytest against PostgreSQL (needs make db-up)
	cd backend && TEST_DATABASE_URL=$(DB_URL_TEST) .venv/bin/pytest

test-frontend: ## Vitest
	cd frontend && npm test

e2e: ## Playwright end-to-end tests (needs the app running on :5173)
	cd frontend && npx playwright test

lint: ## Ruff + ESLint + TypeScript
	cd backend && .venv/bin/ruff check .
	cd frontend && npm run lint && npm run typecheck

perf: ## Measure 20k-line import + dashboard latency (needs make db-up)
	cd backend && TEST_DATABASE_URL=$(DB_URL_TEST) .venv/bin/python ../scripts/perf_check.py

# ---------------------------------------------------------------- containers
up: ## Full stack in Docker: http://localhost:8080
	docker compose up --build -d
	@echo "Open http://localhost:$(or $(WEB_HOST_PORT),8080)  (API docs: http://localhost:$(or $(API_HOST_PORT),8000)/docs)"

down: ## Stop the Docker stack (data kept)
	docker compose down

logs: ## Follow container logs
	docker compose logs -f

demo: ## Read-only public demo preview with seeded samples
	docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build -d
	@echo "Read-only demo on http://localhost:$(or $(WEB_HOST_PORT),8080)"

clean: ## Remove caches and build output
	rm -rf backend/.pytest_cache backend/.ruff_cache frontend/dist frontend/test-results frontend/playwright-report
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
