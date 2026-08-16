@echo off
setlocal
cd /d "%~dp0"

rem ---- configurable ----
set "UPSTREAM_URL=https://github.com/deepseek-ai/deepseek-harness.git"
set "DEV_BRANCH=dev"
set "STABLE_BRANCH=master"
rem -----------------------

where git >nul 2>&1
if errorlevel 1 (
  echo [sync] git not found on PATH.
  exit /b 1
)

rem Refuse to run with uncommitted changes: merging over a dirty tree can
rem destroy local work.
for /f %%i in ('git status --porcelain') do (
  echo [sync] working tree has uncommitted changes. Commit or stash them first.
  exit /b 1
)

rem Ensure the upstream remote exists and points at the official repo.
git remote get-url upstream >nul 2>&1
if errorlevel 1 (
  echo [sync] adding upstream remote: %UPSTREAM_URL%
  git remote add upstream %UPSTREAM_URL% || exit /b 1
)

echo [sync] fetching upstream...
git fetch upstream || exit /b 1
git fetch origin || exit /b 1

rem --- stable branch: fast-forward only, never carries local commits ---
echo [sync] updating %STABLE_BRANCH% to upstream/%STABLE_BRANCH% ^(fast-forward only^)...
git checkout %STABLE_BRANCH% || exit /b 1
git merge --ff-only upstream/%STABLE_BRANCH%
if errorlevel 1 (
  echo [sync] %STABLE_BRANCH% has diverged from upstream. Inspect with: git log --oneline %STABLE_BRANCH%...upstream/%STABLE_BRANCH%
  exit /b 1
)

echo [sync] pushing %STABLE_BRANCH% to origin...
git push origin %STABLE_BRANCH% || exit /b 1

rem --- dev branch: create on first run, then absorb the stable branch ---
git show-ref --verify --quiet refs/heads/%DEV_BRANCH%
if errorlevel 1 (
  echo [sync] creating %DEV_BRANCH% from %STABLE_BRANCH%...
  git checkout -b %DEV_BRANCH% || exit /b 1
) else (
  git checkout %DEV_BRANCH% || exit /b 1
)

echo [sync] merging %STABLE_BRANCH% into %DEV_BRANCH%...
git merge %STABLE_BRANCH% --no-edit
if errorlevel 1 (
  echo [sync] merge conflict. Resolve it, then: git add . ^&^& git merge --continue ^&^& git push origin %DEV_BRANCH%
  exit /b 1
)

echo [sync] pushing %DEV_BRANCH% to origin...
git push -u origin %DEV_BRANCH% || exit /b 1

echo [sync] done: %STABLE_BRANCH% tracks upstream, %DEV_BRANCH% carries your changes on top.
endlocal