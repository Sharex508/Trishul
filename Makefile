SHELL := /bin/sh

.PHONY: build up up-d down logs ps restart setup-venv install-backend install-worker backend-dev worker-dev frontend-dev env-print images-list images-offline-load up-prebuilt up-build publish

build:
	docker compose build

up:
	COMPOSE_PROFILES=build docker compose up --build

up-d:
	COMPOSE_PROFILES=build docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

restart: down up-d

# --- Local development helpers (no Docker required) ---
# Creates a Python virtualenv at ./.venv
setup-venv:
	python3 -m venv .venv
	. .venv/bin/activate; pip install --upgrade pip

# Install backend deps into .venv
install-backend:
	. .venv/bin/activate; pip install -r services/backend/requirements.txt

# Install worker deps into .venv
install-worker:
	. .venv/bin/activate; pip install -r services/worker/requirements.txt

# Print current env (after loading .env)
env-print:
	set -a; [ -f .env ] && . ./.env; set +a; env | sort | grep -E '^(POSTGRES_|TIMEZONE|PRICE_SYMBOLS|BACKEND_PORT|FRONTEND_PORT|VITE_API_BASE)='

# Run FastAPI backend locally (uses .env if present). Visit http://localhost:8000/health
backend-dev:
	set -a; [ -f .env ] && . ./.env; set +a; \
	. .venv/bin/activate; \
	cd services/backend; \
	uvicorn main:app --host 0.0.0.0 --port "$${BACKEND_PORT:-8000}"

# Run background worker locally (uses .env if present)
worker-dev:
	set -a; [ -f .env ] && . ./.env; set +a; \
	. .venv/bin/activate; \
	cd services/worker; \
	python main.py

# Run frontend locally on Vite dev server (uses VITE_API_BASE if set)
frontend-dev:
	cd services/frontend && npm ci || npm install
	cd services/frontend && npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}"

# --- Images utilities (for offline / internal registry flows) ---
images-list:
	@echo "Required base images (can be overridden via .env):"
	@echo "  POSTGRES_IMAGE=\"$${POSTGRES_IMAGE:-public.ecr.aws/docker/library/postgres:15-alpine}\""
	@echo "  BACKEND_BASE_IMAGE=\"$${BACKEND_BASE_IMAGE:-public.ecr.aws/docker/library/python:3.11-slim}\""
	@echo "  WORKER_BASE_IMAGE=\"$${WORKER_BASE_IMAGE:-public.ecr.aws/docker/library/python:3.11-slim}\""
	@echo "  FRONTEND_BASE_IMAGE=\"$${FRONTEND_BASE_IMAGE:-public.ecr.aws/docker/library/node:20-alpine}\""
	@echo "Optional prebuilt service images (COMPOSE_PROFILES=prebuilt):"
	@echo "  BACKEND_IMAGE=\"$${BACKEND_IMAGE:-<set-if-using-prebuilt>}\""
	@echo "  WORKER_IMAGE=\"$${WORKER_IMAGE:-<set-if-using-prebuilt>}\""
	@echo "  FRONTEND_IMAGE=\"$${FRONTEND_IMAGE:-<set-if-using-prebuilt>}\""

images-offline-load:
	@bash scripts/offline-load.sh

up-prebuilt:
	COMPOSE_PROFILES=prebuilt docker compose up -d

up-build:
	COMPOSE_PROFILES=build docker compose up -d

# --- Repo utilities ---
publish:
	bash scripts/publish_to_github.sh
