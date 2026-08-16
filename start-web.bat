@echo off
setlocal
cd /d "%~dp0"

where pnpm >nul 2>&1
if errorlevel 1 (
  echo [dsh] pnpm not found on PATH. Install pnpm 11.7.0 and retry.
  exit /b 1
)

if not exist node_modules (
  echo [dsh] installing dependencies...
  call pnpm install || exit /b 1
)

rem Web profile needs built library + frontend artifacts.
if not exist apps\cli\lib (
  echo [dsh] building...
  call pnpm run build || exit /b 1
)

echo [dsh] starting web UI at http://127.0.0.1:3080 ...
start "" "http://127.0.0.1:3080"
call pnpm dsh web %*
endlocal