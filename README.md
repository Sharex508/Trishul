Crypto AI Platform (Scaffold)

This repository provides a minimal end-to-end scaffold:
- FastAPI backend (async Postgres)
- Background worker for mock price ingestion and AI decisions (paper trading)
- React (Vite + Tailwind) frontend with three panels: monitor, trading, AI panel
- Docker Compose orchestration

Highlights aligned with your requirements:
- Database: Postgres
- Deployment: docker-compose primary
- Exchange: Binance planned later (credentials via Admin UI). Currently mock data only.
- Timezone: UTC by default
- Paper trading: enabled by default
- Explainability: ai_logs table and API endpoint

Quick start
1) Copy env example to .env
   cp .env.example .env
2) Start services
   COMPOSE_PROFILES=build docker compose up --build

Alternative: build images first, then run in detached mode
- Build images only:
  COMPOSE_PROFILES=build docker compose build
- Run containers in background (detached):
  COMPOSE_PROFILES=build docker compose up -d
- Follow logs (optional):
  docker compose logs -f
- Stop and remove:
  docker compose down

Push this code to GitHub (Sharex508/Trishul)
If you want to push this repository to your GitHub account/repo now, use the included helper script. You can authenticate interactively (credential helper) or via a GitHub Personal Access Token (PAT) with repo scope.

Option A: Interactive auth (no token envs)
1) Ensure Git is installed and you’re logged in via credential helper.
2) Run:
   bash scripts/publish_to_github.sh
   or simply:
   make publish

Option B: Use a GitHub PAT (recommended for CI/non‑interactive)
1) Create a PAT with repo scope at https://github.com/settings/tokens
2) Export it and (optionally) your Git identity:
   export GH_TOKEN=ghp_yourTokenHere
   export GIT_USER_NAME="Your Name"
   export GIT_USER_EMAIL="you@example.com"
3) Run the publisher:
   bash scripts/publish_to_github.sh
   or: make publish

Manual commands (fallback)
If you prefer not to use the script:
   git init
   git checkout -b main || git branch -M main
   git add -A
   git commit -m "Initial commit: Crypto AI Platform scaffold"
   git remote add origin https://github.com/Sharex508/Trishul.git
   git push -u origin main

Run without Docker (local dev)
If your Docker build is blocked by TLS/CA restrictions, you can still run everything locally without containers. You only need a reachable Postgres database (local install or a remote instance).

Option A: Use your own/local Postgres
- Ensure a Postgres server is running and create a database (default name crypto).
- Update .env to point to it (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD).

Option B: If Docker can pull only Postgres from an internal registry
- You may run just the db service with your internal image override (see Troubleshooting/Overrides), and run backend/worker/frontend locally.

Steps to run services locally (no Docker):
1) Create a Python virtualenv and install deps
   make setup-venv
   make install-backend
   make install-worker
2) Start the backend (FastAPI on port 8000 by default)
   make backend-dev
   Check: http://localhost:${BACKEND_PORT:-8000}/health
3) In a separate terminal, start the worker
   make worker-dev
   This will generate mock prices, ai logs, and paper trades.
4) In another terminal, start the frontend (Vite dev server on 5173)
   make frontend-dev
   If your backend is not on default, set VITE_API_BASE in .env (e.g., VITE_API_BASE=http://localhost:8000)

Verifying local dev
- UI: http://localhost:${FRONTEND_PORT:-5173}
- Backend health: http://localhost:${BACKEND_PORT:-8000}/health
- Prices: http://localhost:${BACKEND_PORT:-8000}/prices/latest
  You should see rows appear after the worker starts.

If you're behind a corporate proxy/CA (quick steps)
- By default this repo uses AWS ECR Public mirrors for base images (public.ecr.aws/docker/library/*), which often work when Docker Hub is blocked.
- If you still need to override, edit .env and set internal images (or an allowed mirror):
  POSTGRES_IMAGE=mycorp.local/postgres:15-alpine
  BACKEND_BASE_IMAGE=mycorp.local/python:3.11-slim
  WORKER_BASE_IMAGE=mycorp.local/python:3.11-slim
  FRONTEND_BASE_IMAGE=mycorp.local/node:20-alpine
- Then rebuild:
  COMPOSE_PROFILES=build docker compose build
- If the error persists, follow the Troubleshooting section below to add your corporate CA to Docker or configure a registry mirror.

Run with prebuilt images (no docker build, avoids pulling base images)
If your environment blocks pulling base images during build, you can build images on a trusted machine (or use your internal registry) and run them here without any docker build step.

1) In .env, set the following to your internal/prebuilt images:
   BACKEND_IMAGE=mycorp.local/crypto-ai-backend:latest
   WORKER_IMAGE=mycorp.local/crypto-ai-worker:latest
   FRONTEND_IMAGE=mycorp.local/crypto-ai-frontend:latest

2) Start using the prebuilt profile (no builds, no base image pulls):
   COMPOSE_PROFILES=prebuilt docker compose up -d

Notes:
- The db service still uses an image (POSTGRES_IMAGE). If you cannot pull it, either:
  a) Point POSTGRES_IMAGE to your internal registry (recommended), or
  b) Use an external Postgres you already have and set POSTGRES_HOST/PORT/USER/PASSWORD/DB in .env, then comment the db service in docker-compose.yml.

Offline image loader (pure Docker, air-gapped friendly)
If you can move TAR files but not pull images, use the included loader to import images from tarballs.

Steps:
1) On a machine with internet access, pull and save the required images:
   docker pull public.ecr.aws/docker/library/python:3.11-slim
   docker pull public.ecr.aws/docker/library/node:20-alpine
   docker pull public.ecr.aws/docker/library/postgres:15-alpine
   docker save -o python-3.11-slim.tar public.ecr.aws/docker/library/python:3.11-slim
   docker save -o node-20-alpine.tar public.ecr.aws/docker/library/node:20-alpine
   docker save -o postgres-15-alpine.tar public.ecr.aws/docker/library/postgres:15-alpine

   Alternatively, save your internal prebuilt service images:
   docker save -o crypto-ai-backend.tar mycorp.local/crypto-ai-backend:latest
   docker save -o crypto-ai-worker.tar mycorp.local/crypto-ai-worker:latest
   docker save -o crypto-ai-frontend.tar mycorp.local/crypto-ai-frontend:latest

2) Copy the tar files to this repo at ./offline-images/

3) Load them locally:
   make images-offline-load

4a) If you loaded base images and will build here, set .env to reference those exact tags:
   BACKEND_BASE_IMAGE=public.ecr.aws/docker/library/python:3.11-slim
   WORKER_BASE_IMAGE=public.ecr.aws/docker/library/python:3.11-slim
   FRONTEND_BASE_IMAGE=public.ecr.aws/docker/library/node:20-alpine
   POSTGRES_IMAGE=public.ecr.aws/docker/library/postgres:15-alpine
   Then run: COMPOSE_PROFILES=build docker compose build && COMPOSE_PROFILES=build docker compose up -d

4b) If you loaded prebuilt service images, set in .env:
   BACKEND_IMAGE=mycorp.local/crypto-ai-backend:latest
   WORKER_IMAGE=mycorp.local/crypto-ai-worker:latest
   FRONTEND_IMAGE=mycorp.local/crypto-ai-frontend:latest
   Then run: COMPOSE_PROFILES=prebuilt docker compose up -d

Troubleshooting: docker compose build fails to pull images (x509: certificate signed by unknown authority)

If you see an error similar to:

  failed to resolve source metadata for docker.io/library/python:3.11-slim: tls: failed to verify certificate: x509: certificate signed by unknown authority

It indicates your Docker Engine cannot validate the TLS certificate when reaching Docker Hub (often due to a corporate proxy, custom CA, or network interception). Here are ways to resolve or work around it:

1) Verify general connectivity
   - docker login docker.io
   - docker pull hello-world
   - curl https://registry-1.docker.io/v2/ (should return unauthorized JSON, not a TLS error)

2) Configure Docker Desktop/Engine to trust your corporate CA
   - Obtain your company root CA certificate (e.g., corporate-root-ca.crt).
   - Docker Desktop: Settings → Docker Engine → add to "proxies"/"registry-mirrors" as needed and place the CA in the OS trust store. Restart Docker.
   - Linux engine: place the CA at /etc/docker/certs.d/registry-1.docker.io/ca.crt (and for any mirror host) and restart: sudo systemctl restart docker.
   - Docs: https://docs.docker.com/engine/security/certificates/

3) Use a registry mirror you can reach
   - If your org provides a mirror (e.g., https://registry.mycorp.local), configure it in Docker Desktop → Settings → Docker Engine:
     {
       "registry-mirrors": ["https://registry.mycorp.local"]
     }
     Restart Docker.

4) Use alternative image sources (mirrors or internal registry)
   - Defaults already point to AWS ECR Public mirrors: public.ecr.aws/docker/library/{postgres|python|node}.
   - You can override without editing Dockerfiles. Set environment variables before building:
     POSTGRES_IMAGE=mycorp.local/postgres:15-alpine
     BACKEND_BASE_IMAGE=mycorp.local/python:3.11-slim
     WORKER_BASE_IMAGE=mycorp.local/python:3.11-slim
     FRONTEND_BASE_IMAGE=mycorp.local/node:20-alpine
   - Then build:
     docker compose build

5) As a last resort for testing only (not recommended for production)
   - Temporarily allow an insecure registry if your internal mirror uses HTTP (no TLS). Add to /etc/docker/daemon.json:
     {
       "insecure-registries": ["registry.mycorp.local:5000"]
     }
     Then sudo systemctl restart docker. Only do this on trusted networks.

Compose warning about version key
 - Compose v2 ignores the top-level "version" key. This file omits it to avoid the warning.

Services and ports
- db: Postgres on 5432
- backend: FastAPI on 8000
- worker: background generator of mock prices/orders/ai logs
- frontend: Vite dev server on 5173

Open http://localhost:5173 in a browser.

API checks
- http://localhost:8000/health
- http://localhost:8000/config
- http://localhost:8000/symbols
- http://localhost:8000/prices/latest
- http://localhost:8000/orders
- http://localhost:8000/positions
- http://localhost:8000/ai/logs
- WebSocket: ws://localhost:8000/ws/prices

Structure
- services/backend: FastAPI app, models, CRUD, WebSocket
- services/worker: mock generator loop writing to DB
- services/frontend: Vite React app with Tailwind (dark mode)

Next steps to integrate your repos
- Import monitoring from coin-monitor into backend/frontend
- Import trading logic from Praha-Crypto into worker/backend
- Add Admin UI for credentials (Binance key/secret) stored in DB
- Replace mock generator with real market data ingestion (REST/websocket)
- Add Alembic migrations
- Enhance UI design (Tailwind components) and risk controls

Configuration
- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- TIMEZONE (UTC default)
- BACKEND_PORT, FRONTEND_PORT (host mappings)
- PRICE_SYMBOLS (comma-separated; default BTCUSDT,ETHUSDT)
- Frontend uses VITE_API_BASE for backend URL; docker-compose sets this automatically.
- Images/Profiles
  - Build profile (default in Makefile): COMPOSE_PROFILES=build → builds local images using BASE_IMAGEs (may pull).
  - Prebuilt profile: COMPOSE_PROFILES=prebuilt → runs images provided via BACKEND_IMAGE/WORKER_IMAGE/FRONTEND_IMAGE without building.
  - Offline loader: scripts/offline-load.sh loads TARs placed in ./offline-images to avoid pulling.

License
TBD by repository owner.
