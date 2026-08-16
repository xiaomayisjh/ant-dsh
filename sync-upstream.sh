#!/usr/bin/env bash
# Fast-forward the stable branch to upstream, then merge it into the dev branch.
# master tracks the official repository and only ever fast-forwards; dev
# carries the fork's changes. Both are pushed to origin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# ---- configurable ----
UPSTREAM_URL="https://github.com/deepseek-ai/deepseek-harness.git"
DEV_BRANCH="dev"
STABLE_BRANCH="master"
# -----------------------

command -v git >/dev/null 2>&1 || { echo "[sync] git not found on PATH." >&2; exit 1; }

# Refuse to run with uncommitted changes: merging over a dirty tree can
# destroy local work.
if [ -n "$(git status --porcelain)" ]; then
  echo "[sync] working tree has uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

# Ensure the upstream remote exists and points at the official repo.
if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "[sync] adding upstream remote: $UPSTREAM_URL"
  git remote add upstream "$UPSTREAM_URL"
fi

echo "[sync] fetching upstream..."
git fetch upstream
git fetch origin

# --- stable branch: fast-forward only, never carries local commits ---
echo "[sync] updating $STABLE_BRANCH to upstream/$STABLE_BRANCH (fast-forward only)..."
git checkout "$STABLE_BRANCH"
if ! git merge --ff-only "upstream/$STABLE_BRANCH"; then
  echo "[sync] $STABLE_BRANCH has diverged from upstream. Inspect with: git log --oneline $STABLE_BRANCH...upstream/$STABLE_BRANCH" >&2
  exit 1
fi

echo "[sync] pushing $STABLE_BRANCH to origin..."
git push origin "$STABLE_BRANCH"

# --- dev branch: create on first run, then absorb the stable branch ---
if ! git show-ref --verify --quiet "refs/heads/$DEV_BRANCH"; then
  echo "[sync] creating $DEV_BRANCH from $STABLE_BRANCH..."
  git checkout -b "$DEV_BRANCH"
else
  git checkout "$DEV_BRANCH"
fi

echo "[sync] merging $STABLE_BRANCH into $DEV_BRANCH..."
if ! git merge "$STABLE_BRANCH" --no-edit; then
  echo "[sync] merge conflict. Resolve it, then: git add . && git merge --continue && git push origin $DEV_BRANCH" >&2
  exit 1
fi

echo "[sync] pushing $DEV_BRANCH to origin..."
git push -u origin "$DEV_BRANCH"

echo "[sync] done: $STABLE_BRANCH tracks upstream, $DEV_BRANCH carries your changes on top."