Project: Crypto AI Platform (Scaffold) — Status & Next Steps

Overview
- End-to-end scaffold is ready: Postgres + FastAPI backend + worker + React (Vite + Tailwind) frontend.
- Docker Compose is primary. Added two profiles so you can avoid public image pulls if needed:
  - build profile: builds local images (may pull base images unless overridden)
  - prebuilt profile: runs prebuilt images from your internal registry (no docker build)
- Added an offline loader to import images from TAR files for air‑gapped or TLS‑restricted environments.

What’s implemented
1) Backend (FastAPI)
   - Async SQLAlchemy + Postgres
   - Tables: symbols, prices, orders, positions, ai_logs
   - REST endpoints: /health, /config, /symbols, /prices/latest, /orders, /positions, /ai/logs
   - WebSocket: /ws/prices for live updates
2) Worker
   - Generates mock prices and simple AI decisions
   - Writes prices, orders, positions, and AI logs to DB (paper trading)
3) Frontend (React + Vite + Tailwind; dark mode)
   - Monitor tab (prices), Trading tab (orders & positions), AI Panel (explainability logs)
4) Docker / DevOps
   - docker-compose.yml with db, backend, worker, frontend
   - Profiles:
     - build (default in Makefile) → builds service images from Dockerfiles
     - prebuilt → runs images from BACKEND_IMAGE/WORKER_IMAGE/FRONTEND_IMAGE
   - Image override variables in .env:
     - POSTGRES_IMAGE, BACKEND_BASE_IMAGE, WORKER_BASE_IMAGE, FRONTEND_BASE_IMAGE
     - BACKEND_IMAGE, WORKER_IMAGE, FRONTEND_IMAGE (for prebuilt profile)
   - scripts/offline-load.sh to docker load images from ./offline-images/*.tar
   - Makefile helpers: build, up, up-d, up-build, up-prebuilt, images-list, images-offline-load, logs, down, ps
5) No‑Docker local dev path (optional): run backend, worker, frontend directly on host.

Run instructions (new laptop)
1) Clone repo and prepare env
   - cp .env.example .env
2) Easiest path if Docker is unrestricted:
   - COMPOSE_PROFILES=build docker compose up --build
   - UI: http://localhost:5173
   - API: http://localhost:8000/health
3) If you have internal/prebuilt images (recommended in enterprises):
   - Edit .env:
       BACKEND_IMAGE=<your-registry>/crypto-ai-backend:latest
       WORKER_IMAGE=<your-registry>/crypto-ai-worker:latest
       FRONTEND_IMAGE=<your-registry>/crypto-ai-frontend:latest
       (Optional) POSTGRES_IMAGE=<your-registry>/postgres:15-alpine
   - Start without building:
       COMPOSE_PROFILES=prebuilt docker compose up -d
4) If your Docker cannot pull from public registries but you can transfer files:
   - Place TAR files under ./offline-images/ (python/node/postgres or your prebuilt images)
   - Load them: make images-offline-load
   - Either build locally using the loaded base images:
       COMPOSE_PROFILES=build docker compose build && COMPOSE_PROFILES=build docker compose up -d
     or run prebuilt service images:
       COMPOSE_PROFILES=prebuilt docker compose up -d

Common commands
- Build and run (build profile): make up      (foreground) / make up-build (detached)
- Run prebuilt images:         make up-prebuilt
- Show expected image tags:    make images-list
- Load offline TARs:           make images-offline-load
- Logs:                        docker compose logs -f
- Stop:                        docker compose down

Notes about the TLS error
- The x509 “certificate signed by unknown authority” error comes from Docker’s trust of the registry endpoint, not from Python/node versions or app code.
- The repo now supports fully Docker‑only alternatives (prebuilt profile or offline TARs) so you can proceed even in restricted environments.

Roadmap — Next steps to project completion
1) Database migrations
   - Add Alembic migrations for all current tables; auto-run on startup.
2) Admin UI and credentials
   - Admin page to input Binance API key/secret (stored encrypted in DB)
   - Backend endpoints to CRUD exchange credentials and risk parameters
3) Real data ingestion
   - Replace mock price generator with Binance market data (REST + websocket)
   - Symbol universe management (USDT pairs with volume filters)
4) Trading logic
   - Port Praha-Crypto strategy components into worker
   - Implement risk controls: max position, daily loss limit, paper/live mode toggle
   - Dry‑run testing harness (paper trading) with backtest sample
5) AI agent
   - Add rule/indicator engines (RSI, MACD, SMAs, breakouts, ATR stops)
   - Optional LLM reasoning calls with explainability logs
6) Frontend enhancements (design + UX)
   - Tailwind component polish, dark theme refinements
   - Trading UI: live orders, PnL, open positions, order entry, mode switch
   - AI panel: richer “thoughts” timeline with signals and confidence
7) Deploy & Ops
   - Production Docker images, healthchecks, resource limits
   - Environment configs for dev/stage/prod
   - Optional CI pipeline (build, test, push prebuilt images)

What I need from you to proceed
- Decide initial exchange scope (Binance spot by default) and the first symbols or filters
- Confirm if we’ll use internal registry or offline TARs for images in CI/CD
- Provide (or confirm) a target cloud/VM for production deployment later
- Any UI design preferences (component library or inspiration)

Quick verification checklist (after start)
- API health at /health returns {"status": "ok"}
- /prices/latest shows rows after worker starts (mock or real later)
- Frontend shows live price updates and AI logs

Contact/Support
- If compose fails due to image pulls, switch to prebuilt images or use offline loader as described above.
