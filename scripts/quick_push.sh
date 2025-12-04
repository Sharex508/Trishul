#!/usr/bin/env bash
set -euo pipefail
msg="${1:-chore: quick push $(date -u +%F_%T)}"
git add -A
git commit -m "$msg" || echo "[quick_push] nothing to commit"
branch="$(git branch --show-current 2>/dev/null || echo main)"
if git rev-parse --verify origin/$branch >/dev/null 2>&1; then
  git pull --rebase origin "$branch" || true
fi
git push -u origin "$branch"
