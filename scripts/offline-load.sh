#!/usr/bin/env bash
set -euo pipefail

# Offline loader for base/prebuilt images to avoid any pulls from public registries.
# Usage:
#   bash scripts/offline-load.sh
#
# Place image tarballs under ./offline-images/ (created below if missing).
# Accepts any *.tar files (as produced by `docker save`).
# After loading, you may need to `docker tag` them to the names referenced by docker-compose.yml
# via your .env overrides (POSTGRES_IMAGE, BACKEND_BASE_IMAGE, WORKER_BASE_IMAGE, FRONTEND_BASE_IMAGE)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OFFLINE_DIR="$ROOT_DIR/offline-images"
mkdir -p "$OFFLINE_DIR"

echo "[offline-load] Looking for image tarballs in $OFFLINE_DIR"

shopt -s nullglob
TARS=($OFFLINE_DIR/*.tar)
if [ ${#TARS[@]} -eq 0 ]; then
  echo "[offline-load] No tar files found. Put your images here (examples):"
  echo "  $OFFLINE_DIR/python-3.11-slim.tar"
  echo "  $OFFLINE_DIR/node-20-alpine.tar"
  echo "  $OFFLINE_DIR/postgres-15-alpine.tar"
  echo "Or any images you built internally:"
  echo "  docker save -o $OFFLINE_DIR/crypto-ai-backend.tar mycorp.local/crypto-ai-backend:latest"
  exit 0
fi

for TAR in "${TARS[@]}"; do
  echo "[offline-load] Loading $TAR ..."
  docker load -i "$TAR" || {
    echo "[offline-load] Failed to load $TAR" >&2
    exit 1
  }
done

echo "[offline-load] Done. List of local images (filtered):"
docker images | awk 'NR==1 || /python|node|postgres|crypto-ai/'

cat <<'EONOTE'

Next steps:
- If you loaded base images (python/node/postgres) and will build locally:
  * Ensure your .env has BACKEND_BASE_IMAGE / WORKER_BASE_IMAGE / FRONTEND_BASE_IMAGE / POSTGRES_IMAGE set to the exact tags loaded.
  * Then run: COMPOSE_PROFILES=build docker compose build && COMPOSE_PROFILES=build docker compose up -d

- If you loaded prebuilt service images (backend/worker/frontend):
  * Set in .env: BACKEND_IMAGE=..., WORKER_IMAGE=..., FRONTEND_IMAGE=...
  * Then run: COMPOSE_PROFILES=prebuilt docker compose up -d

Tip: To create tarballs on a machine with internet:
  docker pull public.ecr.aws/docker/library/python:3.11-slim
  docker pull public.ecr.aws/docker/library/node:20-alpine
  docker pull public.ecr.aws/docker/library/postgres:15-alpine
  docker save -o python-3.11-slim.tar public.ecr.aws/docker/library/python:3.11-slim
  docker save -o node-20-alpine.tar public.ecr.aws/docker/library/node:20-alpine
  docker save -o postgres-15-alpine.tar public.ecr.aws/docker/library/postgres:15-alpine
  # Move the tar files to ./offline-images on the target machine and run this script.

EONOTE
