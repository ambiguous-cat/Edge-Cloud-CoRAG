#!/usr/bin/env bash
set -euo pipefail

echo "[init] Starting development environment..."

if command -v nvm >/dev/null 2>&1; then
  echo "[init] Switching Node version with nvm: 20"
  nvm use 20 >/dev/null 2>&1 || nvm use 20
else
  echo "[init] nvm command not found in this shell. Please ensure nvm is installed and loaded."
fi

mkdir -p logs

if command -v python >/dev/null 2>&1; then
  echo "[init] Starting backend API (port 8005)..."
  (python api_server.py > logs/api_server.log 2>&1 &) || true
else
  echo "[init] python not found; skip backend startup."
fi

if [ -d "react-frontend" ] && [ -f "react-frontend/package.json" ]; then
  echo "[init] Starting React frontend (port 5173)..."
  (
    cd react-frontend
    npm run dev -- --host 0.0.0.0 --port 5173 > ../logs/react_frontend.log 2>&1 &
  ) || true
else
  echo "[init] react-frontend not found yet; skip frontend startup."
fi

echo "[init] Legacy Gradio frontend is preserved at 前端/ and is not auto-started here."
echo "[init] Done."

