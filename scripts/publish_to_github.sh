#!/usr/bin/env bash
set -euo pipefail

# Helper to initialize git (if needed) and push this repo to GitHub
# Target repo (default): https://github.com/Sharex508/Trishul (override with REMOTE_REPO_URL)
# Usage:
#   export GH_TOKEN=<personal-access-token-with-repo-scope>   # or GITHUB_TOKEN
#   export GIT_USER_NAME="Your Name"                          # optional
#   export GIT_USER_EMAIL="you@example.com"                   # optional
#   bash scripts/publish_to_github.sh
#
# Notes:
# - If a token is provided, the script will embed it in the remote URL for the initial push only.
# - If you prefer to enter credentials interactively, unset GH_TOKEN/GITHUB_TOKEN before running.

REMOTE_REPO_URL="${REMOTE_REPO_URL:-https://github.com/Sharex508/Trishul.git}"
TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v git >/dev/null 2>&1; then
  echo "[publish] Git is not installed. Please install Git and rerun." >&2
  exit 1
fi

# Ensure sensible git config if provided
if [ -n "${GIT_USER_NAME:-}" ]; then
  git config --global user.name "$GIT_USER_NAME"
fi
if [ -n "${GIT_USER_EMAIL:-}" ]; then
  git config --global user.email "$GIT_USER_EMAIL"
fi

if [ ! -d .git ]; then
  echo "[publish] Initializing new git repository..."
  git init
  # Ensure main is the default branch
  git checkout -b main 2>/dev/null || git branch -M main
else
  # Normalize to main branch name
  git rev-parse --abbrev-ref HEAD >/dev/null 2>&1 || true
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD || echo "main")
  if [ "$CURRENT_BRANCH" != "main" ]; then
    git branch -M main || true
  fi
fi

# Create a .gitignore if missing (should already exist)
if [ ! -f .gitignore ]; then
  cat > .gitignore <<'EOGI'
.DS_Store
.env
.env.*
*.log
*.pyc
__pycache__/
.venv/
.idea/
.vscode/
build/
dist/
*.egg-info/
node_modules/
services/frontend/node_modules/
services/frontend/.vite/
services/frontend/dist/
db_data/
offline-images/*.tar
EOGI
fi

# Stage and commit all changes (idempotent)
git add -A
if git diff --cached --quiet; then
  echo "[publish] Nothing to commit."
else
  git commit -m "Initial commit: Crypto AI Platform scaffold (backend, worker, frontend, docker-compose)"
fi

# Configure remote
if git remote get-url origin >/dev/null 2>&1; then
  echo "[publish] Remote 'origin' already set to: $(git remote get-url origin)"
else
  echo "[publish] Setting remote 'origin' to $REMOTE_REPO_URL"
  git remote add origin "$REMOTE_REPO_URL"
fi

# Push
echo "[publish] Pushing to GitHub repo: $REMOTE_REPO_URL (branch: main)"

if [ -n "$TOKEN" ]; then
  # Embed token for this push only (without persisting in git config).
  # Construct a temporary remote URL by injecting the token into REMOTE_REPO_URL.
  # Example: https://github.com/owner/repo.git -> https://TOKEN@github.com/owner/repo.git
  if [[ "$REMOTE_REPO_URL" =~ ^https:// ]]; then
    TMP_URL="${REMOTE_REPO_URL/https:\/\//https:\/\/${TOKEN}@}"
  else
    echo "[publish] REMOTE_REPO_URL must be an HTTPS URL when using a token. Current: $REMOTE_REPO_URL" >&2
    exit 1
  fi
  git push "$TMP_URL" main:main --follow-tags --set-upstream || {
    echo "[publish] Push failed. Check token permissions (repo scope) and repository access." >&2
    exit 1
  }
  # Reset remote (without token) to clean URL for future pulls
  git remote set-url origin "$REMOTE_REPO_URL"
else
  # Interactive/credential-helper path
  git push origin main:main --follow-tags --set-upstream || {
    echo "[publish] Push failed. If you don't want interactive auth, set GH_TOKEN or GITHUB_TOKEN with repo scope." >&2
    exit 1
  }
fi

echo "[publish] Done. Repository is pushed to $REMOTE_REPO_URL"
